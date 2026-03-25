# GestOS_final_yr_proj

# Multimodal HCI System

Welcome to the **Multimodal Human-Computer Interaction (HCI) System**! This project lets you control your computer using **hand gestures** through your webcam and **voice commands** through your microphone. It's like having magic powers for your PC!

## ✨ Features

### ✋ Hand Gestures (Camera)
- **Move Mouse:** Point your index finger up and move your hand.
- **Click:** Do the **PINCH** gesture (quickly pinch your thumb and index finger MCP together).
- **Double Click:** Do the **PINCH** gesture twice quickly.
- **Right Click:** Do the **TWO_FINGER** gesture (hold your index and middle fingers up for a moment).
- **Drag & Drop:** Do the **PINCH** gesture and hold it, move your hand, and release it to drop.
- **Scroll:** Hold 3 fingers up (index, middle, ring). Move your hand up to scroll up, or down to scroll down.
- **System Shutdown:** Hold both hands up with all fingers open (open palms) for 2 seconds.

### 🗣️ Voice Commands (Microphone)
- **Computer Controls:** Say *"volume up/down"*, *"set volume to fifty"*, *"mute"*, or *"brightness up/down"*.
- **Mouse & Keyboard:** Say *"click"*, *"double click"*, *"right click"*, *"copy"*, or *"paste"*. 
- **Application Management:** Say *"open chrome"*, *"close spotify"*, *"open vscode"*, *"close tab"*, etc.

### 🚀 Supported Magic Apps
You can use voice commands to open or close any of these supported apps:
- **Browsers:** Chrome, Brave
- **Games:** Steam, Epic Games, EA
- **Office:** Word, Excel, PowerPoint
- **Tools & Fun:** VS Code, Terminal, Spotify, WhatsApp, Files, Camera, Notepad

---

## 🛠️ Technologies Used

This project is built using some awesome, modern programming tools:
- **Python (3.10):** The core programming language that glues everything together.
- **MediaPipe:** Google's super-fast AI vision tool that detects exactly where your hand and fingers are.
- **OpenCV (`cv2`):** Used for capturing live video from your camera and drawing the cool debug window.
- **Windows SAPI / Vosk:** Used to listen to your voice and turn your spoken words into text commands.
- **PyWin32 (`win32api`, `win32gui`, `win32con`):** Allows Python to take control of your Windows mouse, keyboard, and open windows.
- **PsUtil:** Helps Python safely find and close running applications.
- **Multiprocessing:** Runs the camera and the microphone at the exact same time without slowing each other down!

---

## 🎮 Installation (Kid-Friendly Guide!)

Ready to set up your magic computer controller? Ask an adult to help you with these steps!

### Step 1: Install Python (Super Important!)
You absolutely need **Python 3.10** for this to work properly! 
1. Go to the official Python website and download **Python 3.10**.
2. When installing, **make sure to check the box at the bottom that says "Add Python to PATH"** before you click Install.

### Step 2: Set up the App Shortcuts
For the "open [app]" voice commands to work, the system needs to know where your apps live.
1. Create a folder exactly named `E:\App_path\` on your computer. (if you do not have E drive just create it in any desired path and map those paths to "app_manager.py". just add the path to the APP_MAP dictionary in app_manager.py file. and also add the voice command to the COMMAND_MAP dictionary in voice_process.py file. )
2. Copy the shortcuts (`.lnk` files) of your favorite apps (like Chrome, Word, Spotify) into this folder.
3. Make sure the names match our app list exactly (like `Google Chrome.lnk` or `Spotify.exe`).
4. Boiler plate is provide within app_manager.py file. if you want to add more apps just add the path to the APP_MAP dictionary in app_manager.py file. and also add the voice command to the COMMAND_MAP dictionary in voice_process.py file.

### Step 3: Install the Magic Packages
We need to download the special tools that make the magic happen. Open your computer's Terminal (or Command Prompt) and copy-paste this command, then press Enter:
```cmd
pip install mediapipe opencv-python pywin32 pycaw comtypes psutil
```
*(Optional: If you want to use the backup offline voice recognition, also run: `pip install vosk pyaudio`)*

### Step 4: Run the Magic!
You are all set! In your Terminal, go to the folder where you saved this project and type:
```cmd
python main.py
```
A small camera window will pop up. Raise your hand, point your finger, and start controlling your computer like a wizard! Say *"close window"* to close apps, or press `Ctrl+C` in the terminal to stop the magic.

- **Python**: The main language used to build the system.
- **MediaPipe**: Used for super fast hand tracking.
- **OpenCV**: Used to see through your webcam.
- **PyQt5**: Used to create the transparent over-screen display.
- **Windows SAPI**: Used to listen to your voice commands on Windows.
- **Vosk**: A backup system that listens if Windows SAPI isn't available.
