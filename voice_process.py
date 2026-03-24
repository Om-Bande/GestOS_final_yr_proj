"""
voice_process.py — Windows SAPI speech recognition.

To add a new command: add one line to COMMAND_MAP. Nothing else changes.

Flow:
  SAPI hears a phrase → on_recognized() → puts intent into intent_queue
                                         → puts display text into status_queue
"""

import time
import multiprocessing as mp


# ── Command map ────────────────────────────────────────────────────────────
# "spoken phrase" : ("action_name", {params})
# Add new commands here. Handle the action_name in main.py execute().

COMMAND_MAP: dict[str, tuple[str, dict]] = {
    # Volume
    "volume up":                ("volume_up",      {}),
    "volume down":              ("volume_down",    {}),
    "mute":                     ("mute",           {}),
    "unmute":                   ("mute",           {}),
    "set volume to ten":        ("volume_set",     {"level": 10}),
    "set volume to twenty":     ("volume_set",     {"level": 20}),
    "set volume to thirty":     ("volume_set",     {"level": 30}),
    "set volume to forty":      ("volume_set",     {"level": 40}),
    "set volume to fifty":      ("volume_set",     {"level": 50}),
    "set volume to sixty":      ("volume_set",     {"level": 60}),
    "set volume to seventy":    ("volume_set",     {"level": 70}),
    "set volume to eighty":     ("volume_set",     {"level": 80}),
    "set volume to ninety":     ("volume_set",     {"level": 90}),
    "set volume to hundred":    ("volume_set",     {"level": 100}),

    # Brightness
    "brightness up":            ("brightness_up",  {}),
    "brightness down":          ("brightness_down",{}),
    "set brightness to ten":    ("brightness_set", {"level": 10}),
    "set brightness to twenty": ("brightness_set", {"level": 20}),
    "set brightness to thirty": ("brightness_set", {"level": 30}),
    "set brightness to forty":  ("brightness_set", {"level": 40}),
    "set brightness to fifty":  ("brightness_set", {"level": 50}),
    "set brightness to sixty":  ("brightness_set", {"level": 60}),
    "set brightness to seventy":("brightness_set", {"level": 70}),
    "set brightness to eighty": ("brightness_set", {"level": 80}),
    "set brightness to ninety": ("brightness_set", {"level": 90}),
    "set brightness to hundred":("brightness_set", {"level": 100}),

    # Clicks
    "click":                    ("click",          {}),
    "single click":             ("click",          {}),
    "double click":             ("double_click",   {}),
    "right click":              ("right_click",    {}),

    # Editing
    "copy":                     ("copy",           {}),
    "paste":                    ("paste",          {}),
}


# ── SAPI SRGS grammar XML ──────────────────────────────────────────────────

def _build_grammar_xml(phrases: list[str]) -> str:
    items = "\n      ".join(f"<item>{p}</item>" for p in phrases)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<grammar version="1.0" xml:lang="en-US"
         xmlns="http://www.w3.org/2001/06/grammar">
  <rule id="hci" scope="public">
    <one-of>
      {items}
    </one-of>
  </rule>
