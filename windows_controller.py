import win32api
import win32con
import win32gui
import ctypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import subprocess
import time
from enum import Enum

class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"

class WindowsController:
    def __init__(self):
        self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        # Audio Volume Interface Setup (Lazy init to prevent startup lag)
        self._volume_interface = None

    def _get_volume_interface(self):
        if self._volume_interface is None:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            except Exception as e:
                print(f"Error initializing audio interface: {e}")
                return None
        return self._volume_interface

    def move_mouse(self, x: int, y: int):
        """Moves mouse absolute position (clamped to screen)."""
        x = max(0, min(x, self.screen_width))
        y = max(0, min(y, self.screen_height))
        # Use SendInput for more robust movement in some games/apps, but SetCursorPos is fine for desktop
        win32api.SetCursorPos((x, y))

    def click(self, button: MouseButton = MouseButton.LEFT):
        """Clicks the specified mouse button."""
        x, y = win32api.GetCursorPos()
        if button == MouseButton.LEFT:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        elif button == MouseButton.RIGHT:
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
        elif button == MouseButton.MIDDLE:
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, x, y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, x, y, 0, 0)

    def start_drag(self):
        """Holds down the left mouse button."""
        x, y = win32api.GetCursorPos()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)

    def end_drag(self):
        """Releases the left mouse button."""
        x, y = win32api.GetCursorPos()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def send_keys(self, keys: str):
        """Simulates key presses. Simple wrapper, can be expanded for complex combos."""
        # For simplicity in V1, we accept a few known shortcuts or single keys
        # Expand this with a proper mapping or use keyboard library if needed
        # Current naive implementation for specific commands in plan
        
        # Parse keys like 'ctrl+c'
        parts = keys.lower().split('+')
        vk_codes = []
        
        key_map = {
            'ctrl': win32con.VK_CONTROL,
            'shift': win32con.VK_SHIFT,
            'alt': win32con.VK_MENU,
            'c': 0x43, 'v': 0x56, 'a': 0x41,
            'up': win32con.VK_UP, 'down': win32con.VK_DOWN,
            'left': win32con.VK_LEFT, 'right': win32con.VK_RIGHT,
            'pageup': win32con.VK_PRIOR, 'pagedown': win32con.VK_NEXT,
            'space': win32con.VK_SPACE,
            'enter': win32con.VK_RETURN,
            'esc': win32con.VK_ESCAPE,
            'f11': win32con.VK_F11  # For fullscreen
        }
        
        for p in parts:
            if p in key_map:
                vk_codes.append(key_map[p])
            else:
                # Fallback for single char
                if len(p) == 1:
                     vk_codes.append(ord(p.upper()))

        # Press all
        for vk in vk_codes:
            win32api.keybd_event(vk, 0, 0, 0)
            
        # Release all (reversed)
        for vk in reversed(vk_codes):
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def set_volume(self, level: int):
        """Set volume to absolute level 0-100."""
        try:
            interface = self._get_volume_interface()
            if interface:
                scalar = max(0.0, min(1.0, level / 100.0))
                interface.SetMasterVolumeLevelScalar(scalar, None)
                print(f"[WinCtrl] Volume set to {level}%")
        except Exception as e:
            print(f"[WinCtrl] set_volume error: {e}")

    def adjust_volume(self, delta: int):
        """Adjust volume by delta (-100 to +100)."""
        try:
            interface = self._get_volume_interface()
            if interface:
                current = interface.GetMasterVolumeLevelScalar()
                new_level = max(0.0, min(1.0, current + delta / 100.0))
                interface.SetMasterVolumeLevelScalar(new_level, None)
                print(f"[WinCtrl] Volume: {int(current*100)}% → {int(new_level*100)}%")
        except Exception as e:
            print(f"[WinCtrl] adjust_volume error: {e}")

    def set_brightness(self, level: int):
        """Set brightness 0-100 via WMI/Powershell."""
        level = max(0, min(100, level))
        cmd = f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
        subprocess.Popen(["powershell", "-Command", cmd], creationflags=subprocess.CREATE_NO_WINDOW)

    def adjust_brightness(self, delta: int):
        """Adjust brightness relative."""
        # Need to read current brightness first? WMI read is slow.
        # Implementation Plan says "brightness up/down", usually steps of 10
        # For V1, we can try to guess or just use Set with stored state?
        # Better: Read it.
        try:
             cmd_read = "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness"
             result = subprocess.check_output(["powershell", "-Command", cmd_read], creationflags=subprocess.CREATE_NO_WINDOW)
             current = int(result.strip())
             new_level = current + delta
             self.set_brightness(new_level)
        except Exception as e:
            print(f"Error adjusting brightness: {e}")

    def toggle_mute(self):
        """Toggles system mute."""
        vk = win32con.VK_VOLUME_MUTE
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    def get_active_window(self) -> str:
        """Returns the title of the active window."""
        try:
            window = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(window)
        except Exception:
            return ""

    def shutdown(self, countdown_seconds: int):
        """Initiate system shutdown."""
        # /s = shutdown, /t = time
        subprocess.Popen(["shutdown", "/s", "/t", str(countdown_seconds)], creationflags=subprocess.CREATE_NO_WINDOW)

    def lock_screen(self):
        """Lock the workstation."""
        ctypes.windll.user32.LockWorkStation()
