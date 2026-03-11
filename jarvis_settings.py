"""
JARVIS Settings GUI — Настройки помощника
Выбор микрофона, тест, конфигурация
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sounddevice as sd
import json
import os
import threading
import time
import numpy as np
import queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "jarvis_config.json")

# ============================================================================
# DEFAULT SETTINGS
# ============================================================================

DEFAULT_SETTINGS = {
    "microphone_index": None,       # None = default
    "microphone_name": "По умолчанию",
    "activation_mode": "voice",     # "voice" or "key"
    "wake_words": ["джарвис", "эй джарвис", "привет джарвис"],
    "command_timeout": 8,
    "wake_threshold": 0.75,         # fuzzy match threshold
    "volume_steps": 5,              # how many steps per volume command
    "autostart": False,
    "sound_enabled": True,
    "log_level": "INFO",
}

# ============================================================================
# SETTINGS I/O
# ============================================================================

def load_settings():
    """Load settings from JSON file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            # Merge with defaults (in case new fields were added)
            merged = {**DEFAULT_SETTINGS, **saved}
            return merged
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings to JSON file"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ============================================================================
# MICROPHONE UTILS
# ============================================================================

def get_input_devices():
    """Get list of input (microphone) devices"""
    devices = sd.query_devices()
    inputs = []
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            inputs.append({
                'index': i,
                'name': d['name'],
                'channels': d['max_input_channels'],
                'samplerate': d['default_samplerate'],
                'api': sd.query_hostapis(d['hostapi'])['name']
            })
    return inputs

# ============================================================================
# SETTINGS GUI
# ============================================================================

