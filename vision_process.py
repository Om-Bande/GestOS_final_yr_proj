"""
vision_process.py — camera capture, MediaPipe, gesture detection, display window.

Gestures:
    POINT        (index only)           → move cursor
    PINCH        (thumb + index close)  → short = click/double-click, held = drag
    TWO_FINGER   (index + middle up)    → right click (held 300ms)
    SCROLL       (index + middle + ring)→ index Y position controls up/down

Display: small always-on-top OpenCV window in the corner.
Top-left overlay shows active gesture (green) and last voice command (cyan).
"""

import cv2
import math
import time
import multiprocessing as mp

try:
    import mediapipe as mp_lib
    MEDIAPIPE_OK = True
except ImportError:
    MEDIAPIPE_OK = False
    print("[Vision] MediaPipe not available. Install it: pip install mediapipe")


# ── Tuning ─────────────────────────────────────────────────────────────────
PINCH_DIST       = 0.06   # normalized dist between thumb and index tip
DRAG_HOLD_S      = 0.35   # hold pinch this long → drag instead of click
DOUBLE_CLICK_GAP = 0.40   # two pinches within this → double click
TWO_FINGER_HOLD  = 0.30   # hold two-finger pose this long → right click
SCROLL_DEADZONE  = 0.15   # index Y must be > 0.5±this to scroll
SCROLL_THROTTLE  = 0.08   # seconds between scroll events (~12/s)
TRACK_INTERVAL   = 1/60   # max cursor-move events per second
SMOOTH_ALPHA     = 0.35   # EMA for cursor (lower = smoother, more lag)
VOICE_TTL        = 3.0    # seconds to show last voice command on screen
WIN_W, WIN_H     = 320, 240

# Camera dead zone — your hand never reaches the very edges of the frame.
# These define the portion of the camera frame that maps to the full screen.
# Tune these if the cursor still can't reach screen edges:
#   - Run the app, print(lm[8].x, lm[8].y) while moving finger to each edge
#   - Use those values here
CAM_X_MIN = 0.15   # left edge of your comfortable hand range
CAM_X_MAX = 0.85   # right edge
CAM_Y_MIN = 0.05   # top edge
CAM_Y_MAX = 0.80   # bottom edge

# ── ADDED: Both-hand open palm gesture constant ────────────────────────────
OPEN_PALM_HOLD_S = 2.0    # hold both hands open palm this long → shutdown/restart trigger
# ── ADDED: Fist gesture constant ──────────────────────────────────────────
FIST_HOLD_S      = 0.30   # hold fist this long → VLC play/pause
# ── END ADDED ──────────────────────────────────────────────────────────────


def _put(q: mp.Queue, action: str, params: dict = None):
    """Non-blocking put. Silently drops if queue is full."""
    try:
        q.put_nowait({"action": action, "params": params or {}})
    except Exception:
        pass


def _remap(value: float, in_min: float, in_max: float) -> float:
    """
    Remaps a value from [in_min, in_max] to [0.0, 1.0], clamped.
    Used to map camera-space hand coords to full screen coords.
    """
    if in_max <= in_min:
        return max(0.0, min(1.0, value))
    return max(0.0, min(1.0, (value - in_min) / (in_max - in_min)))


