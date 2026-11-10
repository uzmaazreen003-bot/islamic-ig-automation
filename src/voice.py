"""Voices: real Quran recitation for ayat/duas, and a neural Arabic voice for short dhikr phrases.

Both are optional: if a download or the TTS service fails, the reel is still made (natural sounds only) and the
log says so. Nothing here ever changes the text; it only reads exactly what is in the data files.
"""
from __future__ import annotations

import asyncio
import os
import time

import numpy as np
import requests

from . import audio

RECITER = "Mishary Rashid Alafasy"
CDN = "https://cdn.islamic.network/quran/audio/128/ar.alafasy/{n}.mp3"
TTS_VOICES = ["ar-SA-HamedNeural", "ar-EG-ShakirNeural"]


def _normalize(x, peak=0.8):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def _trim(x, thresh=0.012, pad=0.06):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * audio.SR))
    b = min(len(x), idx[-1] + int(pad * audio.SR))
    return x[a:b]


def recitation(numbers, workdir):
    """Alafasy recitation of the given global ayah numbers, joined. None if it cannot be fetched."""
    parts = []
    for n in numbers:
        path = os.path.join(workdir, f"ayah-{n}.mp3")
        ok = False
        for attempt in range(3):
            try:
                r = requests.get(CDN.format(n=n), timeout=30)
                r.raise_for_status()
                with open(path, "wb") as fh:
                    fh.write(r.content)
                ok = True
                break
            except Exception as exc:                      # noqa: BLE001 - any failure means "no recitation"
                print(f"[voice] recitation {n} attempt {attempt + 1} failed: {exc}")
                time.sleep(2)
        if not ok:
            return None
        try:
            parts.append(_trim(audio.decode_audio(path)))
        except Exception as exc:                          # noqa: BLE001
            print(f"[voice] could not decode recitation {n}: {exc}")
            return None
    gap = np.zeros(int(0.5 * audio.SR))
    seq = []
    for i, p in enumerate(parts):
        if i:
            seq.append(gap)
        seq.append(p)
    return _normalize(np.concatenate(seq), 0.8)


async def _tts(text, voice, path, rate):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(path)


def dhikr(text, workdir, name):
    """Short Arabic phrase spoken slowly and clearly (fully vowelled text). None if TTS is unavailable."""
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("[voice] edge-tts is not installed; dhikr will be sound-only")
        return None
    path = os.path.join(workdir, f"dhikr-{name}.mp3")
    for voice in TTS_VOICES:
        try:
            asyncio.run(_tts(text, voice, path, "-18%"))
            clip = _trim(audio.decode_audio(path))
            if len(clip) > 0.4 * audio.SR:
                print(f"[voice] dhikr '{name}' spoken with {voice}: {len(clip) / audio.SR:.1f}s")
                return _normalize(clip, 0.8)
        except Exception as exc:                          # noqa: BLE001
            print(f"[voice] TTS {voice} failed: {exc}")
    return None
