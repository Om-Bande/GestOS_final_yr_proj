"""
main.py — entry point.

Starts two subprocesses (vision, voice), then sits in a loop
reading intents and executing PC actions. That's it.
"""

import sys
import time
import multiprocessing as mp
import win32api
import win32con

from windows_controller import WindowsController, MouseButton
from vision_process import vision_process_entry
from voice_process import voice_process_entry
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

    # App open/close
    elif action == "open_app":
        open_app(params.get("app", ""))
    elif action == "close_app":
        close_app(params.get("app", ""))
    elif action == "close_window":
        close_foreground_window()
    elif action == "close_tab":
        controller.send_keys("ctrl+w")
    elif action == "new_tab":
        controller.send_keys("ctrl+t")
    elif action == "next_tab":
        controller.send_keys("ctrl+tab")
    elif action == "prev_tab":
        controller.send_keys("ctrl+shift+tab")
    elif action == "reopen_tab":
        controller.send_keys("ctrl+shift+t")
    elif action == "dictation":
        controller.send_keys("win+h")    

    # ── ADDED: VLC media controls ──────────────────────────────────────────
    # Space = play/pause, n = next, p = previous, s = stop in VLC
    elif action == "vlc_play_pause":
        controller.send_vlc_command(" ")
    elif action == "vlc_next":
        controller.send_vlc_command("n")
    elif action == "vlc_previous":
        controller.send_vlc_command("p")
    elif action == "vlc_stop":
        controller.send_vlc_command("s")

    # ── ADDED: WiFi / Bluetooth / Night mode ───────────────────────────────
    elif action == "wifi_on":
        controller.toggle_wifi(True)
    elif action == "wifi_off":
        controller.toggle_wifi(False)
    elif action == "bluetooth_on":
        controller.toggle_bluetooth(True)
    elif action == "bluetooth_off":
        controller.toggle_bluetooth(False)
    elif action == "night_mode_on":
        controller.toggle_night_mode(True)
    elif action == "night_mode_off":
        controller.toggle_night_mode(False)
    # ── END ADDED ──────────────────────────────────────────────────────────


def main():
    mp.set_start_method("spawn", force=True)

    intent_queue = mp.Queue(maxsize=30)
    status_queue = mp.Queue(maxsize=5)   # voice/vision display text
    sys_queue    = mp.Queue(maxsize=5)   # countdown text main → vision

    controller = WindowsController()

    vision_proc = mp.Process(
        target=vision_process_entry,
        args=(intent_queue, status_queue, controller.screen_width, controller.screen_height, sys_queue),
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

    # ── Pending system action state ────────────────────────────────────────
    # Tracks shutdown / restart / sleep waiting for voice confirmation.
    # pending_action: "shutdown" | "restart" | "sleep" | None
    CONFIRM_WINDOW_S = 7

    pending_action   = None
    confirm_deadline = 0.0
    # ──────────────────────────────────────────────────────────────────────

    try:
        while True:
            # ── Countdown tick (runs every loop regardless of new intents) ──
            if pending_action is not None:
                remaining = confirm_deadline - time.time()
                if remaining <= 0:
                    print(f"[Main] {pending_action.upper()} timed out. Cancelled.")
                    pending_action = None
                    try: sys_queue.put_nowait("")
                    except Exception: pass
                else:
                    text = f"{pending_action.upper()}: {int(remaining) + 1}"
                    try:
                        while not sys_queue.empty():
                            sys_queue.get_nowait()
                        sys_queue.put_nowait(text)
                    except Exception: pass
            # ──────────────────────────────────────────────────────────────

            try:
                msg = intent_queue.get(timeout=0.05)
            except Exception:
                continue

            action = msg["action"]
            params = msg.get("params", {})

            # ── System action handlers ─────────────────────────────────────
            if action in ("shutdown_request", "restart_request", "sleep_request"):
                if pending_action is None:
                    pending_action   = action.replace("_request", "")
                    confirm_deadline = time.time() + CONFIRM_WINDOW_S
                    print(f"[Main] {pending_action.upper()} requested. Say 'confirm' within {CONFIRM_WINDOW_S}s.")
                continue

            if action == "confirm":
                if pending_action == "shutdown":
                    print("[Main] SHUTDOWN confirmed.")
                    try: sys_queue.put_nowait("")
                    except Exception: pass
                    controller.shutdown(0)
                elif pending_action == "restart":
                    print("[Main] RESTART confirmed.")
                    try: sys_queue.put_nowait("")
                    except Exception: pass
                    controller.restart(0)
                elif pending_action == "sleep":
                    print("[Main] SLEEP confirmed.")
                    try: sys_queue.put_nowait("")
                    except Exception: pass
                    controller.sleep_pc()
                else:
                    print("[Main] 'confirm' received but nothing pending.")
                pending_action = None
                continue

            if action == "cancel":
                if pending_action:
                    print(f"[Main] {pending_action.upper()} cancelled.")
                    pending_action = None
                    try: sys_queue.put_nowait("")
                    except Exception: pass
                continue

            if action == "lock":
                controller.lock_screen()
                continue

            if action == "stop_program":
                print("[Main] Stopping program.")
                controller.cancel_shutdown()
                vision_proc.terminate()
                voice_proc.terminate()
                vision_proc.join(timeout=2)
                voice_proc.join(timeout=2)
                sys.exit(0)
            # ── END system handlers ────────────────────────────────────────

            try:
                execute(controller, action, params)
            except Exception as e:
                print(f"[Main] Error on '{action}': {e}")

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
