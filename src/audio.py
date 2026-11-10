"""Natural sounds only (glass-bead clicks, singing-bowl chimes, a soft breeze). No music."""
from __future__ import annotations

import subprocess
import wave

import numpy as np

SR = 44100


def _env(n, decay):
    t = np.arange(n) / SR
    return np.exp(-t * decay)


def clink(rng, pitch=1.0):
    """A glass/stone bead tapping on other beads."""
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    f = rng.uniform(1500, 2100) * pitch
    sig = (np.sin(2 * np.pi * f * t) * np.exp(-t * 42)
           + 0.55 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 70)
           + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 110))
    tick = np.diff(rng.standard_normal(int(0.012 * SR) + 1))
    sig[: len(tick)] += tick * np.exp(-np.arange(len(tick)) / SR * 400) * 0.9
    return sig * rng.uniform(0.07, 0.10)


def drop_ping(rng, pitch=1.0):
    """Tiny soft whoosh as the bead leaves the nozzle."""
    n = int(0.12 * SR)
    noise = np.convolve(rng.standard_normal(n), np.ones(30) / 30, mode="same")
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return noise * env * 0.10


def bowl(freq=528.0, dur=2.6, gain=0.22):
    """Singing-bowl style chime: a few slowly beating partials."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for mult, amp, dec, beat in ((1.0, 1.0, 1.5, 1.2), (2.0, 0.5, 2.2, 0.7), (2.98, 0.35, 3.2, 1.6), (4.16, 0.18, 4.5, 0.9)):
        sig += amp * np.sin(2 * np.pi * freq * mult * t) * np.exp(-t * dec) * (0.85 + 0.15 * np.sin(2 * np.pi * beat * t))
    attack = np.minimum(t / 0.012, 1)
    return sig * attack * gain


def breeze(rng, dur, gain=0.05):
    """Very quiet moving air: low-passed noise with slow swells."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    k = 400
    lp = np.convolve(noise, np.ones(k) / k, mode="same")
    t = np.arange(n) / SR
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * t + 1.0) * np.sin(2 * np.pi * 0.047 * t + 0.4)
    lp = lp / (np.abs(lp).max() + 1e-9)
    fade = np.minimum(1, np.minimum(t / 1.5, (dur - t) / 1.5).clip(0))
    return lp * swell * fade * gain


def decode_audio(path):
    """Any audio file -> float32 mono array at 44.1 kHz (via ffmpeg)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)


def stream(rng, dur, gain=0.035):
    """A very quiet brook: band-limited noise with tiny random bubbles."""
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    a = np.convolve(noise, np.ones(18) / 18, mode="same")
    b = np.convolve(noise, np.ones(140) / 140, mode="same")
    band = a - b * 2.2
    band /= np.abs(band).max() + 1e-9
    t = np.arange(n) / SR
    band *= 0.7 + 0.3 * np.sin(2 * np.pi * 0.23 * t + 2.0)
    for _ in range(int(dur * 2.2)):
        i = int(rng.uniform(0, max(1, dur - 0.2)) * SR)
        m = int(0.07 * SR)
        tt = np.arange(m) / SR
        f = rng.uniform(700, 1500)
        bub = np.sin(2 * np.pi * (f * tt + 6000 * tt ** 2)) * np.exp(-tt * 45) * rng.uniform(0.05, 0.16)
        if i + m < n:
            band[i:i + m] += bub
    fade = np.minimum(1, np.minimum(t / 2.0, (dur - t) / 2.0).clip(0))
    return band * fade * gain


def pad(dur, base=110.0, gain=0.05):
    """Soft, slowly breathing drone for the story reels."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for mult, amp, det in ((1.0, 1.0, 0.0), (1.5, 0.55, 0.3), (2.0, 0.4, -0.25), (3.0, 0.15, 0.15)):
        sig += amp * np.sin(2 * np.pi * (base * mult + det) * t) * (0.8 + 0.2 * np.sin(2 * np.pi * (0.07 + 0.02 * mult) * t))
    fade = np.minimum(1, np.minimum(t / 3.0, (dur - t) / 3.0).clip(0))
    return sig / 2.1 * fade * gain


def footstep(rng, gain=0.11):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    noise = np.convolve(rng.standard_normal(n), np.ones(40) / 40, mode="same")
    return (noise / (np.abs(noise).max() + 1e-9)) * np.exp(-t * 28) * gain * rng.uniform(0.8, 1.1)


def mix(events, total, path, seed=7, ambient=True, extra=None):
    """events: [(time_s, mono_array)] -> 16-bit stereo wav at `path`."""
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    out = np.zeros(n)
    if ambient:
        out += breeze(rng, total, 0.045) + stream(rng, total, 0.030)
    if extra is not None:
        out[: len(extra)] += extra[:n]
    for t, arr in events:
        i = int(t * SR)
        if i >= n:
            continue
        j = min(n, i + len(arr))
        out[i:j] += arr[: j - i]
    peak = np.abs(out).max()
    if peak > 0.9:
        out *= 0.9 / peak
    stereo = np.stack([out, out], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def encode_video(frames_iter, w, h, fps, wav_path, out_path, crf=20):
    """Pipe raw RGB frames into ffmpeg and mux the wav as AAC. Returns out_path."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
           "-i", wav_path,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "128k", "-shortest", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for fr in frames_iter:
            proc.stdin.write(fr.tobytes())
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {rc}")
    return out_path
