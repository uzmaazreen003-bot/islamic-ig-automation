"""Final 'film' pass for every reel frame: slow camera push-in, soft bloom on bright parts, vignette, fine grain."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

W, H = 720, 1280
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H * 0.46) / (H / 2)) ** 2)
VIGNETTE = (1.0 - 0.42 * np.clip(_r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
_rng = np.random.default_rng(5)
GRAIN = [_rng.normal(0, 2.6, (H, W, 1)).astype(np.float32) for _ in range(4)]


def finish(img, tm, total, shake=(0.0, 0.0), zoom=0.04, bloom=0.30, fi=0):
    """img: RGB PIL image -> uint8 numpy array (H, W, 3)."""
    z = 1.0 + zoom * min(1.0, tm / max(total, 1.0))
    bw, bh = W / z, H / z
    x0 = min(max((W - bw) / 2 + shake[0], 0.0), W - bw)
    y0 = min(max((H - bh) / 2 + shake[1], 0.0), H - bh)
    img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh))
    arr = np.asarray(img, np.float32)
    if bloom > 0:
        small = np.asarray(img.resize((W // 6, H // 6), Image.BILINEAR), np.float32)
        lum = small.max(axis=2, keepdims=True)
        hot = np.clip((lum - 170.0) / 85.0, 0, 1) * small
        hot = Image.fromarray(np.clip(hot, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
        arr = 255.0 - (255.0 - arr) * (255.0 - np.asarray(hot, np.float32) * bloom) / 255.0     # screen blend
    arr = arr * VIGNETTE + GRAIN[fi % 4]
    return np.clip(arr, 0, 255).astype(np.uint8)
