import threading
import pyaudio
import vosk
import json
import keyboard
import time
import os
import wave
import numpy as np
from datetime import datetime

# Configuration
CONFIG = {
    "model_path": r"C:\Users\ashwi\Downloads\vosk-model-small-en-us-0.15\vosk-model-small-en-us-0.15",
    "sample_rate": 16000,
    "buffer_size": 1024,  # Increased for better word capture
    "channels": 1,
    "debug_mode": False,  # Set to False to disable debugging features
    "save_audio": True,  # Save problematic audio for debugging
    "debug_folder": "debug_audio",
    "energy_threshold": 300,  # Adjust based on your microphone and environment
    "pause_threshold": 0.5,  # Seconds of silence to consider end of speech
}

# Create debug folder if it doesn't exist
if CONFIG["debug_mode"] and CONFIG["save_audio"]:
    os.makedirs(CONFIG["debug_folder"], exist_ok=True)

# Commands with alternatives to improve recognition
COMMANDS = {
    "up": "w", "move up": "w", "go up": "w", "jump": "w", "ump": "w",
    "down": "s", "nou": "s", "move down": "s", "now": "s", "go down": "s", "dawn": "s", "don't": "s",
    "left": "a", "move left": "a", "go left": "a", "lift": "a", "lef": "a",
    "right": "d", "move right": "d", "go right": "d", "write": "d", "rite": "d", "rate": "d",
    "space": "space", "press space": "space", "spase": "space", "spice": "space",
    "select": "enter", "enter": "enter", "confirm": "enter", "inter": "enter", "and her": "enter", "in to": "enter",
    "stop": "esc", "escape": "esc", "cancel": "esc", "exit": "esc", "esc": "esc", "scap": "esc", "es cape": "esc",
}

# Initialize audio and recognition components
print("Initializing speech recognition system...")
try:
    model_alternatives = [
        CONFIG["model_path"],
        r"C:\Users\james\OneDrive\Documents\College\Project\vosk-model-small-en-in-0.4\vosk-model-small-en-in-0.4",
        r"C:\Users\james\OneDrive\Documents\College\Project\vosk-model-en-us-0.22",
    ]

    model = None
    for model_path in model_alternatives:
        if os.path.exists(model_path):
            print(f"Loading model from: {model_path}")
            model = vosk.Model(model_path)
            break

    if model is None:
        print("No valid model found! Using the original path.")
        model = vosk.Model(CONFIG["model_path"])

    recognizer = vosk.KaldiRecognizer(model, CONFIG["sample_rate"])
    recognizer.SetWords(True)  # Enable word timing info for better analysis

    audio = pyaudio.PyAudio()

except Exception as e:
    print(f"Error initializing speech recognition: {e}")
    raise

def save_debug_audio(audio_data, filename_prefix="speech"):
    """Save audio data to WAV file for debugging."""
    if not CONFIG["save_audio"] or not CONFIG["debug_mode"]:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(CONFIG["debug_folder"], f"{filename_prefix}_{timestamp}.wav")

    if not isinstance(audio_data, np.ndarray):
        audio_data = np.frombuffer(audio_data, dtype=np.int16)

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CONFIG["channels"])
        wf.setsampwidth(2)  # 2 bytes = 16 bits
        wf.setframerate(CONFIG["sample_rate"])
        wf.writeframes(audio_data.tobytes())

    if CONFIG["debug_mode"]:
        print(f"Saved debug audio to: {filename}")
    return filename

def calculate_energy(audio_data):
    """Calculate the energy level of an audio buffer."""
    if isinstance(audio_data, bytes):
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
    else:
        audio_array = audio_data

    energy = np.sqrt(np.mean(audio_array.astype(np.float32)**2))
    return energy

def press_key(command):
    """Press the key corresponding to the recognized command."""
    key = COMMANDS.get(command.lower())
    if key:
        if CONFIG["debug_mode"]:
            print(f"Executing command: '{command}' → pressing '{key}'")
        keyboard.press_and_release(key)
        return True
    return False

def listen_for_speech():
    """Listen for speech with improved noise handling and speech detection."""
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=CONFIG["channels"],
        rate=CONFIG["sample_rate"],
        input=True,
        frames_per_buffer=CONFIG["buffer_size"]
    )

    print("Listening...")  # Print "Listening..." initially

    is_speaking = False
    speech_buffer = bytearray()
    silence_frames = 0
    required_silence_frames = int(CONFIG["pause_threshold"] * CONFIG["sample_rate"] / CONFIG["buffer_size"])

    try:
        while True:
            data = stream.read(CONFIG["buffer_size"], exception_on_overflow=False)
            energy = calculate_energy(data)

            if energy > CONFIG["energy_threshold"]:
                if not is_speaking:
                    print("Speech detected!")  # Print when speech is detected
                    is_speaking = True
                    speech_buffer = bytearray()

                speech_buffer.extend(data)
                silence_frames = 0
            else:
                if is_speaking:
                    speech_buffer.extend(data)
                    silence_frames += 1

                    if silence_frames >= required_silence_frames:
                        print("\nProcessing speech segment...")

                        if CONFIG["save_audio"]:
                            save_debug_audio(speech_buffer, "speech")

                        recognizer.Reset()
                        result = None

                        recognizer.AcceptWaveform(bytes(speech_buffer))
                        result = json.loads(recognizer.FinalResult())

                        text = result.get("text", "").lower().strip()
                        if text:
                            print(f"Recognized: '{text}'")
                            if CONFIG["debug_mode"]:
                                if "alternatives" in result:
                                    print(f"Alternatives: {result['alternatives']}")

                            command_executed = False
                            for command in COMMANDS:
                                if command in text:
                                    press_key(command)
                                    command_executed = True
                                    break

                            if not command_executed:
                                for word in text.split():
                                    if press_key(word):
                                        command_executed = True
                                        break

                            if not command_executed:
                                if CONFIG["debug_mode"]:
                                    print(f"Command not recognized in: '{text}'")
                        else:
                            if CONFIG["debug_mode"]:
                                print("No speech recognized!")

                        is_speaking = False
                        speech_buffer = bytearray()
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()

def run_voice_command_system():
    """Main function to run the voice command system."""
    speech_thread = threading.Thread(target=listen_for_speech)
    speech_thread.daemon = True
    speech_thread.start()

    if CONFIG["debug_mode"]:
        print("\nVoice command system is running.")
        print("Available commands:")
        command_groups = {}
        for cmd, key in COMMANDS.items():
            if key not in command_groups:
                command_groups[key] = []
            command_groups[key].append(cmd)

        for key, cmds in command_groups.items():
            print(f'  Say {" or ".join([f"{c}" for c in cmds])} → presses "{key}"')


        print("\nPress Ctrl+C to exit")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting voice command system...")

if __name__ == "__main__":
    run_voice_command_system()
