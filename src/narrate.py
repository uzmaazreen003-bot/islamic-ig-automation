"""English narration for story reels (calm male voice via free edge-tts). Falls back to silence if unavailable."""
from __future__ import annotations

import asyncio
import os

from . import audio
from .voice import _normalize, _trim, _tts

VOICES = ["en-GB-RyanNeural", "en-US-GuyNeural", "en-GB-ThomasNeural", "en-US-ChristopherNeural"]
RATE = "-10%"


def line(text, workdir, name):
    """-> numpy clip (audio.SR) or None."""
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("[narrate] edge-tts missing; reel will have no voice")
        return None
    path = os.path.join(workdir, f"narr-{name}.mp3")
    for v in VOICES:
        try:
            asyncio.run(_tts(text, v, path, RATE))
            clip = _trim(audio.decode_audio(path))
            if len(clip) > 0.3 * audio.SR:
                print(f"[narrate] {name}: {v} {len(clip) / audio.SR:.1f}s")
                return _normalize(clip, 0.85)
        except Exception as exc:                       # noqa: BLE001
            print(f"[narrate] {v} failed: {exc}")
    return None
