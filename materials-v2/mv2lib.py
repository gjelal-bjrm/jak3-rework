"""Outils de creation des matieres v2 (numpy + PIL ; lances avec le Python de Blender).

Toutes les cartes se repetent sans couture : les bruits sont synthetises par transformee de Fourier (periodiques par
construction), les flous et les derivees sont periodiques.
Conventions des cartes (lues par materials_v2.glsl) :
  couleur  <nom>      : rvb = couleur propre de la matiere (sans ombre ni reflet peints), a = alpha d'origine ;
  relief   <nom>.n    : rv = normale (x vers +u, y vers +v, c'est-a-dire vers le bas de l'image), b = hauteur,
                        a = part du grain du monde (1 = plein, 0 = aucun : verre, lumiere) ;
  matiere  <nom>.m    : r = rugosite, v = metal, b = lumiere emise, a = creux (1 = degage, 0 = au fond d'un creux).
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0., 1.)
    return t * t * (3. - 2. * t)


def grid(w, h):
    """u, v au centre des pixels (0..1), u vers la droite, v vers le bas."""
    u = (np.arange(w) + .5) / w; v = (np.arange(h) + .5) / h
    return np.meshgrid(u, v)


def fft_noise(w, h, beta, seed, lo=0., hi=1e9):
    """Bruit periodique de spectre 1/f^beta, limite aux frequences lo..hi (cycles par repetition). Moyenne 0, ecart 1."""
    rng = np.random.default_rng(seed)
    fx = np.fft.fftfreq(w) * w; fy = np.fft.fftfreq(h) * h
    f = np.hypot(*np.meshgrid(fx, fy))
    amp = np.where((f >= max(lo, .5)) & (f <= hi), 1. / np.maximum(f, .5) ** (beta / 2.), 0.)
    spec = amp * np.exp(2j * np.pi * rng.random((h, w)))
    out = np.fft.ifft2(spec).real
    return (out - out.mean()) / (out.std() + 1e-12)


def blur(a, sigma):
    """Flou gaussien periodique (sigma en pixels)."""
    if sigma <= 0: return a
    h, w = a.shape
    fx = np.fft.fftfreq(w); fy = np.fft.fftfreq(h)
    k = np.exp(-2. * (np.pi * sigma) ** 2 * (fx[None, :] ** 2 + fy[:, None] ** 2))
    return np.fft.ifft2(np.fft.fft2(a) * k).real


def splats(w, h, count, sigma, seed, amp=(.5, 1.)):
    """Somme de bosses gaussiennes placees au hasard (periodique). Sert aux creux, aux marques de martelage."""
    rng = np.random.default_rng(seed)
    imp = np.zeros((h, w))
    xs = rng.integers(0, w, count); ys = rng.integers(0, h, count)
    np.add.at(imp, (ys, xs), rng.uniform(amp[0], amp[1], count))
    return blur(imp, sigma) * (2. * np.pi * sigma * sigma)


def scratches(w, h, count, seed, length=(.05, .35), width=1.2, angle=None, spread=3.14159):
    """Rayures fines, droites, au hasard (periodiques). Renvoie 0..1 (1 = au fond de la rayure)."""
    rng = np.random.default_rng(seed)
    s = 2
    img = Image.new('L', (w * s, h * s), 0); d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.random() * w * s, rng.random() * h * s
        a = (rng.random() * 2 - 1) * spread + (angle or 0.)
        L = rng.uniform(*length) * max(w, h) * s
        dx, dy = np.cos(a) * L / 2, np.sin(a) * L / 2
        val = int(rng.uniform(90, 255))
        for ox in (-w * s, 0, w * s):
            for oy in (-h * s, 0, h * s):
                d.line((x - dx + ox, y - dy + oy, x + dx + ox, y + dy + oy), fill=val, width=max(1, int(round(width * s))))
    return np.asarray(img.resize((w, h), Image.BOX), float) / 255.


def normal_from_height(hm, metres_u, metres_v, gain=1.):
    """Hauteur (m) -> normale. metres_u / metres_v : taille d'une repetition dans le monde."""
    h, w = hm.shape
    dx = (np.roll(hm, -1, 1) - np.roll(hm, 1, 1)) / (2. * metres_u / w)
    dy = (np.roll(hm, -1, 0) - np.roll(hm, 1, 0)) / (2. * metres_v / h)
    n = np.stack([-dx * gain, -dy * gain, np.ones_like(hm)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def cavity(hm, sigma, scale):
    """Creux : 1 = degage, 0 = au fond d'un creux (hauteur sous la moyenne du voisinage)."""
    return np.clip(1. + (hm - blur(hm, sigma)) / scale, 0., 1.)


def edges(hm, sigma, scale):
    """Aretes saillantes (usure, metal poli) : 0..1."""
    return np.clip((hm - blur(hm, sigma)) / scale, 0., 1.)


def to8(a):
    return np.clip(np.round(a * 255.), 0, 255).astype(np.uint8)


def pack_normal(n, height01, grain):
    h, w = height01.shape
    g = np.broadcast_to(np.asarray(grain, float), (h, w))
    return np.dstack([to8(n[..., 0] * .5 + .5), to8(n[..., 1] * .5 + .5), to8(height01), to8(g)])


def pack_matter(rough, metal, emit, cav):
    shape = np.broadcast(rough, metal, emit, cav).shape
    f = lambda x: to8(np.broadcast_to(np.asarray(x, float), shape))
    return np.dstack([f(rough), f(metal), f(emit), f(cav)])


def save(out_dir, name, rgba):
    """Ecrit <nom>.rgba (pour le niveau) + <nom>.png (apercu). Renvoie la fiche pour le patch."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    rgba = np.ascontiguousarray(rgba)
    path = out_dir / f'{name}.rgba'
    data = rgba.tobytes()
    if not (path.exists() and path.read_bytes() == data): path.write_bytes(data)
    Image.fromarray(rgba[..., :3]).save(out_dir / f'{name}.png')
    return {'name': name, 'rgba_file': str(path), 'width': int(rgba.shape[1]), 'height': int(rgba.shape[0])}


def colour_field(base_rgb, lum, sat=1.):
    """Couleur de base (0..255) modulee par une luminance relative (1 = neutre)."""
    base = np.asarray(base_rgb, float) / 255.
    out = base[None, None, :] * lum[..., None]
    if sat != 1.:
        y = out @ np.array([.2126, .7152, .0722])
        out = y[..., None] + (out - y[..., None]) * sat
    return out
