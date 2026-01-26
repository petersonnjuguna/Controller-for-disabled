import cv2
import mediapipe as mp
from pynput.keyboard import Controller, Key
import time

# Initialize keyboard controller
keyboard = Controller()

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Gesture mapping to keyboard keys
GESTURES = {
    "jump": Key.up,       # ☝️ Index Finger Up → Jump (Changed to Up Arrow)
    "slide": Key.down,    # 🤘 Rock Sign → Slide
    "left": Key.left,     # 🖐 Open Hand → Move Left
    "right": Key.right    # ✌️ Two Fingers Up → Move Right
}

# Track the last detected gesture to prevent repeated actions
last_gesture = None
last_gesture_time = 0
gesture_cooldown = 1.0  # Cooldown period in seconds

def press_key(action):
    """Simulate a real keypress in the game."""
    if action in GESTURES:
        keyboard.press(GESTURES[action])
        time.sleep(0.1)  # Hold the key for 0.1 seconds
        keyboard.release(GESTURES[action])
        print(f"{action.upper()} Move!")

def detect_gesture(hand_landmarks):
    """Detects which gesture is shown based on finger positions."""
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y
    
    index_base = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
    middle_base = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
    ring_base = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
    pinky_base = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP].y
    
    # Check if fingers are up (1 = extended, 0 = folded)
    fingers = [
        index_tip < index_base,   # Index Finger Up
        middle_tip < middle_base, # Middle Finger Up
        ring_tip < ring_base,     # Ring Finger Up
        pinky_tip < pinky_base    # Pinky Finger Up
    ]
    
    # Recognize gestures
    if fingers == [1, 0, 0, 0]:  
        return "jump"    # ☝️ Index Finger Up → Jump
    elif fingers == [1, 1, 0, 0]:  
        return "right"   # ✌️ Two Fingers Up → Move Right
    elif fingers == [1, 0, 0, 1]:  
        return "slide"   # 🤘 Rock Sign → Slide
    elif fingers == [1, 1, 1, 1]:  
        return "left"    # 🖐 Full Open Hand → Move Left
    elif fingers == [0, 0, 0, 0]:  
        return "none"    # 👊 Closed Fist → Reset Gesture State
    else:
        return "none"

# Start webcam
cap = cv2.VideoCapture(0)

# Display instructions
print("Gesture Controls:")
print("☝️ Index Finger Up → Jump (Up Arrow)")
print("✌️ Two Fingers Up → Move Right (Right Arrow)")
print("🤘 Rock Sign → Slide (Down Arrow)")
print("🖐 Open Hand → Move Left (Left Arrow)")
print("👊 Closed Fist → Reset / Do Nothing")
print("Press 'q' to quit")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        continue
    
    # Flip frame for mirror effect
    frame = cv2.flip(frame, 1)
    
    # Convert frame to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb_frame)
    
    current_time = time.time()
    current_gesture = "none"
    
    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            # Detect gesture
            current_gesture = detect_gesture(hand_landmarks)
    
    # Display the current gesture
    cv2.putText(frame, f"Gesture: {current_gesture}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # Only trigger action if gesture has changed AND cooldown period has passed
    if (current_gesture != "none" and current_gesture != last_gesture and 
            current_time - last_gesture_time > gesture_cooldown):
        press_key(current_gesture)
        last_gesture = current_gesture
        last_gesture_time = current_time
    
    # Reset gesture state when closed fist is detected
    if current_gesture == "none":
        last_gesture = "none"
    
    # Show webcam feed
    cv2.imshow("Gesture Control", frame)
    
    # Exit with 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
