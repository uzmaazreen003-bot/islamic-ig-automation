"""English narration (calm, warm male voice via free edge-tts). Falls back to silence if unavailable.

Change the voice in data/config.json: "narrator_voice": "en-US-AndrewMultilingualNeural" (or any voice below),
"narrator_rate": "-10%", "narrator_pitch": "-2Hz".
"""
from __future__ import annotations

import asyncio
import os
import re

from . import audio
from .voice import _normalize, _trim

# warmest / most natural first; the next one is used automatically if a voice is unavailable
VOICES = ["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural", "en-GB-RyanNeural", "en-US-GuyNeural", "en-GB-ThomasNeural"]
SETTINGS = {"voice": None, "rate": "-10%", "pitch": "-2Hz"}


def configure(cfg):
    SETTINGS["voice"] = cfg.get("narrator_voice") or None
    SETTINGS["rate"] = cfg.get("narrator_rate", SETTINGS["rate"])
    SETTINGS["pitch"] = cfg.get("narrator_pitch", SETTINGS["pitch"])


def clean(text):
    text = text.replace("(ﷺ)", "").replace("ﷺ", "")
    text = re.sub(r"[\[\]]", "", text)
    text = text.replace(" - ", ", ").replace("“", "").replace("”", "")
    return re.sub(r"\s+", " ", text).strip()


async def _speak(text, voice, path, rate, pitch):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)


def line(text, workdir, name):
    """-> numpy clip (audio.SR) or None."""
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("[narrate] edge-tts missing; reel will have no voice")
        return None
    path = os.path.join(workdir, f"narr-{name}.mp3")
    voices = ([SETTINGS["voice"]] if SETTINGS["voice"] else []) + VOICES
    for v in dict.fromkeys(voices):
        for pitch in (SETTINGS["pitch"], "+0Hz"):
            try:
                asyncio.run(_speak(clean(text), v, path, SETTINGS["rate"], pitch))
                clip = _trim(audio.decode_audio(path))
                if len(clip) > 0.3 * audio.SR:
                    print(f"[narrate] {name}: {v} {len(clip) / audio.SR:.1f}s")
                    return _normalize(clip, 0.85)
            except Exception as exc:                       # noqa: BLE001
                print(f"[narrate] {v} ({pitch}) failed: {exc}")
    return None
