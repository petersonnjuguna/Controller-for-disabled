import tkinter as tk
from tkinter import messagebox, font
import subprocess
import os
import signal
import psutil

# File paths to the corresponding Python scripts
VOICE_FILE = "voice_control.py"  # Replace with the actual path
FACE_GESTURE_FILE = "face_gesture_control.py"  # Replace with the actual path
HAND_GESTURE_FILE = "hand_gesture_control.py"  # Replace with the actual path
WINDOWS_FILE = "windows_control.py"  # Replace with the actual path

# Dictionary to keep track of running processes
running_processes = {
    "voice_control": None,
    "face_gesture_control": None,
    "hand_gesture_control": None,
    "windows_control": None
}

# Function to run a Python script
def run_script(script_path, process_key):
    if os.path.exists(script_path):
        try:
            # Run the script using subprocess
            process = subprocess.Popen(["python", script_path])
            running_processes[process_key] = process
            messagebox.showinfo("Success", f"Started {os.path.basename(script_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start {os.path.basename(script_path)}: {e}")
    else:
        messagebox.showerror("Error", f"File not found: {script_path}")

# Function to kill a running process
def kill_process(process_key):
    process = running_processes.get(process_key)
    if process and process.poll() is None:  # Check if process exists and is still running
        try:
            # Try to terminate gracefully first
            process.terminate()
            
            # Wait a bit for process to terminate
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # If still running, force kill
                process.kill()
                
            running_processes[process_key] = None
            update_status(f"{process_key.replace('_', ' ').title()} stopped")
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop {process_key}: {e}")
            return False
    else:
        messagebox.showinfo("Info", f"No running {process_key.replace('_', ' ').title()} process found")
        running_processes[process_key] = None
        return False

# Function to show the gesture submenu
def show_gesture_submenu():
    # Hide the main frame
    main_frame.pack_forget()
    
    # Show the gesture submenu frame
    gesture_frame.pack(expand=True, fill="both", padx=20, pady=20)

# Function to go back to the main menu
def go_back():
    # Hide the gesture submenu frame
    gesture_frame.pack_forget()
    
    # Show the main frame again
    main_frame.pack(expand=True, fill="both", padx=20, pady=20)

# Create the main Tkinter window
root = tk.Tk()
root.title("Control Panel")
root.configure(bg="#E6E6FA")  # Light purple background

# Make window full screen
root.attributes('-fullscreen', True)

# Add escape key binding to exit fullscreen
root.bind("<Escape>", lambda event: root.attributes("-fullscreen", False))

# Custom font
custom_font = font.Font(family="Helvetica", size=16, weight="bold")
title_font = font.Font(family="Helvetica", size=24, weight="bold")
desc_font = font.Font(family="Helvetica", size=12)

# Title label
title_label = tk.Label(
    root, 
    text="Accessibility Control Panel", 
    font=title_font, 
    bg="#E6E6FA", 
    fg="#4B0082"  # Indigo color for text
)
title_label.pack(pady=(50, 30))  # Increased top padding to move content up

