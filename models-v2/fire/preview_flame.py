"""Apercu hors jeu de la nappe de flamme (meme calcul que modern_fire.frag), pour regler la forme vite.
Lancement : python de Blender (numpy + PIL) : preview_flame.py [sortie.png]
Planche : 6 instants x 3 nappes superposees, fond sombre et fond clair.
"""
import sys
import numpy as np
from PIL import Image

W, H = 220, 300


def hash2(x, y):
    q = np.stack([x, y, x], -1) * .1031
    q = q - np.floor(q)
    d = (q * (q[..., [1, 2, 0]] + 33.33)).sum(-1, keepdims=True)
    q = q + d
    return (q[..., 0] + q[..., 1]) * q[..., 2] - np.floor((q[..., 0] + q[..., 1]) * q[..., 2])


def noise(x, y):
    ix, iy = np.floor(x), np.floor(y); fx, fy = x - ix, y - iy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a, b = hash2(ix, iy), hash2(ix + 1, iy); c, d = hash2(ix, iy + 1), hash2(ix + 1, iy + 1)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(x, y):
    v, a = 0, .5
    for _ in range(4):
        v = v + a * noise(x, y)
        x, y = 1.6 * x - 1.2 * y + 3.1, 1.2 * x + 1.6 * y + 3.1
        a *= .5
    return v


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


P = dict(width=.62, tongue=.5, lick=.95, lick2=.38, puff=.55, edge=.05, speed=1.05)


def flame(time, seed, layer_weight):
    ys, xs = np.mgrid[0:H, 0:W]
    x = (xs / (W - 1) * 2 - 1) * 1.5
    y = (1 - ys / (H - 1)) * 1.47 - .12
    t = time * P['speed'] + seed * 7
    # turbulence qui monte (domaine tordu), plus forte en hauteur
    w1 = fbm(x * 1.5 + seed, y * 1.8 - t * 1.7)
    w2 = fbm(x * 3.4 - seed * 1.3, y * 3.9 - t * 2.9)
    lean = (w1 - .5) * 1.1 * y + (w2 - .5) * .42 * y
    xw = x + lean
    tip = .95 + .10 * np.sin(t * 2.1 + seed) + .06 * np.sin(t * 4.9 + seed * 2.1)
    yy = y / tip
    # plusieurs langues : largeur modulee par un bruit horizontal qui monte
    tongues = fbm(xw * 2.9 + seed * 5.1, yy * 1.0 - t * 1.55)
    width = (.95 + (.02 - .95) * np.clip(yy, 0, 1) ** .55) * (.18 + 1.45 * tongues)
    body = width - np.abs(xw) * 1.05
    # lechage fin des bords
    lick = fbm(xw * 6.0 + seed * 3, yy * 2.4 - t * 4.2)
    body = body + (lick - .5) * .42 * smooth(.08, .8, yy)
    # base plate au niveau des braises, bouts qui se detachent au-dessus
    body = body - smooth(.55, 1.08, yy + (w2 - .5) * .7) * .6
    mask = smooth(0, .045, body) * smooth(-.07, .10, yy)
    inner = smooth(.10, .42, body)
    heat = np.clip(inner * (1.05 - yy * .9) + (1 - yy) * .10, 0, 1) * smooth(-.05, .12, yy)
    c0, c1, c2 = np.array([.78, .10, .02]), np.array([1.45, .46, .06]), np.array([1.65, 1.12, .40])
    k1 = smooth(0, .40, heat)[..., None]; c = c0 * (1 - k1) + c1 * k1
    k2 = smooth(.50, .95, heat)[..., None]; c = c * (1 - k2) + c2 * k2
    glow = np.exp(-x * x * 1.2) * np.exp(-np.maximum(yy, 0) * 1.6) * smooth(-.10, .05, yy) * .18
    return (c * mask[..., None] * layer_weight + np.array([1.2, .38, .06]) * glow[..., None]) * .8


def sheet(path):
    cols = []
    for bg in (np.array([.06, .05, .05]), np.array([.55, .50, .45])):
        row = []
        for k in range(6):
            rgb = np.zeros((H, W, 3)) + bg
            for layer, wgt in ((0, .72), (1, 1.), (2, .72)):
                rgb = rgb + flame(k * .37, 3.3 + layer * 3.71, wgt)
            rgb = rgb / (1 + rgb * .25)                       # doux ecrasement des hautes lumieres
            row.append(np.clip(rgb, 0, 1))
        cols.append(np.concatenate(row, 1))
    img = (np.concatenate(cols, 0) * 255).astype(np.uint8)
    Image.fromarray(img).save(path)


if __name__ == '__main__':
    sheet(sys.argv[1] if len(sys.argv) > 1 else 'flame-preview.png')