class JarvisSettingsApp:
    def __init__(self, root=None, on_save_callback=None):
        self.on_save_callback = on_save_callback
        self.settings = load_settings()
        self.testing = False
        self.test_thread = None
        self.audio_queue = queue.Queue()

        if root is None:
            self.root = tk.Tk()
            self.standalone = True
        else:
            self.root = tk.Toplevel(root)
            self.standalone = False

        self.root.title("JARVIS — Настройки")
        self.root.geometry("580x620")
        self.root.resizable(True, True)
        self.root.configure(bg='#1a1a2e')

        # Try to set icon
        try:
            self.root.iconbitmap(default='')
        except:
            pass

        self._build_ui()

    def _build_ui(self):
        # ---- Styles ----
        style = ttk.Style()
        style.theme_use('clam')

        # Dark theme colors
        BG = '#1a1a2e'
        BG2 = '#16213e'
        BG3 = '#0f3460'
        FG = '#e0e0e0'
        ACCENT = '#1e88e5'
        ACCENT2 = '#00c853'
        RED = '#e53935'

        style.configure('Dark.TFrame', background=BG)
        style.configure('Card.TFrame', background=BG2, relief='solid', borderwidth=1)
        style.configure('Dark.TLabel', background=BG, foreground=FG, font=('Segoe UI', 10))
        style.configure('Title.TLabel', background=BG, foreground='#ffffff', font=('Segoe UI', 14, 'bold'))
        style.configure('Section.TLabel', background=BG2, foreground=ACCENT, font=('Segoe UI', 11, 'bold'))
        style.configure('Dark.TRadiobutton', background=BG2, foreground=FG, font=('Segoe UI', 10))
        style.configure('Dark.TCheckbutton', background=BG2, foreground=FG, font=('Segoe UI', 10))

        style.configure('Accent.TButton', background=ACCENT, foreground='white', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Accent.TButton', background=[('active', BG3)])

        style.configure('Green.TButton', background=ACCENT2, foreground='white', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Green.TButton', background=[('active', '#00a844')])

        style.configure('Red.TButton', background=RED, foreground='white', font=('Segoe UI', 10, 'bold'), padding=8)
        style.map('Red.TButton', background=[('active', '#c62828')])

        style.configure('Dark.TCombobox', fieldbackground=BG3, foreground=FG, font=('Segoe UI', 10))

        # ---- Main Frame ----
        main = ttk.Frame(self.root, style='Dark.TFrame')
        main.pack(fill='both', expand=True, padx=15, pady=5)

        # ---- Title ----
        title_frame = ttk.Frame(main, style='Dark.TFrame')
        title_frame.pack(fill='x', pady=(0, 5))

        ttk.Label(title_frame, text="⚙️  JARVIS — Настройки", style='Title.TLabel').pack(side='left')

        # ============================================================
        # SECTION 1: MICROPHONE
        # ============================================================
        mic_frame = tk.Frame(main, bg=BG2, relief='solid', bd=1, padx=15, pady=5)
        mic_frame.pack(fill='x', pady=(0, 5))

        tk.Label(mic_frame, text="🎙  Микрофон", bg=BG2, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        # Device selector
        sel_frame = tk.Frame(mic_frame, bg=BG2)
        sel_frame.pack(fill='x', pady=(8, 5))

        tk.Label(sel_frame, text="Устройство:", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        self.devices = get_input_devices()
        device_names = ["По умолчанию"] + [f"{d['name']} ({d['api']})" for d in self.devices]

        self.mic_var = tk.StringVar(value=self.settings.get('microphone_name', 'По умолчанию'))
        self.mic_combo = ttk.Combobox(sel_frame, textvariable=self.mic_var, values=device_names,
                                       state='readonly', width=45, style='Dark.TCombobox')
        self.mic_combo.pack(side='left', padx=(10, 0))

        # Refresh button
        refresh_btn = tk.Button(sel_frame, text="🔄", bg=BG3, fg=FG, font=('Segoe UI', 10),
                                relief='flat', cursor='hand2', command=self._refresh_devices)
        refresh_btn.pack(side='left', padx=(5, 0))

        # Test section
        test_frame = tk.Frame(mic_frame, bg=BG2)
        test_frame.pack(fill='x', pady=(8, 5))

        self.test_btn = tk.Button(test_frame, text="🎤  Тест микрофона", bg=ACCENT, fg='white',
                                  font=('Segoe UI', 10, 'bold'), relief='flat', cursor='hand2',
                                  padx=15, pady=5, command=self._toggle_test)
        self.test_btn.pack(side='left')

        self.test_status = tk.Label(test_frame, text="", bg=BG2, fg=FG, font=('Segoe UI', 9))
        self.test_status.pack(side='left', padx=(10, 0))

        # Level meter
        meter_frame = tk.Frame(mic_frame, bg=BG2)
        meter_frame.pack(fill='x', pady=(5, 3))

        tk.Label(meter_frame, text="Уровень:", bg=BG2, fg='#888', font=('Segoe UI', 9)).pack(side='left')

        self.level_canvas = tk.Canvas(meter_frame, width=380, height=20, bg='#0d1117', highlightthickness=0)
        self.level_canvas.pack(side='left', padx=(10, 0))
        self.level_bar = self.level_canvas.create_rectangle(0, 0, 0, 20, fill=ACCENT2, outline='')

        self.level_label = tk.Label(meter_frame, text="0%", bg=BG2, fg='#888', font=('Segoe UI', 9), width=5)
        self.level_label.pack(side='left', padx=(5, 0))

        # Recognition test
        recog_frame = tk.Frame(mic_frame, bg=BG2)
        recog_frame.pack(fill='x', pady=(5, 0))

        tk.Label(recog_frame, text="Распознано:", bg=BG2, fg='#888', font=('Segoe UI', 9)).pack(side='left')

        self.recog_label = tk.Label(recog_frame, text="—", bg=BG2, fg='#fff', font=('Segoe UI', 10, 'bold'),
                                    wraplength=400, justify='left')
        self.recog_label.pack(side='left', padx=(10, 0))

        # ============================================================
        # SECTION 2: ACTIVATION MODE
        # ============================================================
        act_frame = tk.Frame(main, bg=BG2, relief='solid', bd=1, padx=15, pady=5)
        act_frame.pack(fill='x', pady=(0, 5))

        tk.Label(act_frame, text="🚀  Режим активации", bg=BG2, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        self.mode_var = tk.StringVar(value=self.settings.get('activation_mode', 'voice'))

        modes_frame = tk.Frame(act_frame, bg=BG2)
        modes_frame.pack(fill='x', pady=(8, 5))

        tk.Radiobutton(modes_frame, text='🎙  Голосовая активация (сказать "Джарвис")',
                       variable=self.mode_var, value='voice', bg=BG2, fg=FG, selectcolor=BG3,
                       font=('Segoe UI', 10), activebackground=BG2, activeforeground=FG
                       ).pack(anchor='w', pady=2)

        tk.Radiobutton(modes_frame, text='⌨️  По клавише (Right Shift)',
                       variable=self.mode_var, value='key', bg=BG2, fg=FG, selectcolor=BG3,
                       font=('Segoe UI', 10), activebackground=BG2, activeforeground=FG
                       ).pack(anchor='w', pady=2)

        # Wake words
        wake_frame = tk.Frame(act_frame, bg=BG2)
        wake_frame.pack(fill='x', pady=(8, 5))

        tk.Label(wake_frame, text="Слова активации:", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        wake_words_str = ", ".join(self.settings.get('wake_words', DEFAULT_SETTINGS['wake_words']))
        self.wake_entry = tk.Entry(wake_frame, bg=BG3, fg=FG, font=('Segoe UI', 10),
                                   insertbackground=FG, width=40, relief='flat', bd=5)
        self.wake_entry.insert(0, wake_words_str)
        self.wake_entry.pack(side='left', padx=(10, 0))

        # ============================================================
        # SECTION 3: PARAMETERS
        # ============================================================
        param_frame = tk.Frame(main, bg=BG2, relief='solid', bd=1, padx=15, pady=5)
        param_frame.pack(fill='x', pady=(0, 5))

        tk.Label(param_frame, text="⚡  Параметры", bg=BG2, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        # Command timeout
        timeout_frame = tk.Frame(param_frame, bg=BG2)
        timeout_frame.pack(fill='x', pady=(8, 5))

        tk.Label(timeout_frame, text="Таймаут команды (сек):", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        self.timeout_var = tk.IntVar(value=self.settings.get('command_timeout', 8))
        self.timeout_scale = tk.Scale(timeout_frame, from_=3, to=20, orient='horizontal',
                                       variable=self.timeout_var, bg=BG2, fg=FG, font=('Segoe UI', 9),
                                       highlightthickness=0, sliderrelief='flat', troughcolor=BG3,
                                       activebackground=ACCENT, length=200)
        self.timeout_scale.pack(side='left', padx=(10, 0))

        # Fuzzy threshold
        thresh_frame = tk.Frame(param_frame, bg=BG2)
        thresh_frame.pack(fill='x', pady=(5, 5))

        tk.Label(thresh_frame, text="Точность распознавания:", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        self.thresh_var = tk.DoubleVar(value=self.settings.get('wake_threshold', 0.75))
        self.thresh_scale = tk.Scale(thresh_frame, from_=0.5, to=1.0, resolution=0.05, orient='horizontal',
                                     variable=self.thresh_var, bg=BG2, fg=FG, font=('Segoe UI', 9),
                                     highlightthickness=0, sliderrelief='flat', troughcolor=BG3,
                                     activebackground=ACCENT, length=200)
        self.thresh_scale.pack(side='left', padx=(10, 0))

        tk.Label(thresh_frame, text="(ниже = мягче)", bg=BG2, fg='#888', font=('Segoe UI', 9)).pack(side='left', padx=(5, 0))

        # Volume steps
        vol_frame = tk.Frame(param_frame, bg=BG2)
        vol_frame.pack(fill='x', pady=(5, 5))

        tk.Label(vol_frame, text="Шаги громкости:", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        self.vol_var = tk.IntVar(value=self.settings.get('volume_steps', 5))
        self.vol_scale = tk.Scale(vol_frame, from_=1, to=15, orient='horizontal',
                                   variable=self.vol_var, bg=BG2, fg=FG, font=('Segoe UI', 9),
                                   highlightthickness=0, sliderrelief='flat', troughcolor=BG3,
                                   activebackground=ACCENT, length=200)
        self.vol_scale.pack(side='left', padx=(10, 0))

        # ============================================================
        # SECTION 4: OPTIONS
        # ============================================================
        opt_frame = tk.Frame(main, bg=BG2, relief='solid', bd=1, padx=15, pady=5)
        opt_frame.pack(fill='x', pady=(0, 5))

        tk.Label(opt_frame, text="🔧  Опции", bg=BG2, fg=ACCENT, font=('Segoe UI', 11, 'bold')).pack(anchor='w')

        opts_inner = tk.Frame(opt_frame, bg=BG2)
        opts_inner.pack(fill='x', pady=(8, 0))

        self.sound_var = tk.BooleanVar(value=self.settings.get('sound_enabled', True))
        tk.Checkbutton(opts_inner, text="🔊  Звуковые ответы", variable=self.sound_var,
                       bg=BG2, fg=FG, selectcolor=BG3, font=('Segoe UI', 10),
                       activebackground=BG2, activeforeground=FG
                       ).pack(anchor='w', pady=2)

        self.autostart_var = tk.BooleanVar(value=self.settings.get('autostart', False))
        tk.Checkbutton(opts_inner, text="🚀  Автозапуск с Windows", variable=self.autostart_var,
                       bg=BG2, fg=FG, selectcolor=BG3, font=('Segoe UI', 10),
                       activebackground=BG2, activeforeground=FG
                       ).pack(anchor='w', pady=2)

        # Log level
        log_frame = tk.Frame(opt_frame, bg=BG2)
        log_frame.pack(fill='x', pady=(5, 0))

        tk.Label(log_frame, text="Уровень логов:", bg=BG2, fg=FG, font=('Segoe UI', 10)).pack(side='left')

        self.log_var = tk.StringVar(value=self.settings.get('log_level', 'INFO'))
        log_combo = ttk.Combobox(log_frame, textvariable=self.log_var,
                                  values=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                                  state='readonly', width=12, style='Dark.TCombobox')
        log_combo.pack(side='left', padx=(10, 0))

        # ============================================================
        # BUTTONS
        # ============================================================
        btn_frame = tk.Frame(main, bg=BG)
        btn_frame.pack(fill='x', pady=(5, 0))

        save_btn = tk.Button(btn_frame, text="💾  Сохранить", bg=ACCENT2, fg='white',
                             font=('Segoe UI', 11, 'bold'), relief='flat', cursor='hand2',
                             padx=25, pady=8, command=self._save)
        save_btn.pack(side='right')

        reset_btn = tk.Button(btn_frame, text="🔄  Сбросить", bg='#555', fg='white',
                              font=('Segoe UI', 10), relief='flat', cursor='hand2',
                              padx=15, pady=8, command=self._reset)
        reset_btn.pack(side='right', padx=(0, 10))

        launch_btn = tk.Button(btn_frame, text="▶️  Запустить JARVIS", bg=ACCENT, fg='white',
                               font=('Segoe UI', 10, 'bold'), relief='flat', cursor='hand2',
                               padx=15, pady=8, command=self._launch_jarvis)
        launch_btn.pack(side='left')

    # ================================================================
    # DEVICE REFRESH
    # ================================================================

    def _refresh_devices(self):
        self.devices = get_input_devices()
        device_names = ["По умолчанию"] + [f"{d['name']} ({d['api']})" for d in self.devices]
        self.mic_combo['values'] = device_names
        self.test_status.config(text="Список обновлён", fg='#00c853')

    # ================================================================
    # MIC TEST
    # ================================================================

    def _toggle_test(self):
        if self.testing:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        self.testing = True
        self.test_btn.config(text="⏹  Остановить тест", bg='#e53935')
        self.test_status.config(text="Слушаю...", fg='#ffb300')
        self.recog_label.config(text="Говорите что-нибудь...")

        # Get selected device index
        selected = self.mic_var.get()
        device_index = None
        if selected != "По умолчанию":
            for d in self.devices:
                full_name = f"{d['name']} ({d['api']})"
                if full_name == selected:
                    device_index = d['index']
                    break

        self.test_thread = threading.Thread(target=self._test_worker, args=(device_index,), daemon=True)
        self.test_thread.start()

    def _stop_test(self):
        self.testing = False
        self.test_btn.config(text="🎤  Тест микрофона", bg='#1e88e5')
        self.test_status.config(text="Тест остановлен", fg='#888')

    def _test_worker(self, device_index):
        """Test microphone: show level + try to recognize speech"""
        from vosk import Model, KaldiRecognizer
        MODEL_PATH = os.path.join(BASE_DIR, "vosk-model-small-ru-0.22")

        try:
            model = Model(MODEL_PATH)
        except Exception as e:
            self.root.after(0, lambda: self.test_status.config(text=f"Ошибка модели: {e}", fg='red'))
            self.testing = False
            return

        recognizer = KaldiRecognizer(model, 16000)
        q = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(bytes(indata))
            # Calculate RMS level
            audio_data = np.frombuffer(indata, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
            level = min(100, int(rms / 300 * 100))
            self.root.after(0, lambda l=level: self._update_level(l))

        try:
            kwargs = {
                'samplerate': 16000,
                'blocksize': 4000,
                'dtype': 'int16',
                'channels': 1,
                'callback': callback
            }
            if device_index is not None:
                kwargs['device'] = device_index

            with sd.RawInputStream(**kwargs):
                while self.testing:
                    try:
                        data = q.get(timeout=0.2)
                    except:
                        continue

                    if recognizer.AcceptWaveform(data):
                        import json as js
                        result = js.loads(recognizer.Result())
                        text = result.get("text", "")
                        if text:
                            self.root.after(0, lambda t=text: self.recog_label.config(text=f'"{t}"'))
                            self.root.after(0, lambda: self.test_status.config(text="Распознано!", fg='#00c853'))

        except Exception as e:
            self.root.after(0, lambda: self.test_status.config(text=f"Ошибка: {e}", fg='red'))
        finally:
            self.root.after(0, lambda: self._update_level(0))
            self.testing = False
            self.root.after(0, lambda: self.test_btn.config(text="🎤  Тест микрофона", bg='#1e88e5'))

    def _update_level(self, level):
        """Update the level meter bar"""
        bar_width = int(380 * level / 100)
        # Color gradient: green -> yellow -> red
        if level < 40:
            color = '#00c853'
        elif level < 70:
            color = '#ffb300'
        else:
            color = '#e53935'

        self.level_canvas.coords(self.level_bar, 0, 0, bar_width, 20)
        self.level_canvas.itemconfig(self.level_bar, fill=color)
        self.level_label.config(text=f"{level}%")

    # ================================================================
    # SAVE / RESET / LAUNCH
    # ================================================================

    def _save(self):
        # Get microphone
        selected = self.mic_var.get()
        mic_index = None
        if selected != "По умолчанию":
            for d in self.devices:
                full_name = f"{d['name']} ({d['api']})"
                if full_name == selected:
                    mic_index = d['index']
                    break

        # Parse wake words
        wake_text = self.wake_entry.get().strip()
        wake_words = [w.strip() for w in wake_text.split(',') if w.strip()]
        if not wake_words:
            wake_words = DEFAULT_SETTINGS['wake_words']

        self.settings = {
            "microphone_index": mic_index,
            "microphone_name": selected,
            "activation_mode": self.mode_var.get(),
            "wake_words": wake_words,
            "command_timeout": self.timeout_var.get(),
            "wake_threshold": self.thresh_var.get(),
            "volume_steps": self.vol_var.get(),
            "autostart": self.autostart_var.get(),
            "sound_enabled": self.sound_var.get(),
            "log_level": self.log_var.get(),
        }

        save_settings(self.settings)

        # Handle autostart
        if self.settings['autostart']:
            self._setup_autostart()
        else:
            self._remove_autostart()

        messagebox.showinfo("JARVIS", "Настройки сохранены!\n\nПерезапустите JARVIS для применения.")

        if self.on_save_callback:
            self.on_save_callback(self.settings)

    def _reset(self):
        if messagebox.askyesno("Сбросить настройки", "Вернуть все настройки по умолчанию?"):
            self.settings = DEFAULT_SETTINGS.copy()
            save_settings(self.settings)
            # Update UI
            self.mic_var.set("По умолчанию")
            self.mode_var.set("voice")
            self.wake_entry.delete(0, 'end')
            self.wake_entry.insert(0, ", ".join(DEFAULT_SETTINGS['wake_words']))
            self.timeout_var.set(8)
            self.thresh_var.set(0.75)
            self.vol_var.set(5)
            self.sound_var.set(True)
            self.autostart_var.set(False)
            self.log_var.set("INFO")
            messagebox.showinfo("JARVIS", "Настройки сброшены!")

    def _launch_jarvis(self):
        """Launch Jarvis.py as separate process"""
        import subprocess
        jarvis_path = os.path.join(BASE_DIR, "Jarvis.py")
        try:
            subprocess.Popen(
                ['python', jarvis_path],
                cwd=BASE_DIR,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.test_status.config(text="JARVIS запущен!", fg='#00c853')
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")

    def _setup_autostart(self):
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               r"Microsoft\Windows\Start Menu\Programs\Startup")
        src = os.path.join(BASE_DIR, "run_audiohelper.vbs")
        dst = os.path.join(startup, "Jarvis_Autostart.vbs")
        if os.path.exists(src):
            import shutil
            shutil.copy2(src, dst)

    def _remove_autostart(self):
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               r"Microsoft\Windows\Start Menu\Programs\Startup")
        dst = os.path.join(startup, "Jarvis_Autostart.vbs")
        if os.path.exists(dst):
            os.remove(dst)

    def run(self):
        self.root.mainloop()


# ============================================================================
# STANDALONE RUN
# ============================================================================

if __name__ == "__main__":
    app = JarvisSettingsApp()
    app.run()
