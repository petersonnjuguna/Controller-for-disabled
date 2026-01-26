import speech_recognition as sr

# Mapping of voice commands to controller inputs (ASCII values)
command_to_ascii = {
    "up": ord('U'),  # Assuming 'U' for 'up' direction
    "down": ord('D'),  # Assuming 'D' for 'down' direction
    "left": ord('L'),  # Assuming 'L' for 'left' direction
    "right": ord('R'),  # Assuming 'R' for 'right' direction
    "start": ord('S'),  # Assuming 'S' for 'start'
    "stop": ord('X'),  # Assuming 'X' for 'stop'
    # Add more commands as needed
}

def recognize_voice_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for voice command...")
        audio = recognizer.listen(source)
        try:
            # Use Google's speech recognition engine (could be any other)
            command = recognizer.recognize_google(audio)
            print(f"Recognized command: {command}")
            return command.lower()  # Convert command to lowercase for easier mapping
        except sr.UnknownValueError:
            print("Sorry, could not understand the command.")
            return None
        except sr.RequestError:
            print("Request error from the speech recognition service.")
            return None

def convert_command_to_ascii(command):
    if command in command_to_ascii:
        ascii_value = command_to_ascii[command]
        print(f"Command '{command}' corresponds to ASCII value: {ascii_value}")
        return ascii_value
    else:
        print(f"Command '{command}' is not recognized.")
        return None

# Main execution
if __name__ == "__main__":
    voice_command = recognize_voice_command()
    if voice_command:
        ascii_value = convert_command_to_ascii(voice_command)
        if ascii_value:
            # Now you can send the ASCII value to the controller
            # For example, simulate controller input using the ASCII value
            print(f"Sending ASCII value {ascii_value} to the controller.")
