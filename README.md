# GestOS — Multimodal HCI System

> Control your Windows PC using **hand gestures** and **voice commands**. No mouse, no keyboard needed.

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat-square&logo=python)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10-green?style=flat-square)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=flat-square&logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## Table of Contents

- [How It Works](#how-it-works)
- [Hand Gestures](#hand-gestures)
- [Voice Commands](#voice-commands)
- [Safety Mechanisms](#safety-mechanisms)
- [Installation](#installation)
- [Customization Guide](#customization-guide)
- [Tuning](#tuning)
- [Tech Stack](#tech-stack)

---

## How It Works

The system runs as **three separate OS processes** — eliminating the Python GIL bottleneck that causes lag in single-process implementations.

```
┌─────────────────────────────────────────────────────┐
│  Main Process                                        │
│  └── Reads intent queue → executes Windows actions  │
├─────────────────────────────────────────────────────┤
│  Vision Process                                      │
│  └── Camera → MediaPipe → Gesture detection         │
├─────────────────────────────────────────────────────┤
│  Voice Process                                       │
│  └── Microphone → Windows SAPI → Command recognition│
└─────────────────────────────────────────────────────┘
```

Gestures and voice commands both put small intent objects into a shared `multiprocessing.Queue`. The main process reads from that queue and calls the appropriate Windows API. Frames never cross process boundaries.

---

## Hand Gestures

A small always-on-top camera window shows your hand landmarks and the currently detected gesture in real time.

| Gesture | Action |
|---|---|
| ☝️ Index finger up, move hand | Move mouse cursor |
| 🤏 Quick pinch (thumb + index) | Left click |
| 🤏🤏 Two quick pinches | Double click |
| ✌️ Index + middle up, hold 300ms | Right click |
| 🤏 Pinch and hold 350ms, then move | Drag and drop |
| 🤟 Index + middle + ring up | Scroll mode — hand Y position controls up/down |
| ✊ Closed fist, hold 300ms | VLC play / pause |
| 🙌 Both hands open palm, hold 2s | Trigger shutdown/restart confirm window |

---

## Voice Commands

Uses **Windows SAPI with grammar-constrained recognition** — only your exact phrases are matched, giving near-zero false positives and ~100–200ms response time.

### Volume & Brightness

| Command | Action |
|---|---|
| `volume up` / `volume down` | ±10% volume |
| `mute` / `unmute` | Toggle mute |
| `set volume to fifty` | Set exact volume (ten, twenty, ... hundred) |
| `brightness up` / `brightness down` | ±10% brightness |
| `set brightness to fifty` | Set exact brightness (ten, twenty, ... hundred) |

### Mouse & Keyboard

| Command | Action |
|---|---|
| `click` / `single click` | Left click |
| `double click` | Double click |
| `right click` | Right click |
| `copy` / `paste` | Ctrl+C / Ctrl+V |
| `new tab` | Ctrl+T |
| `close tab` | Ctrl+W |
| `next tab` / `previous tab` | Switch tabs |
| `reopen tab` | Ctrl+Shift+T |
| `start dictation` / `stop dictation` | Toggle Windows voice typing (Win+H) |

### Media (VLC)

| Command | Action |
|---|---|
| `play` / `pause` / `play pause` | Toggle VLC playback |
| `next` / `next track` | Next track |
| `previous` / `previous track` | Previous track |
| `stop media` | Stop playback |

### System Controls

| Command | Action |
|---|---|
| `wifi on` / `wifi off` | Enable/disable Wi-Fi |
| `bluetooth on` / `bluetooth off` | Enable/disable Bluetooth |
| `night mode on` / `night mode off` | Toggle Windows Night Light |
| `lock` / `lock screen` | Lock PC immediately |
| `shutdown` / `restart` / `sleep` | Start 7s confirm window |
| `confirm` | Confirm pending action |
| `cancel` | Cancel pending action |
| `stop program` | Close the HCI system |

### Open / Close Applications

| Command | Action |
|---|---|
| `open chrome` / `close chrome` | Google Chrome |
| `open brave` / `close brave` | Brave Browser |
| `open spotify` / `close spotify` | Spotify |
| `open vlc` / `close vlc` | VLC Media Player |
| `open vscode` / `close vs code` | Visual Studio Code |
| `open word` / `close word` | Microsoft Word |
| `open excel` / `close excel` | Microsoft Excel |
| `open powerpoint` / `close powerpoint` | PowerPoint |
| `open steam` / `close steam` | Steam |
| `open epic games` / `close epic games` | Epic Games Launcher |
| `open ea` / `close ea` | EA Desktop |
| `open terminal` / `close terminal` | Windows Terminal |
| `open notepad` / `close notepad` | Notepad |
| `open whatsapp` / `close whatsapp` | WhatsApp |
| `open camera` | Windows Camera |
| `open files` | File Explorer |
| `close window` | Close focused window |

---

## Safety Mechanisms

Shutdown, restart, and sleep require a two-step confirmation to prevent accidental execution.

```
Say "shutdown" / "restart" / "sleep"
        OR hold both hands open palm for 2 seconds
                    ↓
        7-second countdown on camera feed
        "SHUTDOWN: 7" ... "SHUTDOWN: 1"
                    ↓
  Say "confirm" → executes instantly
  Say "cancel"  → cancelled immediately
  Wait 7 seconds → auto-cancelled (safe)
```

> **Note:** The both-hands gesture always triggers `shutdown_request`. To restart or sleep, use voice commands.

---

## Installation

### Requirements

- Windows 10 or 11
- Python **3.10** (exactly — MediaPipe requires this version)
- Working webcam and microphone
- Windows Speech Recognition configured (`Settings → Time & Language → Speech`)

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/gestos.git
cd gestos
```

### 2. Install dependencies

```bash
pip install mediapipe opencv-python pywin32 pycaw comtypes psutil
```

> Optional — Vosk fallback (used automatically if SAPI fails):
> ```bash
> pip install vosk pyaudio
> ```

### 3. Set up app shortcuts

1. Create a folder at `E:\App_path\` (or any path you prefer)
2. Copy `.lnk` shortcuts of your apps into the folder
3. Make sure filenames match exactly: `Google Chrome.lnk`, `Spotify.exe`, etc.
4. If using a different path, update `APP_MAP` in `app_manager.py`

### 4. Run

```bash
python main.py
```

A small camera preview window appears in the corner. Raise your hand to start.

**To stop:** say `stop program`, press `Ctrl+C` in terminal, or press `Q` in the camera window.

---

## Customization Guide

### Quick reference — which file for what

| What to change | File |
|---|---|
| Add / remove / rename a voice phrase | `voice_process.py` |
| Change what a command does | `main.py` |
| Add / remove an app | `app_manager.py` + `voice_process.py` |
| Change an app's install path | `app_manager.py` only |
| Add / modify a gesture | `vision_process.py` |
| Tune cursor sensitivity / dead zones | `vision_process.py` (constants at top) |

---

### Adding a voice command

**Step 1** — Add phrase to `COMMAND_MAP` in `voice_process.py`:
```python
"take screenshot":    ("screenshot", {}),
```

**Step 2** — Add handler to `execute()` in `main.py`:
```python
elif action == "screenshot":
    controller.send_keys("shift+win+s")
```

**Step 3** — Restart. Done.

---

### Removing a voice command

Delete the line from `COMMAND_MAP` in `voice_process.py`. Restart.

---

### Renaming a voice command

Change the key (left side) in `COMMAND_MAP`. The action and handler stay the same:
```python
# Before:
"play pause":   ("vlc_play_pause", {}),

# After:
"toggle play":  ("vlc_play_pause", {}),
```

---

### Adding a new app

**Step 1** — Add to `APP_MAP` in `app_manager.py`:
```python
"telegram": {
    "path":    r"E:\App_path\Telegram.lnk",
    "type":    "shortcut",   # shortcut | exe | uwp
    "process": "Telegram.exe",
},
```

**Step 2** — Add phrases to `COMMAND_MAP` in `voice_process.py`:
```python
"open telegram":   ("open_app",  {"app": "telegram"}),
"close telegram":  ("close_app", {"app": "telegram"}),
```

**Step 3** — Restart. `main.py` needs no changes.

> **App types:** `shortcut` = .lnk file | `exe` = direct executable | `uwp` = Windows Store protocol (e.g. `ms-camera:`)

---

### Removing an app

Delete the entry from `APP_MAP` in `app_manager.py` and the phrases from `COMMAND_MAP` in `voice_process.py`. Restart.

---

### Changing an app's path

Only edit `app_manager.py`:
```python
"chrome": {
    "path": r"D:\CustomLocation\Google Chrome.lnk",  # updated
    ...
},
```

---

## Tuning

### Cursor can't reach screen edges

Edit the dead zone constants at the top of `vision_process.py`:

```python
CAM_X_MIN = 0.15   # left edge of your comfortable hand range
CAM_X_MAX = 0.85   # right edge
CAM_Y_MIN = 0.05   # top edge
CAM_Y_MAX = 0.80   # bottom edge
```

To find your exact values, temporarily add `print(lm[8].x, lm[8].y)` inside the POINT handler, move your finger to each screen edge, and note the printed values.

### Other tuning constants

| Constant | Default | Effect |
|---|---|---|
| `SMOOTH_ALPHA` | 0.35 | Lower = smoother cursor, more lag. Higher = faster, more jitter. |
| `PINCH_DIST` | 0.06 | Raise if accidental clicks occur. Lower if pinch is hard to trigger. |
| `DRAG_HOLD_S` | 0.35 | How long to hold pinch before drag starts. |
| `TWO_FINGER_HOLD` | 0.30 | How long to hold two fingers for right click. |
| `OPEN_PALM_HOLD_S` | 2.0 | How long to hold both palms for shutdown trigger. |

---

## Tech Stack

| Library | Purpose |
|---|---|
| Python 3.10 | Core language |
| MediaPipe | Real-time hand landmark detection (21 points per hand, lite model) |
| OpenCV | Camera capture, frame processing, preview window |
| Windows SAPI | Primary speech recognition — grammar-constrained, ~100–200ms latency |
| Vosk | Fallback speech recognition when SAPI unavailable |
| PyWin32 | Windows API — mouse, keyboard, window management, COM |
| pycaw | Windows audio endpoint control |
| psutil | Process management for closing apps by name |
| multiprocessing | Separate OS processes for vision and voice — eliminates GIL contention |
| screen-brightness-control | Monitor brightness via WMI |

---

## Project Structure

```
gestos/
├── main.py               # Entry point, intent executor
├── vision_process.py     # Camera + gesture detection subprocess
├── voice_process.py      # Speech recognition subprocess
├── windows_controller.py # Windows API wrapper
├── app_manager.py        # App open/close logic and path map
└── requirements.txt
```

---

## License

MIT