# Create rounded button with description
def create_rounded_button_with_desc(parent, text, description, command, tamil_description, process_key=None):
    # Create a frame to hold button and description
    frame = tk.Frame(parent, bg="#E6E6FA")
    
    # Create the button with rounded corners
    button = tk.Button(
        frame,
        text=text,
        command=command,
        width=15,
        height=7,
        font=custom_font,
        bg="#D8BFD8",
        fg="#4B0082",
        activebackground="#DDA0DD",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2"  # Hand cursor on hover
    )
    
    # Apply rounded corners using canvas
    def create_rounded_button(widget, radius=15):
        # Function to be called when button needs to be drawn
        def _on_configure(event):
            # Get the button's dimensions
            width, height = event.width, event.height
            
            # Create a rounded rectangle on the canvas
            canvas.delete("all")
            canvas.create_rounded_rectangle(0, 0, width, height, radius=radius, fill="#D8BFD8", outline="#9370DB", width=2)
            canvas.create_text(width/2, height/2, text=text, fill="#4B0082", font=custom_font)
            
        # Create a canvas that will sit on top of the button
        canvas = tk.Canvas(frame, highlightthickness=0, bg="#E6E6FA")
        canvas.place(relwidth=1, relheight=1, in_=button)
        
        # Add rounded rectangle creation method to canvas
        tk.Canvas.create_rounded_rectangle = lambda self, x1, y1, x2, y2, radius=25, **kwargs: self.create_polygon(
            x1+radius, y1,
            x2-radius, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2-radius,
            x1, y1+radius,
            smooth=True, **kwargs
        )
        
        # Bind the canvas redraw to configure events (resize)
        canvas.bind("<Configure>", _on_configure)
        
        # Bind click events to the canvas that forward to the button
        canvas.bind("<Button-1>", lambda event: command())
        
        return canvas
    
    canvas = create_rounded_button(button)
    
    # Create description label (English)
    desc_label = tk.Label(
        frame,
        text=description,
        font=desc_font,
        bg="#E6E6FA",
        fg="#4B0082",
        wraplength=250,
        justify=tk.CENTER
    )
    
    # Create Tamil description label
    tamil_desc_label = tk.Label(
        frame,
        text=tamil_description,
        font=desc_font,
        bg="#E6E6FA",
        fg="#800080",  # Darker purple for Tamil text
        wraplength=250,
        justify=tk.CENTER
    )
    
    # Pack components
    button.pack(pady=(0, 10))
    desc_label.pack(pady=5)
    tamil_desc_label.pack(pady=5)
    
    # Add kill button if process_key is provided
    if process_key:
        kill_button = tk.Button(
            frame,
            text="Stop",
            command=lambda: kill_process(process_key),
            bg="#FF6347",  # Tomato color
            fg="white",
            font=("Helvetica", 10, "bold"),
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        kill_button.pack(pady=5)
    
    return frame

# Create frames for main menu and gesture submenu
main_frame = tk.Frame(root, bg="#E6E6FA")
gesture_frame = tk.Frame(root, bg="#E6E6FA")

# Create horizontal frame for buttons in main menu
main_button_frame = tk.Frame(main_frame, bg="#E6E6FA")
main_button_frame.pack(expand=True, fill="both", pady=(0, 50))  # Move buttons up

# Main buttons with descriptions
voice_button_frame = create_rounded_button_with_desc(
    main_button_frame, 
    "Voice\nControl",
    "Control games using voice commands for users with disabilities",
    lambda: [run_script(VOICE_FILE, "voice_control"), update_status("Voice Control activated")],
    "குரல் கட்டுப்பாடு மூலம் விளையாட்டுகளை இயக்கவும்",
    "voice_control"
)

gesture_button_frame = create_rounded_button_with_desc(
    main_button_frame, 
    "Gesture\nControl",
    "Live face gesture control for games and applications",
    show_gesture_submenu,
    "முக சைகை மூலம் விளையாட்டுகளை உயிரோட்டமாக கட்டுப்படுத்தவும்"
)

windows_button_frame = create_rounded_button_with_desc(
    main_button_frame, 
    "System\nControl",
    "Control System elements and get Tamil language assistance",
    lambda: [run_script(WINDOWS_FILE, "windows_control"), update_status("System Control activated")],
    "விண்டோஸ் கூறுகளை கட்டுப்படுத்தி தமிழில் உதவி பெறுங்கள்",
    "windows_control"
)

# Pack main buttons horizontally
voice_button_frame.pack(side=tk.LEFT, padx=20, expand=True)
gesture_button_frame.pack(side=tk.LEFT, padx=20, expand=True)
windows_button_frame.pack(side=tk.LEFT, padx=20, expand=True)

# Create horizontal frame for buttons in gesture submenu
gesture_button_frame = tk.Frame(gesture_frame, bg="#E6E6FA")
gesture_button_frame.pack(expand=True, fill="both", pady=(0, 50))  # Move buttons up

# Gesture submenu buttons with descriptions
face_gesture_frame = create_rounded_button_with_desc(
    gesture_button_frame, 
    "Face\nGesture",
    "Control applications using facial expressions and movements",
    lambda: [run_script(FACE_GESTURE_FILE, "face_gesture_control"), update_status("Face Gesture Control activated")],
    "முக வெளிப்பாடுகள் மூலம் பயன்பாடுகளை கட்டுப்படுத்தவும்",
    "face_gesture_control"
)

hand_gesture_frame = create_rounded_button_with_desc(
    gesture_button_frame, 
    "Hand\nGesture",
    "Control applications using hand movements and gestures",
    lambda: [run_script(HAND_GESTURE_FILE, "hand_gesture_control"), update_status("Hand Gesture Control activated")],
    "கை அசைவுகள் மூலம் பயன்பாடுகளை கட்டுப்படுத்தவும்",
    "hand_gesture_control"
)

back_button_frame = create_rounded_button_with_desc(
    gesture_button_frame, 
    "Back to\nMain Menu",
    "Return to the main menu to access all controls",
    go_back,
    "அனைத்து கட்டுப்பாடுகளையும் அணுக முதன்மை மெனுவிற்குத் திரும்பவும்"
)

# Pack gesture buttons horizontally
face_gesture_frame.pack(side=tk.LEFT, padx=20, expand=True)
hand_gesture_frame.pack(side=tk.LEFT, padx=20, expand=True)
back_button_frame.pack(side=tk.LEFT, padx=20, expand=True)

# Add a status bar at the bottom
status_bar = tk.Label(
    root, 
    text="Ready | தயாராக உள்ளது", 
    bd=1, 
    relief=tk.SUNKEN, 
    anchor=tk.W,
    bg="#D8BFD8",
    fg="#4B0082",
    font=("Helvetica", 12),
    padx=10,
    pady=5
)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

# Function to update status bar
def update_status(message):
    status_bar.config(text=message)
    root.after(3000, lambda: status_bar.config(text="Ready | தயாராக உள்ளது"))

# Add exit button
exit_button = tk.Button(
    root,
    text="Exit",
    command=root.destroy,
    bg="#FF6347",  # Tomato color
    fg="white",
    font=("Helvetica", 12, "bold"),
    relief=tk.FLAT,
    bd=0,
    padx=10,
    pady=5,
    cursor="hand2"
)
exit_button.place(relx=0.95, rely=0.05, anchor=tk.NE)

# Show the main frame initially
main_frame.pack(expand=True, fill="both", padx=20, pady=20)

# Start the Tkinter event loop
root.mainloop()