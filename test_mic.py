import sounddevice as sd
import numpy as np
import time

print(sd.query_devices())

def callback(indata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    rms = np.sqrt(np.mean(np.frombuffer(indata, dtype=np.int16).astype(float) ** 2))
    print(f"RMS: {rms:.2f}")

try:
    with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16', channels=1, callback=callback):
        print("Listening for 3 seconds...")
        time.sleep(3)
except Exception as e:
    print(f"Error: {e}")
