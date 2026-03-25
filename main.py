"""
main.py — entry point.

Starts two subprocesses (vision, voice), then sits in a loop
reading intents and executing PC actions. That's it.
"""

import sys
import multiprocessing as mp
import win32api
import win32con

from windows_controller import WindowsController, MouseButton
from vision_process import vision_process_entry
from voice_process import voice_process_entry
# ADDED: app manager for open/close application commands
from app_manager import open_app, close_app, close_foreground_window


def execute(controller: WindowsController, action: str, params: dict):
    if action == "move_cursor":
        controller.move_mouse(params["x"], params["y"])

    elif action == "click":
        controller.click()
    elif action == "double_click":
        controller.click()
        controller.click()
    elif action == "right_click":
        controller.click(button=MouseButton.RIGHT)

    elif action == "drag_start":
        controller.move_mouse(params["x"], params["y"])
        controller.start_drag()
    elif action == "drag_move":
        controller.move_mouse(params["x"], params["y"])
    elif action == "drag_end":
        controller.end_drag()

    elif action == "scroll_up":
        controller.scroll(120)
    elif action == "scroll_down":
        controller.scroll(-120)

    elif action == "volume_up":
        controller.adjust_volume(10)
    elif action == "volume_down":
        controller.adjust_volume(-10)
    elif action == "volume_set":
        controller.set_volume(params.get("level", 50))
    elif action == "mute":
        controller.toggle_mute()

    elif action == "brightness_up":
        controller.adjust_brightness(10)
    elif action == "brightness_down":
        controller.adjust_brightness(-10)
    elif action == "brightness_set":
        controller.set_brightness(params.get("level", 50))

    elif action == "copy":
        controller.send_keys("ctrl+c")
    elif action == "paste":
        controller.send_keys("ctrl+v")

    # ── ADDED: App open/close handlers ────────────────────────────────────
    elif action == "open_app":
        open_app(params.get("app", ""))

    elif action == "close_app":
        close_app(params.get("app", ""))

    elif action == "close_window":
        close_foreground_window()
    # ── END ADDED ──────────────────────────────────────────────────────────


def main():
    mp.set_start_method("spawn", force=True)

    intent_queue = mp.Queue(maxsize=30)
    status_queue = mp.Queue(maxsize=5)   # voice → vision display

    controller = WindowsController()

    vision_proc = mp.Process(
        target=vision_process_entry,
        args=(intent_queue, status_queue, controller.screen_width, controller.screen_height),
        name="VisionProcess",
        daemon=True,
    )
    voice_proc = mp.Process(
        target=voice_process_entry,
        args=(intent_queue, status_queue),
        name="VoiceProcess",
        daemon=True,
    )

    vision_proc.start()
    voice_proc.start()
    print("[Main] Running. Close camera window or Ctrl+C to stop.")

    try:
        while True:
            try:
                msg = intent_queue.get(timeout=0.05)
            except Exception:
                continue
            try:
                execute(controller, msg["action"], msg.get("params", {}))
            except Exception as e:
                print(f"[Main] Error on '{msg.get('action')}': {e}")

    except KeyboardInterrupt:
        print("[Main] Stopping...")
    finally:
        vision_proc.terminate()
        voice_proc.terminate()
        vision_proc.join(timeout=2)
        voice_proc.join(timeout=2)
        sys.exit(0)


if __name__ == "__main__":
    main()
