import cv2
import mediapipe as mp
import keyboard
import time

# Initialize MediaPipe Face Mesh detector
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,  # Only track one face for stability
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Start video capture
cap = cv2.VideoCapture(0)

# Setup for tracking face position
initial_nose_x = None
initial_nose_y = None
active_keys = set()  # Set to track which keys are currently active

# Configuration
move_threshold_x = 0.02  # Horizontal movement threshold
move_threshold_y = 0.03  # Vertical movement threshold
mouth_open_threshold = 0.03  # Threshold for mouth open detection

# Control mapping
control_scheme = {
    'forward': 'w',    # Accelerate
    'backward': 's',   # Brake/Reverse
    'left': 'a',       # Steer left
    'right': 'd',      # Steer right
    'nitro': 'shift',  # Nitro boost (activated by opening mouth)
    'handbrake': 'shift'  # Handbrake/Drift
}

# Debug info
show_debug = True
calibration_time = 0

print("=== NFS Face Controller ===")
print("Tilt your head to steer left/right")
print("Move your head up/down to accelerate/brake")
print("Open your mouth to activate nitro (shift)")
print("Press 'c' to recalibrate")
print("Press 'q' to quit")

try:
    while True:
        # Capture frame from the camera
        ret, frame = cap.read()
        if not ret:
            break
        
        # Flip the frame horizontally for a mirrored effect
        frame = cv2.flip(frame, 1)
        
        # Convert BGR image to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect face landmarks
        result = face_mesh.process(rgb_frame)
        height, width, _ = frame.shape
        
        # Get current time
        current_time = time.time()
        
        # Handle key presses
        if keyboard.is_pressed('c'):
            initial_nose_x = None
            initial_nose_y = None
            calibration_time = current_time
            print("Recalibrating center position...")
        
        # Reset if face is not detected
        if not result.multi_face_landmarks:
            # Release all active keys
            for key in active_keys:
                keyboard.release(key)
            active_keys.clear()
            
            cv2.putText(frame, "No face detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            face_landmarks = result.multi_face_landmarks[0]  # Get the first face
            
            # Get nose tip coordinates (landmark 1 in MediaPipe Face Mesh)
            nose_landmark = face_landmarks.landmark[1]
            nose_x = nose_landmark.x
            nose_y = nose_landmark.y
            
            # Get mouth landmarks for detecting open mouth
            # Upper lip: landmark 13, Lower lip: landmark 14
            upper_lip = face_landmarks.landmark[13]
            lower_lip = face_landmarks.landmark[14]
            mouth_distance = abs(lower_lip.y - upper_lip.y)
            
            # Draw mouth points for visualization
            upper_lip_x, upper_lip_y = int(upper_lip.x * width), int(upper_lip.y * height)
            lower_lip_x, lower_lip_y = int(lower_lip.x * width), int(lower_lip.y * height)
            cv2.circle(frame, (upper_lip_x, upper_lip_y), 3, (0, 255, 255), -1)
            cv2.circle(frame, (lower_lip_x, lower_lip_y), 3, (0, 255, 255), -1)
            
            # Draw nose point for visualization
            screen_x, screen_y = int(nose_x * width), int(nose_y * height)
            cv2.circle(frame, (screen_x, screen_y), 5, (0, 255, 0), -1)
            
            # Set initial position if not set
            if initial_nose_x is None or initial_nose_y is None:
                if current_time - calibration_time > 0.5:  # Wait a bit after calibration request
                    initial_nose_x = nose_x
                    initial_nose_y = nose_y
                    print(f"Center calibrated at X: {initial_nose_x:.3f}, Y: {initial_nose_y:.3f}")
                    cv2.circle(frame, (screen_x, screen_y), 10, (255, 0, 0), 2)  # Mark initial position
            else:
                # Calculate movement from initial position
                delta_x = nose_x - initial_nose_x
                delta_y = nose_y - initial_nose_y
                
                # Determine active controls based on face position
                new_active_keys = set()
                
                # Horizontal movement (steering)
                if delta_x > move_threshold_x:
                    new_active_keys.add(control_scheme['right'])
                elif delta_x < -move_threshold_x:
                    new_active_keys.add(control_scheme['left'])
                
                # Vertical movement (acceleration/braking)
                if delta_y < -move_threshold_y:  # Up = accelerate
                    new_active_keys.add(control_scheme['forward'])
                elif delta_y > move_threshold_y:  # Down = brake
                    new_active_keys.add(control_scheme['backward'])
                
                # Open mouth detection for nitro
                if mouth_distance > mouth_open_threshold:
                    new_active_keys.add(control_scheme['nitro'])
                    # Draw indicator for mouth open
                    cv2.line(frame, (upper_lip_x, upper_lip_y), (lower_lip_x, lower_lip_y), (0, 0, 255), 2)
                    cv2.putText(frame, "NITRO!", (lower_lip_x + 10, lower_lip_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Press new keys that weren't active before
                for key in new_active_keys:
                    if key not in active_keys:
                        keyboard.press(key)
                
                # Release keys that are no longer active
                for key in active_keys:
                    if key not in new_active_keys:
                        keyboard.release(key)
                
                # Update active keys
                active_keys = new_active_keys
                
                # Draw direction indicators
                cv2.putText(frame, "Active Controls:", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_pos = 60
                for key in active_keys:
                    for name, control_key in control_scheme.items():
                        if key == control_key:
                            cv2.putText(frame, f"- {name.upper()}", (20, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            y_pos += 25
                
                # Show debug info
                if show_debug:
                    cv2.putText(frame, f"Delta X: {delta_x:.3f}", (width - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    cv2.putText(frame, f"Delta Y: {delta_y:.3f}", (width - 200, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    cv2.putText(frame, f"Mouth: {mouth_distance:.3f}", (width - 200, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    cv2.putText(frame, f"Center: ({initial_nose_x:.3f}, {initial_nose_y:.3f})", (width - 200, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    
                    # Draw threshold lines
                    center_x, center_y = int(initial_nose_x * width), int(initial_nose_y * height)
                    thresh_left = int((initial_nose_x - move_threshold_x) * width)
                    thresh_right = int((initial_nose_x + move_threshold_x) * width)
                    thresh_top = int((initial_nose_y - move_threshold_y) * height)
                    thresh_bottom = int((initial_nose_y + move_threshold_y) * height)
                    
                    # Draw threshold box
                    cv2.rectangle(frame, (thresh_left, thresh_top), (thresh_right, thresh_bottom), (255, 255, 0), 1)
                    cv2.circle(frame, (center_x, center_y), 3, (255, 0, 0), -1)
        
        # Display the video frame
        cv2.imshow("NFS Face Controller", frame)
        
        # Exit on pressing 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Cleanup - release all keys before exiting
    for key in active_keys:
        keyboard.release(key)
    
    # Release video capture and close all windows
    cap.release()
    cv2.destroyAllWindows()
    print("Controller stopped.")
