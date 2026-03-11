import queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import webbrowser
import json
import platform
import urllib.parse
from cachetools import TTLCache
import time
import subprocess
import pygame
import difflib
from concurrent.futures import ThreadPoolExecutor
import ctypes
import os
import threading
import logging
import sys
import asyncio
import edge_tts
import tempfile

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============================================================================
# CONFIG — load from jarvis_config.json
# ============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "vosk-model-small-ru-0.22")
SETTINGS_FILE = os.path.join(BASE_DIR, "jarvis_config.json")

def _load_config():
    defaults = {
        "microphone_index": None,
        "microphone_name": "По умолчанию",
        "activation_mode": "voice",
        "wake_words": ["джарвис", "эй джарвис", "привет джарвис", "jarvis"],
        "command_timeout": 8,
        "wake_threshold": 0.75,
        "volume_steps": 5,
        "autostart": False,
        "sound_enabled": True,
        "log_level": "INFO",
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
            return {**defaults, **saved}
        except Exception:
            pass
    return defaults

CONFIG = _load_config()

WAKE_WORDS = CONFIG['wake_words']
COMMAND_TIMEOUT = CONFIG['command_timeout']
PASSIVE_LISTEN = (CONFIG['activation_mode'] == 'voice')
FUZZY_THRESHOLD = CONFIG['wake_threshold']
VOLUME_STEPS = CONFIG['volume_steps']
SOUND_ENABLED = CONFIG['sound_enabled']
MIC_DEVICE = CONFIG['microphone_index']  # None = default

pygame.mixer.init()
executor = ThreadPoolExecutor(max_workers=4)

# ============================================================================
# SOUNDS
# ============================================================================

SOUNDS = {
    'greeting':    pygame.mixer.Sound(os.path.join(BASE_DIR, "Да, сэр.wav")),
    'greeting2':   pygame.mixer.Sound(os.path.join(BASE_DIR, "Мы подключены и готовы.wav")),
    'shutdown':    pygame.mixer.Sound(os.path.join(BASE_DIR, "Отключаю питание.wav")),
    'restart':     pygame.mixer.Sound(os.path.join(BASE_DIR, "Да, сэр.wav")),
    'lock':        pygame.mixer.Sound(os.path.join(BASE_DIR, "Да, сэр.wav")),
    'minimize_all': pygame.mixer.Sound(os.path.join(BASE_DIR, "Всегда к вашим услугам сэр.wav")),
    'bin':         pygame.mixer.Sound(os.path.join(BASE_DIR, "Как пожелаете .wav")),
    'camera':      pygame.mixer.Sound(os.path.join(BASE_DIR, "Есть.wav")),
    'exit':        pygame.mixer.Sound(os.path.join(BASE_DIR, "Отключаю питание.wav")),
    'search':      pygame.mixer.Sound(os.path.join(BASE_DIR, "Запрос выполнен, сэр.wav")),
    'action':      pygame.mixer.Sound(os.path.join(BASE_DIR, "Есть.wav")),
    'confirm':     pygame.mixer.Sound(os.path.join(BASE_DIR, "К вашим услугам сэр.wav")),
    'loading':     pygame.mixer.Sound(os.path.join(BASE_DIR, "Загружаю сэр.wav")),
    'timer_done':  pygame.mixer.Sound(os.path.join(BASE_DIR, "Запрос выполнен, сэр.wav")),
}

search_cache = TTLCache(maxsize=50, ttl=43200)
active_timers = []

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def speak(text):
    if not SOUND_ENABLED:
        return
    print(f"🤖 Джарвис говорит: {text}")
    try:
        # Generate temporary filename
        temp_file = os.path.join(tempfile.gettempdir(), f"jarvis_speech_{int(time.time()*1000)}.mp3")
        
        async def _save_audio():
            # Voice can be changed: ru-RU-SvetlanaNeural (female), ru-RU-DmitryNeural (male)
            communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
            await communicate.save(temp_file)
            
        asyncio.run(_save_audio())
        
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
        try:
            os.remove(temp_file)
        except Exception:
            pass
    except Exception as e:
        print(f"❌ Ошибка синтеза речи: {e}")

def play_sound(sound):
    if not SOUND_ENABLED:
        return
    try:
        sound.play()
    except Exception:
        pass

def safe_submit(action, *args):
    try:
        action(*args)
    except Exception as e:
        logging.error(f"Ошибка в {action.__name__}: {e}")

def fuzzy_match(word, keyword_list, threshold=None):
    if threshold is None:
        threshold = FUZZY_THRESHOLD
    best_match = None
    best_score = 0
    for keyword in keyword_list:
        similarity = difflib.SequenceMatcher(None, word, keyword).ratio()
        if similarity >= threshold and similarity > best_score:
            best_score = similarity
            best_match = keyword
    return best_match

# ============================================================================
# ACTIONS — System
# ============================================================================

def action_exit():
    print("🛑 Выключение помощника...")
    executor.submit(play_sound, SOUNDS['exit'])
    time.sleep(2)
    os._exit(0)

def action_shutdown():
    os.system("shutdown /s /t 3")

def action_restart():
    os.system("shutdown /r /t 3")

def action_lock():
    if platform.system() == "Windows":
        ctypes.windll.user32.LockWorkStation()

def action_minimize_all_windows():
    if platform.system() == "Windows":
        user32 = ctypes.WinDLL('user32')
        VK_LWIN, VK_D = 0x5B, 0x44
        user32.keybd_event(ctypes.c_ubyte(VK_LWIN), 0, 0, 0)
        user32.keybd_event(ctypes.c_ubyte(VK_D), 0, 0, 0)
        time.sleep(0.05)
        user32.keybd_event(ctypes.c_ubyte(VK_D), 0, 2, 0)
        user32.keybd_event(ctypes.c_ubyte(VK_LWIN), 0, 2, 0)

def action_restart_explorer():
    try:
        subprocess.run("taskkill /f /im explorer.exe", shell=True)
        time.sleep(1)
        subprocess.Popen("explorer.exe", shell=True)
        print("🔄 explorer.exe перезапущен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def action_empty_recycle_bin():
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        print("🗑 Корзина очищена" if result == 0 else f"Ошибка: {result}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def action_screenshot():
    try:
        import keyboard
        keyboard.press_and_release('win+shift+s')
        print("📸 Скриншот (Win+Shift+S)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def action_task_manager():
    try:
        subprocess.Popen("taskmgr.exe")
        print("📊 Диспетчер задач открыт")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ============================================================================
# ACTIONS — Apps
# ============================================================================

def open_app(app_path):
    try:
        if platform.system() == 'Windows':
            os.startfile(app_path)
    except Exception as e:
        print(f'❌ Ошибка при открытии {app_path}: {e}')

def action_open_browser():
    webbrowser.open("https://google.com")
    print("🌐 Браузер открыт")

def action_open_calculator():
    subprocess.Popen("calc.exe")
    print("🔢 Калькулятор открыт")

def action_open_notepad():
    subprocess.Popen("notepad.exe")
    print("📝 Блокнот открыт")

def action_open_telegram():
    telegram_paths = [
        os.path.expanduser(r"~\AppData\Roaming\Telegram Desktop\Telegram.exe"),
        r"C:\Program Files\Telegram Desktop\Telegram.exe",
        r"C:\Users\user\AppData\Roaming\Telegram Desktop\Telegram.exe",
    ]
    for path in telegram_paths:
        if os.path.exists(path):
            subprocess.Popen([path])
            print("💬 Telegram открыт")
            return
    # Попробуем через start
    try:
        subprocess.Popen(["start", "tg://"], shell=True)
        print("💬 Telegram открыт")
    except:
        print("❌ Telegram не найден")

def action_open_camera():
    try:
        subprocess.run(["start", "microsoft.windows.camera:"], shell=True)
        print("📷 Камера запущена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def action_open_explorer():
    subprocess.Popen("explorer.exe")
    print("📁 Проводник открыт")

def action_open_settings():
    subprocess.Popen(["start", "ms-settings:"], shell=True)
    print("⚙️ Настройки открыты")

# ============================================================================
# ACTIONS — Volume Control
# ============================================================================

def _send_media_key(vk_code):
    """Send media key using Windows API"""
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    user32 = ctypes.WinDLL('user32')
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

def action_volume_up():
    VK_VOLUME_UP = 0xAF
    for _ in range(VOLUME_STEPS):
        _send_media_key(VK_VOLUME_UP)
        time.sleep(0.05)
    print("🔊 Громкость увеличена")

def action_volume_down():
    VK_VOLUME_DOWN = 0xAE
    for _ in range(VOLUME_STEPS):
        _send_media_key(VK_VOLUME_DOWN)
        time.sleep(0.05)
    print("🔉 Громкость уменьшена")

def action_volume_mute():
    VK_VOLUME_MUTE = 0xAD
    _send_media_key(VK_VOLUME_MUTE)
    print("🔇 Звук выключен/включён")

def action_media_play_pause():
    VK_MEDIA_PLAY_PAUSE = 0xB3
    _send_media_key(VK_MEDIA_PLAY_PAUSE)
    print("⏯ Плей/Пауза")

def action_media_next():
    VK_MEDIA_NEXT_TRACK = 0xB0
    _send_media_key(VK_MEDIA_NEXT_TRACK)
    print("⏭ Следующий трек")

def action_media_prev():
    VK_MEDIA_PREV_TRACK = 0xB1
    _send_media_key(VK_MEDIA_PREV_TRACK)
    print("⏮ Предыдущий трек")

# ============================================================================
# ACTIONS — Timers
# ============================================================================

def _timer_worker(seconds, label):
    time.sleep(seconds)
    print(f"⏰ ТАЙМЕР: {label} — время вышло!")
    play_sound(SOUNDS['timer_done'])
    # Show Windows notification
    try:
        from ctypes import windll
        windll.user32.MessageBeep(0x00000040)
    except:
        pass

def action_timer_1min():
    t = threading.Thread(target=_timer_worker, args=(60, "1 минута"), daemon=True)
    t.start()
    active_timers.append(t)
    print("⏱ Таймер на 1 минуту запущен")

def action_timer_5min():
    t = threading.Thread(target=_timer_worker, args=(300, "5 минут"), daemon=True)
    t.start()
    active_timers.append(t)
    print("⏱ Таймер на 5 минут запущен")

def action_timer_10min():
    t = threading.Thread(target=_timer_worker, args=(600, "10 минут"), daemon=True)
    t.start()
    active_timers.append(t)
    print("⏱ Таймер на 10 минут запущен")

def action_timer_30min():
    t = threading.Thread(target=_timer_worker, args=(1800, "30 минут"), daemon=True)
    t.start()
    active_timers.append(t)
    print("⏱ Таймер на 30 минут запущен")

# ============================================================================
# ACTIONS — Search
# ============================================================================

def action_search(text):
    try:
        for kw in COMMANDS['search']['keywords']:
            text = text.replace(kw.lower(), "")
        query = text.strip()
        if not query:
            speak("Что именно вы хотите найти?")
            return
        
        speak(f"Ищу информацию по запросу {query}")

        encoded_query = urllib.parse.quote(query)
        cache_key = f"search_{encoded_query}"
        if cache_key in search_cache:
            url = search_cache[cache_key]
        else:
            url = f"https://www.google.com/search?q={encoded_query}"
            search_cache[cache_key] = url
        
        webbrowser.open(url)
        print(f"🔍 Поиск: {query}")
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")

def action_youtube_search(text):
    try:
        for kw in COMMANDS['youtube']['keywords']:
            text = text.replace(kw.lower(), "")
        query = text.strip()
        if not query:
            speak("Что будем искать на ютубе?")
            webbrowser.open("https://youtube.com")
            return
            
        speak(f"Ищу видео {query}")

        encoded = urllib.parse.quote(query)
        webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
        print(f"▶️ YouTube: {query}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ============================================================================
# ACTIONS — Info
# ============================================================================

def action_time():
    now_str = time.strftime("%H:%M")
    # For speaking, let's substitute '00' with something readable if needed, Edge TTS handles %H:%M fine
    print(f"🕐 Сейчас {now_str}")
    speak(f"В данный момент {now_str}")

def action_date():
    import locale
    try:
        # На Windows "Russian_Russia.1251" обычно работает лучше, но попробуем и UTF-8
        locale.setlocale(locale.LC_TIME, '')
    except:
        pass
    now_str = time.strftime("%d %B %Y, %A")
    print(f"📅 Сегодня {now_str}")
    speak(f"Сегодня {now_str}")

def greeting():
    import random
    phrases = ["Всегда к вашим услугам!", "К вашим услугам, сэр.", "Слушаю.", "Я здесь.", "Системы онлайн."]
    speak(random.choice(phrases))

# ============================================================================
# COMMANDS REGISTRY
# ============================================================================

COMMANDS = {
    # --- Приветствие ---
    'greeting': {
        'keywords': ['джарвис', 'эй джарвис', 'ассистент', 'jarvis', 'привет джарвис'],
        'action': greeting,
        'sound': SOUNDS['greeting']
    },

    # --- Система ---
    'shutdown': {
        'keywords': ['выключи компьютер', 'отключи компьютер', 'заверши работу', 'питание выкл'],
        'action': action_shutdown,
        'sound': SOUNDS['shutdown']
    },
    'restart': {
        'keywords': ['перезагрузи компьютер', 'перезапусти компьютер', 'рестарт', 'перезапуск'],
        'action': action_restart,
        'sound': SOUNDS['restart']
    },
    'lock': {
        'keywords': ['заблокируй компьютер', 'блокировка', 'заблокировать', 'экран блок'],
        'action': action_lock,
        'sound': SOUNDS['confirm']
    },
    'minimize_all': {
        'keywords': ['сверни все окна', 'сверни всё', 'показать рабочий стол', 'покажи стол'],
        'action': action_minimize_all_windows,
        'sound': SOUNDS['minimize_all']
    },
    'bin': {
        'keywords': ['очисти корзину', 'очисти мусор', 'удали мусор', 'пустая корзина'],
        'action': action_empty_recycle_bin,
        'sound': SOUNDS['bin']
    },
    'restart_explorer': {
        'keywords': ['перезагрузи проводник', 'перезапусти проводник'],
        'action': action_restart_explorer,
        'sound': SOUNDS['action']
    },
    'screenshot': {
        'keywords': ['скриншот', 'снимок экрана', 'сделай скриншот', 'сделай снимок'],
        'action': action_screenshot,
        'sound': SOUNDS['action']
    },
    'task_manager': {
        'keywords': ['диспетчер задач', 'открой диспетчер', 'менеджер задач'],
        'action': action_task_manager,
        'sound': SOUNDS['action']
    },

    # --- Приложения ---
    'browser': {
        'keywords': ['открой браузер', 'запусти браузер', 'интернет', 'открой интернет'],
        'action': action_open_browser,
        'sound': SOUNDS['loading']
    },
    'calculator': {
        'keywords': ['калькулятор', 'открой калькулятор', 'запусти калькулятор'],
        'action': action_open_calculator,
        'sound': SOUNDS['action']
    },
    'notepad': {
        'keywords': ['блокнот', 'открой блокнот', 'запусти блокнот', 'текстовый редактор'],
        'action': action_open_notepad,
        'sound': SOUNDS['action']
    },
    'telegram': {
        'keywords': ['телеграм', 'открой телеграм', 'запусти телеграм', 'telegram', 'открой телеграмм'],
        'action': action_open_telegram,
        'sound': SOUNDS['loading']
    },
    'camera': {
        'keywords': ['запусти камеру', 'открой камеру', 'включи камеру', 'вебкамера'],
        'action': action_open_camera,
        'sound': SOUNDS['action']
    },
    'explorer': {
        'keywords': ['открой проводник', 'файлы', 'диспетчер файлов', 'мой компьютер'],
        'action': action_open_explorer,
        'sound': SOUNDS['action']
    },
    'settings': {
        'keywords': ['настройки', 'открой настройки', 'параметры', 'параметры системы'],
        'action': action_open_settings,
        'sound': SOUNDS['action']
    },

    # --- Громкость ---
    'volume_up': {
        'keywords': ['громче', 'прибавь громкость', 'увеличь громкость', 'звук громче', 'погромче'],
        'action': action_volume_up,
        'sound': None
    },
    'volume_down': {
        'keywords': ['тише', 'убавь громкость', 'уменьши громкость', 'звук тише', 'потише'],
        'action': action_volume_down,
        'sound': None
    },
    'volume_mute': {
        'keywords': ['выключи звук', 'без звука', 'отключи звук', 'мьют'],
        'action': action_volume_mute,
        'sound': None
    },

    # --- Медиа ---
    'media_play': {
        'keywords': ['плей', 'пауза', 'воспроизведение', 'играй', 'продолжи'],
        'action': action_media_play_pause,
        'sound': None
    },
    'media_next': {
        'keywords': ['следующий трек', 'следующая песня', 'дальше', 'следующий'],
        'action': action_media_next,
        'sound': None
    },
    'media_prev': {
        'keywords': ['предыдущий трек', 'предыдущая песня', 'назад', 'предыдущий'],
        'action': action_media_prev,
        'sound': None
    },

    # --- Таймеры ---
    'timer_1': {
        'keywords': ['таймер одна минута', 'таймер на минуту', 'таймер один минута'],
        'action': action_timer_1min,
        'sound': SOUNDS['confirm']
    },
    'timer_5': {
        'keywords': ['таймер пять минут', 'таймер на пять', 'таймер на пять минут'],
        'action': action_timer_5min,
        'sound': SOUNDS['confirm']
    },
    'timer_10': {
        'keywords': ['таймер десять минут', 'таймер на десять', 'таймер на десять минут'],
        'action': action_timer_10min,
        'sound': SOUNDS['confirm']
    },
    'timer_30': {
        'keywords': ['таймер тридцать минут', 'таймер на тридцать', 'таймер на полчаса', 'таймер полчаса'],
        'action': action_timer_30min,
        'sound': SOUNDS['confirm']
    },

    # --- Поиск ---
    'search': {
        'keywords': ['поиск', 'найди', 'найди в гугл', 'поиск в интернете', 'загугли', 'погугли'],
        'action': action_search,
        'sound': SOUNDS['search']
    },
    'youtube': {
        'keywords': ['ютуб', 'открой ютуб', 'youtube', 'видео поиск', 'найди на ютубе'],
        'action': action_youtube_search,
        'sound': SOUNDS['loading']
    },

    # --- Информация ---
    'time': {
        'keywords': ['который час', 'сколько времени', 'время', 'текущее время'],
        'action': action_time,
        'sound': SOUNDS['confirm']
    },
    'date': {
        'keywords': ['какой сегодня день', 'какая дата', 'дата', 'сегодняшняя дата'],
        'action': action_date,
        'sound': SOUNDS['confirm']
    },

    # --- Выход ---
    'exit': {
        'keywords': ['джарвис выключись', 'джарвис отключись', 'джарвис стоп'],
        'action': action_exit,
        'sound': SOUNDS['exit']
    },
}

# ============================================================================
# COMMAND RECOGNITION
# ============================================================================

def recognize_command(text):
    text_clean = text.strip().lower()

    # 1. Exact/fuzzy match
    for cmd_key, command in COMMANDS.items():
        for keyword in command['keywords']:
            # Try exact substring match first
            if keyword in text_clean:
                return cmd_key, keyword
            # Then fuzzy match
            matched = fuzzy_match(text_clean, [keyword])
            if matched:
                return cmd_key, matched

    # 2. Search fallback — if text contains search keywords
    if any(kw in text_clean for kw in COMMANDS['search']['keywords']):
        return 'search', next(kw for kw in COMMANDS['search']['keywords'] if kw in text_clean)

    # 3. YouTube fallback
    if any(kw in text_clean for kw in COMMANDS['youtube']['keywords']):
        return 'youtube', next(kw for kw in COMMANDS['youtube']['keywords'] if kw in text_clean)

    return None, None

def is_wake_word(text):
    """Check if text contains a wake word"""
    text_lower = text.strip().lower()
    for wake in WAKE_WORDS:
        if wake in text_lower:
            return True
        if fuzzy_match(text_lower, [wake], threshold=0.8):
            return True
    return False

# ============================================================================
# SYSTEM TRAY
# ============================================================================

def setup_tray():
    """Create system tray icon with menu"""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logging.warning("pystray / Pillow не установлены — трей не будет создан")
        return

    def create_icon_image():
        """Create a simple J icon"""
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Blue circle background
        draw.ellipse([2, 2, 62, 62], fill=(30, 136, 229, 255))
        # White "J" letter
        try:
            font = ImageFont.truetype("arial.ttf", 38)
        except:
            font = ImageFont.load_default()
        draw.text((20, 8), "J", fill=(255, 255, 255, 255), font=font)
        return img

    def on_exit(icon, item):
        icon.stop()
        action_exit()

    def on_status(icon, item):
        print("="*40)
        print("   JARVIS STATUS")
        print("="*40)
        print(f"   Режим: {'Голосовая активация' if PASSIVE_LISTEN else 'По клавише'}")
        print(f"   Таймеров: {len([t for t in active_timers if t.is_alive()])}")
        print(f"   Команд: {len(COMMANDS)}")
        print("="*40)

    def on_settings(icon, item):
        """Open Settings GUI"""
        settings_script = os.path.join(BASE_DIR, "jarvis_settings.py")
        try:
            subprocess.Popen(
                ['python', settings_script],
                cwd=BASE_DIR,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
        except Exception as e:
            logging.error(f"Не удалось открыть настройки: {e}")

    mic_name = CONFIG.get('microphone_name', 'По умолчанию')
    mode_label = "🎙 Голос" if PASSIVE_LISTEN else "⌨️ Клавиша"

    menu = pystray.Menu(
        pystray.MenuItem(f"🟢 JARVIS | {mode_label}", None, enabled=False),
        pystray.MenuItem(f"🎤 {mic_name}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⚙️ Настройки", on_settings),
        pystray.MenuItem("📊 Статус", on_status),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🔊 Громче", lambda icon, item: action_volume_up()),
        pystray.MenuItem("🔉 Тише", lambda icon, item: action_volume_down()),
        pystray.MenuItem("🔇 Мьют", lambda icon, item: action_volume_mute()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐 Браузер", lambda icon, item: action_open_browser()),
        pystray.MenuItem("💬 Telegram", lambda icon, item: action_open_telegram()),
        pystray.MenuItem("🔢 Калькулятор", lambda icon, item: action_open_calculator()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Выход", on_exit),
    )

    icon = pystray.Icon("JARVIS", create_icon_image(), "JARVIS Assistant", menu)

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()
    logging.info("🔵 Иконка в трее создана")

# ============================================================================
# AUTOSTART SETUP
# ============================================================================

def setup_autostart():
    """Copy VBS launcher to Windows Startup folder"""
    startup_folder = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    vbs_source = os.path.join(BASE_DIR, "run_audiohelper.vbs")
    vbs_dest = os.path.join(startup_folder, "Jarvis_Autostart.vbs")

    if not os.path.exists(vbs_source):
        print("❌ Файл run_audiohelper.vbs не найден")
        return False

    try:
        import shutil
        shutil.copy2(vbs_source, vbs_dest)
        print(f"✅ Автозапуск настроен: {vbs_dest}")
        return True
    except Exception as e:
        print(f"❌ Ошибка настройки автозапуска: {e}")
        return False

def remove_autostart():
    """Remove VBS launcher from Windows Startup folder"""
    startup_folder = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    vbs_dest = os.path.join(startup_folder, "Jarvis_Autostart.vbs")
    if os.path.exists(vbs_dest):
        os.remove(vbs_dest)
        print("✅ Автозапуск удалён")
    else:
        print("ℹ️ Автозапуск не был настроен")

# ============================================================================
# MAIN LISTENER
# ============================================================================

def listen():
    logging.info("Проверка аудиоустройств")
    logging.info(f"Устройства: {sd.query_devices()}")

    try:
        model = Model(MODEL_PATH)
    except Exception as e:
        logging.error(f"Ошибка загрузки модели Vosk: {e}")
        return

    recognizer = KaldiRecognizer(model, 16000)
    q = queue.Queue()

    def callback(indata, frames, _time, status):
        if status and 'overflow' in str(status).lower():
            logging.warning("Переполнение аудиобуфера")
        q.put(bytes(indata))

    # Build RawInputStream kwargs with optional device
    stream_kwargs = {
        'samplerate': 16000,
        'blocksize': 4000,
        'dtype': 'int16',
        'channels': 1,
        'callback': callback
    }
    if MIC_DEVICE is not None:
        stream_kwargs['device'] = MIC_DEVICE
        logging.info(f"🎤 Используется микрофон: {CONFIG.get('microphone_name', MIC_DEVICE)}")

    if PASSIVE_LISTEN:
        # ========== ГОЛОСОВАЯ АКТИВАЦИЯ ==========
        logging.info("🎙 Режим голосовой активации. Скажите 'Джарвис'...")

        with sd.RawInputStream(**stream_kwargs):
            while True:
                try:
                    data = q.get(timeout=0.5)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower().strip()
                    if not text:
                        continue

                    # Check for wake word
                    if is_wake_word(text):
                        # Check if there's a command merged with wake word
                        remaining = text
                        for wake in WAKE_WORDS:
                            remaining = remaining.replace(wake, "").strip()

                        if remaining:
                            # Command was said together with wake word
                            cmd_key, keyword = recognize_command(remaining)
                            if cmd_key:
                                logging.info(f"🗣 Команда: {remaining} → {cmd_key}")
                                command = COMMANDS[cmd_key]
                                if command['sound']:
                                    executor.submit(play_sound, command['sound'])
                                if command['action'] in (action_search, action_youtube_search):
                                    executor.submit(safe_submit, command['action'], remaining)
                                else:
                                    executor.submit(safe_submit, command['action'])
                                continue

                        # Wake word detected — activate listening mode
                        logging.info("🟢 Активирован. Слушаю команду...")
                        executor.submit(play_sound, SOUNDS['greeting'])

                        active_until = time.time() + COMMAND_TIMEOUT
                        while time.time() < active_until:
                            try:
                                data = q.get(timeout=0.1)
                            except queue.Empty:
                                continue

                            if recognizer.AcceptWaveform(data):
                                result = json.loads(recognizer.Result())
                                cmd_text = result.get("text", "").lower().strip()
                                if not cmd_text:
                                    continue

                                logging.info(f"🗣 Услышал: {cmd_text}")
                                cmd_key, keyword = recognize_command(cmd_text)
                                if not cmd_key:
                                    logging.warning("❌ Команда не распознана")
                                    continue

                                command = COMMANDS[cmd_key]
                                if command['sound']:
                                    executor.submit(play_sound, command['sound'])
                                if command['action'] in (action_search, action_youtube_search):
                                    cleaned = cmd_text.replace(keyword, "").strip()
                                    executor.submit(safe_submit, command['action'], cleaned)
                                else:
                                    executor.submit(safe_submit, command['action'])
                                active_until = time.time() + COMMAND_TIMEOUT

                            # Clear buffer
                            while not q.empty():
                                q.get()

                        logging.info("💤 Время ожидания истекло")
                    # else: not a wake word — continue passive listening

    else:
        # ========== ПО КЛАВИШЕ (FALLBACK) ==========
        import keyboard
        while True:
            logging.debug("Ожидание нажатия Right Shift")
            try:
                keyboard.wait('right shift')
            except Exception as e:
                logging.error(f"Ошибка: {e}")
                continue

            logging.info("🟢 Активирован. Слушаю...")
            executor.submit(safe_submit, play_sound, SOUNDS['greeting'])

            active_until = time.time() + COMMAND_TIMEOUT
            try:
                with sd.RawInputStream(**stream_kwargs):
                    while time.time() < active_until:
                        try:
                            data = q.get(timeout=0.1)
                        except queue.Empty:
                            continue

                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            text = result.get("text", "").lower()
                            if not text:
                                continue

                            logging.info(f"🗣 Услышал: {text}")
                            cmd_key, keyword = recognize_command(text)
                            if not cmd_key:
                                logging.warning("❌ Команда не распознана")
                                continue

                            command = COMMANDS[cmd_key]
                            if command['sound']:
                                executor.submit(play_sound, command['sound'])
                            if command['action'] in (action_search, action_youtube_search):
                                cleaned = text.replace(keyword, "").strip()
                                executor.submit(safe_submit, command['action'], cleaned)
                            else:
                                executor.submit(safe_submit, command['action'])
                            active_until = time.time() + COMMAND_TIMEOUT

                        while not q.empty():
                            q.get()

            except Exception as e:
                logging.error(f"Ошибка аудиопотока: {e}")
            logging.info("💤 Время ожидания истекло")
            time.sleep(0.3)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Parse CLI args
    if "--setup-autostart" in sys.argv:
        setup_autostart()
        sys.exit(0)
    if "--remove-autostart" in sys.argv:
        remove_autostart()
        sys.exit(0)
    if "--settings" in sys.argv:
        subprocess.Popen(
            ['python', os.path.join(BASE_DIR, 'jarvis_settings.py')],
            cwd=BASE_DIR,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        )
        sys.exit(0)
    if "--key-mode" in sys.argv:
        PASSIVE_LISTEN = False

    print(r"""
       ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
       ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
       ██║███████║██████╔╝██║   ██║██║███████╗
  ██╗  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
  ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
   ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
           Voice Assistant v2.0
    """)

    mic_info = CONFIG.get('microphone_name', 'По умолчанию')
    mode = "🎙 Голосовая активация" if PASSIVE_LISTEN else "⌨️ Клавиша Right Shift"
    print(f"  Режим:      {mode}")
    print(f"  Микрофон:   {mic_info}")
    print(f"  Таймаут:    {COMMAND_TIMEOUT} сек")
    print(f"  Точность:   {FUZZY_THRESHOLD}")
    print(f"  Команд:     {len(COMMANDS)}")
    print(f"  Звуки:      {'Вкл' if SOUND_ENABLED else 'Выкл'}")
    print(f"  Конфиг:     {SETTINGS_FILE}")
    print()

    # System tray
    setup_tray()

    # Greeting sound
    play_sound(SOUNDS['greeting2'])
    time.sleep(2)

    # Start listening
    listen()
