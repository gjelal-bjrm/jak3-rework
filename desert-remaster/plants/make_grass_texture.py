"""Texture d'un brin d'herbe seche du desert (degrade base -> pointe, teintes de l'herbe d'origine, fines stries).
Lancement (Python de Blender : numpy + PIL) : python desert-remaster/plants/make_grass_texture.py
Sorties : grass-blade.rgba (pour le bridge) et grass-blade.png (apercu)."""
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
W, H = 64, 256
v = np.linspace(0, 1, H)[:, None]
u = np.linspace(0, 1, W)[None, :]
# teintes de l'herbe d'origine (des-sand-grass-01 : haut 148,129,79 / milieu 129,108,65 / bas 112,89,51), pointe un peu eclaircie
tip = np.array([188, 170, 112]); mid = np.array([146, 124, 76]); base = np.array([112, 90, 54])
col = np.where(v[..., None] < .5, tip + (mid - tip) * (v[..., None] / .5), mid + (base - mid) * ((v[..., None] - .5) / .5))
col = np.broadcast_to(col, (H, W, 3)).copy()
rng = np.random.default_rng(3)
streak = np.convolve(rng.normal(0, 1, W), np.ones(3) / 3, 'same')
col *= (1 + .06 * streak)[None, :, None]
col *= (1 - .08 * np.abs(u - .5) * 2)[..., None]
col *= (1 + rng.normal(0, 1, (H, W)) * .02)[..., None]
rgba = np.dstack([np.clip(col, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
(HERE / 'grass-blade.rgba').write_bytes(rgba.tobytes())
Image.fromarray(rgba).save(HERE / 'grass-blade.png')