</grammar>"""


# ── SAPI event sink factory ────────────────────────────────────────────────
# DispatchWithEvents instantiates the class itself, so we bake the callback
# into the class via a factory to avoid shared state issues.

def _make_sink(on_recog):
    import win32com.client

    class Sink:
        def OnRecognition(self, StreamNumber, StreamPosition, RecognitionType, Result):
            try:
                obj  = win32com.client.Dispatch(Result)
                text = obj.PhraseInfo.GetText().strip().lower()
                on_recog(text)
            except Exception as e:
                print(f"[Voice] Recognition error: {e}")

        # SAPI requires all these stubs or it raises a COM error
        def OnStartStream(self, *a):              pass
        def OnEndStream(self, *a):                pass
        def OnHypothesis(self, *a):               pass
        def OnPhraseStart(self, *a):              pass
        def OnFalseRecognition(self, *a):         pass
        def OnSoundStart(self, *a):               pass
        def OnSoundEnd(self, *a):                 pass
        def OnAudioLevel(self, *a):               pass
        def OnInterference(self, *a):             pass
        def OnRecognitionForOtherContext(self, *a):pass
        def OnAdaptationComplete(self, *a):       pass
        def OnStateChange(self, *a):              pass
        def OnBookmark(self, *a):                 pass
        def OnPropertyNumberChange(self, *a):     pass
        def OnPropertyStringChange(self, *a):     pass

    return Sink


# ── Shared recognition handler ─────────────────────────────────────────────

def _on_recognized(text: str, intent_queue: mp.Queue, status_queue: mp.Queue):
    print(f"[Voice] '{text}'")
    cmd = COMMAND_MAP.get(text)

    # Partial match fallback for minor ASR drift
    if cmd is None:
        for phrase, c in COMMAND_MAP.items():
            if phrase in text or text in phrase:
                cmd = c
                break

    if cmd:
        action, params = cmd
        try:
            intent_queue.put_nowait({"action": action, "params": params})
        except Exception:
            pass
        try:
            status_queue.put_nowait(text)
        except Exception:
            pass


# ── Process entry ──────────────────────────────────────────────────────────

def voice_process_entry(intent_queue: mp.Queue, status_queue: mp.Queue):
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        print("[Voice] pywin32 not found. Voice disabled.")
        return

    def on_recog(text: str):
        _on_recognized(text, intent_queue, status_queue)

    pythoncom.CoInitialize()
    try:
        reco        = win32com.client.Dispatch("SAPI.SpInprocRecognizer")
        audio_in    = win32com.client.Dispatch("SAPI.SpMMAudioIn")
        reco.AudioInput = audio_in

        ctx     = reco.CreateRecoContext()
        grammar = ctx.CreateGrammar(1)
        grammar.DictationSetState(0)   # Disable free dictation

        xml = _build_grammar_xml(list(COMMAND_MAP.keys()))
        grammar.CmdLoadFromString(xml, 0)   # SLOStatic = 0
        grammar.CmdSetRuleState("hci", 1)   # SGDSActive = 1

        win32com.client.DispatchWithEvents(ctx, _make_sink(on_recog))

        print(f"[Voice] SAPI ready — {len(COMMAND_MAP)} phrases loaded.")

        # Pump COM events. Voice recognition callbacks arrive here.
        while True:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.02)

    except Exception as e:
        print(f"[Voice] SAPI error: {e}. Trying Vosk fallback...")
        _vosk_fallback(intent_queue, status_queue)
    finally:
        pythoncom.CoUninitialize()


def _vosk_fallback(intent_queue: mp.Queue, status_queue: mp.Queue):
    """
    Vosk fallback — used when SAPI is unavailable.
    Requires: pip install vosk pyaudio
    Requires: a Vosk model folder named 'model' in the project root.
    Download: https://alphacephei.com/vosk/models (vosk-model-small-en-us-0.15)
    """
    try:
        import json, os
        import vosk, pyaudio

        if not os.path.exists("model"):
            print("[Voice] Vosk model folder 'model' not found. Voice disabled.")
            return

        model      = vosk.Model("model")
        pa         = pyaudio.PyAudio()
        stream     = pa.open(format=pyaudio.paInt16, channels=1,
                             rate=16000, input=True, frames_per_buffer=8000)
        grammar    = json.dumps(list(COMMAND_MAP.keys()) + ["[unk]"])
        recognizer = vosk.KaldiRecognizer(model, 16000, grammar)

        print("[Voice] Vosk fallback active.")

        while True:
            data = stream.read(4000, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text   = result.get("text", "").strip().lower()
                if text and text != "[unk]":
                    _on_recognized(text, intent_queue, status_queue)

    except Exception as e:
        print(f"[Voice] Vosk fallback error: {e}. Voice disabled.")
