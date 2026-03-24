# GestOS_final_yr_proj

# Multimodal HCI System

## Installation (Kid-Friendly Guide)
1. **Get Python**: Ask an adult to help you download and install the latest version of Python from [python.org](https://www.python.org/downloads/). During installation, make sure to check the box that says "Add Python to PATH".
2. **Open a Command Window**: Press the Windows Key and type "cmd", then press Enter.
3. **Go to the Folder**: Use `cd` to navigate to the project directory.
4. **Install Tools**: Type `pip install -r requirements.txt` and wait for it to finish.
5. **Check your Mic**: Go to your computer's settings and make sure your microphone is working.
6. **Start the Magic**: Type `python main.py` and watch your computer come to life!

## Features
- **Hand Control**: Move your mouse, click, and scroll just by moving your hands in front of the camera!
- **Voice Commands**: Tell your computer to "volume up", "mute", or "copy/paste".
- **Super Fast**: Uses separate processes for vision and voice so it doesn't lag.
- **Cool Overlay**: See a special window on your screen that shows what the system is doing.

## Technologies Used
- **Python**: The main language used to build the system.
- **MediaPipe**: Used for super fast hand tracking.
- **OpenCV**: Used to see through your webcam.
- **PyQt5**: Used to create the transparent over-screen display.
- **Windows SAPI**: Used to listen to your voice commands on Windows.
- **Vosk**: A backup system that listens if Windows SAPI isn't available.