def vision_process_entry(
    intent_queue: mp.Queue,
    status_queue: mp.Queue,
    screen_w: int,
    screen_h: int,
    sys_queue: mp.Queue = None,   # ADDED: receives countdown status from main for display
):
    if not MEDIAPIPE_OK:
        return

    hands = mp_lib.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=2,             # CHANGED: 2 hands needed for both-palm shutdown gesture
        model_complexity=0,          # Lite model — fastest inference
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )
    draw = mp_lib.solutions.drawing_utils

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW = faster init on Windows
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # Never queue old frames

    WIN = "Hand Control"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, WIN_W, WIN_H)
    cv2.setWindowProperty(WIN, cv2.WND_PROP_TOPMOST, 1)

    # ── Gesture state ──────────────────────────────────────────────────────
    pinch_active    = False
    pinch_start_t   = 0.0
    pinch_start_xy  = (0.0, 0.0)
    dragging        = False
    click_times: list[float] = []

    two_finger_start_t: float | None = None
    two_finger_fired   = False

    smooth_xy: tuple | None = None
    last_track_t  = 0.0
    last_scroll_t = 0.0

    # ── Display state ──────────────────────────────────────────────────────
    disp_gesture = ""
    disp_voice   = ""
    last_voice_t = 0.0

    # ── ADDED: Both-hand open palm state + countdown display ───────────────
    both_palm_start_t: float | None = None
    both_palm_fired   = False
    countdown_text = ""
    # ── ADDED: Fist gesture state (VLC play/pause) ─────────────────────────
    fist_start_t: float | None = None
    fist_fired        = False
    # ── END ADDED ──────────────────────────────────────────────────────────

    print("[Vision] Started.")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        now   = time.time()
        frame = cv2.flip(frame, 1)

        # Poll voice status (non-blocking drain)
        try:
            while not status_queue.empty():
                disp_voice   = status_queue.get_nowait()
                last_voice_t = now
        except Exception:
            pass
        if now - last_voice_t > VOICE_TTL:
            disp_voice = ""

        # ── ADDED: Poll countdown status from main process ─────────────────
        # main.py sends strings like "SHUTDOWN: 5" during countdown, or "" to clear
        if sys_queue is not None:
            try:
                while not sys_queue.empty():
                    countdown_text = sys_queue.get_nowait()
            except Exception:
                pass
        # ── END ADDED ──────────────────────────────────────────────────────

        # ── MediaPipe inference ────────────────────────────────────────────
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = hands.process(rgb)
        rgb.flags.writeable = True

        gesture = "IDLE"

        if results.multi_hand_landmarks:
            lm_obj = results.multi_hand_landmarks[0]
            draw.draw_landmarks(frame, lm_obj, mp_lib.solutions.hands.HAND_CONNECTIONS)
            lm = lm_obj.landmark

            # ── Finger state ───────────────────────────────────────────────
            index_up  = lm[8].y  < lm[6].y
            middle_up = lm[12].y < lm[10].y
            ring_up   = lm[16].y < lm[14].y
            pinky_up  = lm[20].y < lm[18].y
            is_pinch  = math.hypot(lm[4].x - lm[5].x, lm[4].y - lm[5].y) < PINCH_DIST

            # ── Classify gesture (priority order matters) ──────────────────
            if index_up and middle_up and ring_up:
                gesture = "SCROLL"
            elif is_pinch:
                gesture = "PINCH"
            elif index_up and middle_up and not ring_up and not pinky_up:
                gesture = "TWO_FINGER"
            elif index_up and not middle_up and not ring_up:
                gesture = "POINT"

            # ── Reset states for gestures that are no longer active ────────
            if gesture != "TWO_FINGER":
                two_finger_start_t = None
                two_finger_fired   = False
            if gesture != "POINT":
                smooth_xy = None

            # ── Resolve pinch that just ended ──────────────────────────────
            if gesture != "PINCH" and pinch_active:
                if dragging:
                    _put(intent_queue, "drag_end")
                    dragging = False
                else:
                    # Short pinch = click. Check for double click.
                    click_times.append(now)
                    click_times = [t for t in click_times if now - t < DOUBLE_CLICK_GAP * 2]
                    if len(click_times) >= 2 and (click_times[-1] - click_times[-2]) < DOUBLE_CLICK_GAP:
                        _put(intent_queue, "double_click")
                        click_times.clear()
                    else:
                        _put(intent_queue, "click")
                pinch_active = False

            # ── Gesture handlers ───────────────────────────────────────────

            if gesture == "SCROLL":
                y = lm[8].y
                if now - last_scroll_t >= SCROLL_THROTTLE:
                    if y < 0.5 - SCROLL_DEADZONE:
                        _put(intent_queue, "scroll_up")
                        last_scroll_t = now
                    elif y > 0.5 + SCROLL_DEADZONE:
                        _put(intent_queue, "scroll_down")
                        last_scroll_t = now

            elif gesture == "PINCH":
                if not pinch_active:
                    pinch_active   = True
                    pinch_start_t  = now
                    pinch_start_xy = (lm[8].x, lm[8].y)
                    dragging       = False
                else:
                    held = now - pinch_start_t
                    if not dragging and held >= DRAG_HOLD_S:
                        dragging = True
                        sx = int(_remap(pinch_start_xy[0], CAM_X_MIN, CAM_X_MAX) * screen_w)
                        sy = int(_remap(pinch_start_xy[1], CAM_Y_MIN, CAM_Y_MAX) * screen_h)
                        _put(intent_queue, "drag_start", {"x": sx, "y": sy})
                    if dragging and now - last_track_t >= TRACK_INTERVAL:
                        last_track_t = now
                        _put(intent_queue, "drag_move", {
                            "x": int(_remap(lm[8].x, CAM_X_MIN, CAM_X_MAX) * screen_w),
                            "y": int(_remap(lm[8].y, CAM_Y_MIN, CAM_Y_MAX) * screen_h),
                        })

            elif gesture == "TWO_FINGER":
                if two_finger_start_t is None:
                    two_finger_start_t = now
                elif not two_finger_fired and (now - two_finger_start_t) >= TWO_FINGER_HOLD:
                    _put(intent_queue, "right_click")
                    two_finger_fired = True

            elif gesture == "POINT":
                if now - last_track_t >= TRACK_INTERVAL:
                    last_track_t = now
                    raw_x = _remap(lm[8].x, CAM_X_MIN, CAM_X_MAX)
                    raw_y = _remap(lm[8].y, CAM_Y_MIN, CAM_Y_MAX)
                    if smooth_xy is None:
                        smooth_xy = (raw_x, raw_y)
                    px, py = smooth_xy
                    sx = px + (raw_x - px) * SMOOTH_ALPHA
                    sy = py + (raw_y - py) * SMOOTH_ALPHA
                    smooth_xy = (sx, sy)
                    _put(intent_queue, "move_cursor", {
                        "x": int(sx * screen_w),
                        "y": int(sy * screen_h),
                    })

        else:
            # No hand — clean up any active drag
            if pinch_active and dragging:
                _put(intent_queue, "drag_end")
            pinch_active       = False
            dragging           = False
            smooth_xy          = None
            two_finger_start_t = None
            two_finger_fired   = False
            gesture            = ""

        # ── ADDED: Both-hand open palm detection (shutdown/restart trigger) ──
        # Runs independently of single-hand gesture logic above.
        # Requires BOTH hands visible and ALL fingers up on each hand.
        # Hold for OPEN_PALM_HOLD_S (2s) → sends shutdown_request to main.
        # Re-arms once hands are lowered (both_palm_fired resets on no-detection).

        both_palms_detected = False
        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
            all_open = True
            for hand_lm in results.multi_hand_landmarks:
                lm_p = hand_lm.landmark
                # Check all 4 fingers extended (tip Y < pip Y = finger is up)
                fingers_up = (
                    lm_p[8].y  < lm_p[6].y  and   # index
                    lm_p[12].y < lm_p[10].y and   # middle
                    lm_p[16].y < lm_p[14].y and   # ring
                    lm_p[20].y < lm_p[18].y        # pinky
                )
                if not fingers_up:
                    all_open = False
                    break
            both_palms_detected = all_open

        if both_palms_detected:
            if both_palm_start_t is None:
                both_palm_start_t = now
            elif not both_palm_fired and (now - both_palm_start_t) >= OPEN_PALM_HOLD_S:
                _put(intent_queue, "shutdown_request")
                both_palm_fired = True
        else:
            both_palm_start_t = None
            both_palm_fired   = False
        # ── END ADDED ──────────────────────────────────────────────────────

        # ── ADDED: Fist gesture detection (VLC play/pause) ────────────────
        # All 4 fingers curled = fist. Hold FIST_HOLD_S → vlc_play_pause.
        # Only fires on one hand (primary hand from single-hand results).
        # Re-arms when fist is released.
        fist_detected = False
        if results.multi_hand_landmarks:
            lm_f = results.multi_hand_landmarks[0].landmark
            fist_detected = (
                lm_f[8].y  > lm_f[6].y  and   # index down
                lm_f[12].y > lm_f[10].y and   # middle down
                lm_f[16].y > lm_f[14].y and   # ring down
                lm_f[20].y > lm_f[18].y        # pinky down
            )

        if fist_detected:
            if fist_start_t is None:
                fist_start_t = now
            elif not fist_fired and (now - fist_start_t) >= FIST_HOLD_S:
                _put(intent_queue, "vlc_play_pause")
                fist_fired = True
        else:
            fist_start_t = None
            fist_fired   = False
        # ── END ADDED ──────────────────────────────────────────────────────

        # ── Draw overlay on frame ──────────────────────────────────────────
        disp_gesture = gesture if gesture not in ("IDLE", "") else ""

        cv2.putText(frame, f"G: {disp_gesture}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 80), 2, cv2.LINE_AA)
        cv2.putText(frame, f"V: {disp_voice}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA)

        # ── ADDED: Countdown overlay (big red text center frame) ───────────
        # countdown_text is set by sys_queue messages from main.py
        # e.g. "SHUTDOWN: 5" or "RESTART: 3" or "" to clear
        if countdown_text:
            h, w = frame.shape[:2]
            # Draw a dark semi-transparent bar behind the text for readability
            text_size = cv2.getTextSize(countdown_text, cv2.FONT_HERSHEY_DUPLEX, 1.4, 3)[0]
            tx = (w - text_size[0]) // 2
            ty = h // 2
            cv2.rectangle(frame, (tx - 10, ty - text_size[1] - 10),
                          (tx + text_size[0] + 10, ty + 10), (0, 0, 0), -1)
            cv2.putText(frame, countdown_text, (tx, ty),
                        cv2.FONT_HERSHEY_DUPLEX, 1.4, (0, 0, 255), 3, cv2.LINE_AA)
        # ── END ADDED ──────────────────────────────────────────────────────

        small = cv2.resize(frame, (WIN_W, WIN_H))
        cv2.imshow(WIN, small)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("[Vision] Stopped.")
