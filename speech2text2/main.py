# main.py
import sounddevice as sd
import vosk
import json
import threading
import queue
import time

# Optional language detection (better if you install langdetect)
try:
    from langdetect import detect
    LANGDETECT_OK = True
except Exception:
    LANGDETECT_OK = False

# ======= Paths to your models (edit if needed) =======
MODEL_EN_PATH = r"C:/Users/prati/OneDrive/Desktop/SignLanguage_Project/speech2text/vosk-model-en-in-0.5"
MODEL_HI_PATH = r"C:/Users/prati/OneDrive/Desktop/SignLanguage_Project/speech2text/vosk-model-small-hi-0.22"

print("Loading models (this may take a while)...")
model_en = vosk.Model(MODEL_EN_PATH)
model_hi = vosk.Model(MODEL_HI_PATH)
print("Models loaded.")

# ======= shared state and synchronization =======
state = {
    "samplerate": 16000,
    "blocksize": 4000,
    "channels": 1,
    "dtype": "int16",
    "mode": "en",            # "en" or "hi"
    "auto_detect": False,
    "running": True,
    "rec": None,             # current recognizer
}
state_lock = threading.Lock()

def make_recognizer(mode):
    """Create and return a fresh recognizer for the requested mode."""
    if mode == "hi":
        return vosk.KaldiRecognizer(model_hi, state["samplerate"])
    else:
        return vosk.KaldiRecognizer(model_en, state["samplerate"])

# init recognizer
with state_lock:
    state["rec"] = make_recognizer(state["mode"])

# queue to receive text outputs from audio callback
out_q = queue.Queue()

# simple Hindi keyword heuristic (fallback if langdetect not installed)
HINDI_KEYWORDS = {"hai","ka","kya","main","hoon","ho","tum","aap","namaste","dhanyavaad","shukriya","kare","kijiye"}

def heuristic_is_hindi(text):
    tokens = set(text.lower().split())
    return len(tokens & HINDI_KEYWORDS) >= 1

def maybe_switch_model_based_on_text(text):
    """If auto-detect is enabled, examine text and switch model if necessary."""
    with state_lock:
        if not state["auto_detect"]:
            return
    if not text:
        return

    # try langdetect first if available
    is_hindi = False
    if LANGDETECT_OK:
        try:
            lang = detect(text)
            # langdetect returns 'hi' for hindi, 'en' for english
            is_hindi = (lang == "hi")
        except Exception:
            # fallback to heuristic
            is_hindi = heuristic_is_hindi(text)
    else:
        is_hindi = heuristic_is_hindi(text)

    desired_mode = "hi" if is_hindi else "en"
    with state_lock:
        if desired_mode != state["mode"]:
            print(f"[auto-detect] switching to {'Hindi' if desired_mode=='hi' else 'English'} model based on text: '{text}'")
            # create a fresh recognizer of the new mode (clears previous state)
            state["mode"] = desired_mode
            state["rec"] = make_recognizer(state["mode"])


def callback(indata, frames, time_info, status):
    """
    sounddevice RawInputStream callback:
    - indata is a CFFI buffer-like object for RawInputStream; convert with bytes().
    - feed bytes to current recognizer.
    """
    # Convert buffer to raw bytes (works for RawInputStream CFFI buffers)
    data_bytes = bytes(indata)

    # Access recognizer thread-safely
    with state_lock:
        rec = state["rec"]

    if rec.AcceptWaveform(data_bytes):
        try:
            result_json = rec.Result()
            result = json.loads(result_json)
        except Exception:
            result = {}

        text = result.get("text", "")
        # send to queue for main thread to print & possibly auto-detect/switch
        out_q.put(text)

# Thread: monitor out_q for recognized texts, print, and possibly auto-switch model
def output_consumer():
    while True:
        try:
            text = out_q.get(timeout=0.5)
        except queue.Empty:
            with state_lock:
                if not state["running"]:
                    break
            continue

        if text:
            print(f"Recognized Text: {text}")
            maybe_switch_model_based_on_text(text)
        else:
            # optionally print partial or empty results for debugging
            # print("Recognized empty text.")
            pass

# Thread: read user commands from stdin to switch languages or toggle auto-detect
def command_listener():
    help_msg = (
        "\nCommands (type and press Enter):\n"
        "  e  -> switch to English model\n"
        "  h  -> switch to Hindi model\n"
        "  a  -> toggle auto-detect (current: {})\n"
        "  q  -> quit\n"
        "  help -> show this message\n"
    ).format("ON" if state["auto_detect"] else "OFF")
    print(help_msg)
    while True:
        try:
            cmd = input().strip().lower()
        except EOFError:
            cmd = "q"
        if cmd == "e":
            with state_lock:
                state["mode"] = "en"
                state["rec"] = make_recognizer("en")
                state["auto_detect"] = False
            print("Switched to English model. Auto-detect OFF.")
        elif cmd == "h":
            with state_lock:
                state["mode"] = "hi"
                state["rec"] = make_recognizer("hi")
                state["auto_detect"] = False
            print("Switched to Hindi model. Auto-detect OFF.")
        elif cmd == "a":
            with state_lock:
                state["auto_detect"] = not state["auto_detect"]
            print("Toggled auto-detect to", "ON" if state["auto_detect"] else "OFF")
        elif cmd == "q":
            with state_lock:
                state["running"] = False
            print("Quitting...")
            break
        elif cmd == "help":
            print(help_msg)
        else:
            print("Unknown command. Type 'help' for commands.")

# Start threads
consumer_thread = threading.Thread(target=output_consumer, daemon=True)
consumer_thread.start()

cmd_thread = threading.Thread(target=command_listener, daemon=True)
cmd_thread.start()

# Start recording (RawInputStream) and keep alive until user quits
try:
    with sd.RawInputStream(samplerate=state["samplerate"],
                           blocksize=state["blocksize"],
                           dtype=state["dtype"],
                           channels=state["channels"],
                           callback=callback):
        print("Listening... Speak now! (type 'help' + Enter for commands)")
        # Keep running until command thread sets running False
        while True:
            with state_lock:
                if not state["running"]:
                    break
            time.sleep(0.2)

except KeyboardInterrupt:
    print("\nStopped listening by Ctrl+C.")
except Exception as e:
    print("Error:", e)

# cleanup
with state_lock:
    state["running"] = False

consumer_thread.join(timeout=1)
print("Program terminated.")
