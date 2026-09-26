"""Texture d'un rameau d'aiguilles de pin du desert (opaque) : rameau central brun, aiguilles en chevrons, base vert
sombre -> pointe jaune-vert (teintes de des-pinetree-leaf-01). Python de Blender : numpy + PIL.
Sorties : sprig.rgba (bridge) et sprig.png (apercu). u = travers du rameau (0..1), v = 0 pointe -> 1 base."""
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
W, H = 128, 256
u = np.linspace(0, 1, W)[None, :].repeat(H, 0); v = np.linspace(0, 1, H)[:, None].repeat(W, 1)
x = np.abs(u - .5) * 2                                   # 0 au centre, 1 au bord
tip = np.array([176, 170, 70]); mid = np.array([92, 112, 44]); base = np.array([44, 62, 30])
t = v[..., None]
col = np.where(t < .45, tip + (mid - tip) * (t / .45), mid + (base - mid) * ((t - .45) / .55))
# aiguilles en chevrons : lignes obliques qui partent du rameau vers la pointe
phase = (v * 26 + x * 9) % 1.0
needle = np.clip(1 - np.abs(phase - .5) * 5, 0, 1)
col = col * (.72 + .45 * needle[..., None])
col = col * (1 - .35 * x[..., None] ** 2)                # bords plus sombres (volume)
twig = np.clip(1 - x / .07, 0, 1)[..., None]             # rameau central
col = col * (1 - twig) + np.array([86, 62, 38]) * twig
rng = np.random.default_rng(5)
col *= (1 + rng.normal(0, 1, (H, W)) * .03)[..., None]
rgba = np.dstack([np.clip(col, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
(HERE / 'sprig.rgba').write_bytes(rgba.tobytes())
Image.fromarray(rgba).save(HERE / 'sprig.png')
