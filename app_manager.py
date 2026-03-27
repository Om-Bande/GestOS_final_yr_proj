"""
app_manager.py — open and close applications via voice commands.

To add a new app:
    1. Add the shortcut/exe to E:\\App_path\\
    2. Add one entry to APP_MAP below
    3. Add the voice phrase to COMMAND_MAP in voice_process.py
    That's it — no other file needs to change.

To change an app's path:
    Just update the path in APP_MAP below.
"""

import os
import subprocess
import win32gui
import win32con
import win32process
import psutil


# ── App map ────────────────────────────────────────────────────────────────
# "app_key" : {
#     "path"    : full path to .lnk / .exe / UWP protocol string,
#     "type"    : "shortcut" | "exe" | "uwp",
#     "process" : process name for taskkill (None for UWP apps)
# }
#
# To add a new app — add one entry here and one line in voice_process.py

APP_MAP: dict[str, dict] = {
    "brave": {
        "path":    r"E:\App_path\Brave.lnk",
        "type":    "shortcut",
        "process": "brave.exe",
    },
    "ea": {
        "path":    r"E:\App_path\EA.lnk",
        "type":    "shortcut",
        "process": "EADesktop.exe",
    },
    "epic games": {
        "path":    r"E:\App_path\Epic Games Launcher.lnk",
        "type":    "shortcut",
        "process": "EpicGamesLauncher.exe",
    },
    "excel": {
        "path":    r"E:\App_path\Excel.lnk",
        "type":    "shortcut",
        "process": "EXCEL.EXE",
    },
    "files": {
        "path":    r"E:\App_path\File Explorer.lnk",
        "type":    "shortcut",
        "process": "explorer.exe",
    },
    "chrome": {
        "path":    r"E:\App_path\Google Chrome.lnk",
        "type":    "shortcut",
        "process": "chrome.exe",
    },
    "powerpoint": {
        "path":    r"E:\App_path\PowerPoint.lnk",
        "type":    "shortcut",
        "process": "POWERPNT.EXE",
    },
    "spotify": {
        "path":    r"E:\App_path\Spotify.exe",
        "type":    "exe",
        "process": "Spotify.exe",
    },
    "steam": {
        "path":    r"E:\App_path\Steam.lnk",
        "type":    "shortcut",
        "process": "steam.exe",
    },
    "vscode": {
        "path":    r"E:\App_path\Visual Studio Code.lnk",
        "type":    "shortcut",
        "process": "Code.exe",
    },
    "word": {
        "path":    r"E:\App_path\Word.lnk",
        "type":    "shortcut",
        "process": "WINWORD.EXE",
    },
    # ── ADDED: VLC ─────────────────────────────────────────────────────────
    "vlc": {
        "path":    r"E:\App_path\VLC media player.lnk",
        "type":    "shortcut",
        "process": "vlc.exe",
    },
    # ── END ADDED ──────────────────────────────────────────────────────────
    # ── No shortcut needed — launched directly ─────────────────────────
    "notepad": {
        "path":    "notepad.exe",
        "type":    "exe",
        "process": "notepad.exe",
    },
    "terminal": {
        "path":    "wt.exe",
        "type":    "exe",
        "process": "WindowsTerminal.exe",
    },
    "camera": {
        "path":    "ms-camera:",
        "type":    "uwp",
        "process": None,   # UWP — can't kill by process name reliably
    },
    "whatsapp": {
        "path":    "ms-chat:",
        "type":    "uwp",
        "process": "WhatsApp.exe",
    },
}


# ── Open ───────────────────────────────────────────────────────────────────

def open_app(app_key: str) -> bool:
    """
    Opens the app by key (must match a key in APP_MAP).
    Returns True on success, False on failure.
    """
    entry = APP_MAP.get(app_key)
    if not entry:
        print(f"[AppManager] Unknown app: '{app_key}'")
        return False

    path = entry["path"]
    kind = entry["type"]

    try:
        if kind in ("shortcut", "uwp"):
            # os.startfile handles .lnk shortcuts and UWP protocol strings (ms-camera: etc.)
            os.startfile(path)
        elif kind == "exe":
            # Direct exe — use Popen so it doesn't block
            subprocess.Popen(path, creationflags=subprocess.CREATE_NO_WINDOW)

        print(f"[AppManager] Opened: {app_key}")
        return True

    except FileNotFoundError:
        print(f"[AppManager] Path not found: {path}")
        return False
    except Exception as e:
        print(f"[AppManager] Failed to open '{app_key}': {e}")
        return False


# ── Close by app name (kill all instances) ─────────────────────────────────

def close_app(app_key: str) -> bool:
    """
    Kills all running instances of the app by process name.
    Used when user says "close chrome", "close spotify" etc.
    Returns True if at least one process was killed.
    """
    entry = APP_MAP.get(app_key)
    if not entry:
        print(f"[AppManager] Unknown app: '{app_key}'")
        return False

    process_name = entry.get("process")
    if not process_name:
        print(f"[AppManager] No process name for '{app_key}' (UWP app — use close tab instead)")
        return False

    killed = 0
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"].lower() == process_name.lower():
                proc.terminate()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if killed:
        print(f"[AppManager] Closed {killed} instance(s) of {process_name}")
        return True
    else:
        print(f"[AppManager] No running instances of {process_name} found")
        return False


# ── Close foreground window (close tab / close window) ────────────────────

def close_foreground_window() -> bool:
    """
    Sends WM_CLOSE to whatever window is currently in the foreground.
    Used for "close tab" and "close window" voice commands.
    Safer than killing the process — lets the app handle unsaved changes.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            title = win32gui.GetWindowText(hwnd)
            print(f"[AppManager] Closed foreground window: '{title}'")
            return True
    except Exception as e:
        print(f"[AppManager] close_foreground_window error: {e}")
    return False
