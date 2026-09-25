"""Textures HD de l'arene (generees par Codex, style peint « Genshin ») -> textures pretes pour le jeu.

Lancement (Python de Blender : numpy + PIL) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" arena-remaster/textures/prepare_textures.py

Pour chaque image de arena-remaster/chatgpt/resultats/ :
  1. remise aux proportions de la texture d'origine (Codex recoit des images etirees en 1024x1024 ou 1536x1024) ;
  2. raccords : si la texture d'origine se repete sans couture, la nouvelle est corrigee sur ses bords
     (ecart de couleur lisse reparti pres des bords + fondu etroit sur la couture) ;
  3. alpha d'origine (128 = opaque sur PS2) ;
  4. deux versions de couleurs :
       genshin : les couleurs de Codex telles quelles ;
       fidele  : le dessin peint de Codex, mais les couleurs « de fond » (basses frequences) ramenees vers
                 celles de l'original, pour que l'arene reste reconnaissable.
Sorties : out/<version>/<nom>.png (apercu) et .rgba (octets RGBA pour le bridge), textures-<version>.json,
et une planche de comparaison qa/textures-versions.png.
"""
import json, math, sys
from pathlib import Path, PureWindowsPath
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KIT = ROOT / 'arena-remaster/chatgpt'
MANIFEST = {e['name']: e for e in json.loads((KIT / 'manifest.json').read_text())}
VERSIONS = ('genshin', 'fidele')


# ---------------------------------------------------------------- couleurs
def srgb_to_lab(rgb):
    c = rgb / 255.0
    c = np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    M = np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]])
    xyz = c @ M.T / np.array([.95047, 1.0, 1.08883])
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab_to_srgb(lab):
    fy = (lab[..., 0] + 16) / 116; fx = fy + lab[..., 1] / 500; fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], -1)
    xyz = np.where(f ** 3 > .008856, f ** 3, (f - 16 / 116) / 7.787) * np.array([.95047, 1.0, 1.08883])
    M = np.array([[3.2406, -1.5372, -.4986], [-.9689, 1.8758, .0415], [.0557, -.2040, 1.0570]])
    c = np.clip(xyz @ M.T, 0, 1)
    c = np.where(c <= .0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - .055)
    return np.clip(c * 255, 0, 255)


def blur(a, radius):
    """Flou gaussien qui boucle sur les bords (textures repetees)."""
    h, w = a.shape[:2]
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    gain = np.exp(-2 * (math.pi * radius) ** 2 * (fx * fx + fy * fy))       # gaussienne, convolution circulaire
    return np.stack([np.real(np.fft.ifft2(np.fft.fft2(a[..., ch]) * gain)) for ch in range(a.shape[-1])], -1)


def faithful(new_rgb, orig_rgb):
    """Dessin de Codex (hautes frequences) + couleurs de fond de l'original (basses frequences)."""
    h, w = new_rgb.shape[:2]
    up = np.asarray(Image.fromarray(orig_rgb.astype(np.uint8)).resize((w, h), Image.BICUBIC), float)
    a, b = srgb_to_lab(new_rgb), srgb_to_lab(up)
    r = max(w, h) / 24
    la, lb = blur(a, r), blur(b, r)
    out = a.copy()
    out[..., 0] = a[..., 0] - la[..., 0] + (.25 * la[..., 0] + .75 * lb[..., 0])     # luminosite de fond : surtout l'original
    out[..., 1:] = a[..., 1:] - la[..., 1:] + lb[..., 1:]                           # teinte de fond : l'original
    return lab_to_srgb(out)


# ---------------------------------------------------------------- raccords
def seam_ratio(img, axis):
    """Ecart a la couture (bord oppose) rapporte a l'ecart moyen entre voisins a l'interieur."""
    a = img.astype(float)
    if axis == 1:
        wrap = np.abs(a[:, 0] - a[:, -1]).mean(); inner = np.abs(np.diff(a, axis=1)).mean()
    else:
        wrap = np.abs(a[0] - a[-1]).mean(); inner = np.abs(np.diff(a, axis=0)).mean()
    return wrap / max(inner, 1e-6)


def fix_seam(img, axis):
    a = img.astype(float)
    if axis == 0: a = a.transpose(1, 0, 2)
    h, w = a.shape[:2]
    delta = a[:, :1] - a[:, -1:]                                        # (h,1,3)
    delta = blur(delta, max(1., h / 64))
    band = w / 6; x = np.arange(w, dtype=float)
    left = np.clip(1 - x / band, 0, 1) ** 2; right = np.clip(1 - (w - 1 - x) / band, 0, 1) ** 2
    a = a - delta * (.5 * left)[None, :, None] + delta * (.5 * right)[None, :, None]
    # fondu etroit sur la couture pour le detail fin restant
    m = max(2, w // 96)
    rolled = np.roll(a, m, axis=1)
    ring = blur(rolled[:, :2 * m], max(1., m / 2))
    wgt = (1 - np.abs(np.arange(2 * m) - m + .5) / m)[None, :, None]
    rolled[:, :2 * m] = rolled[:, :2 * m] * (1 - wgt) + ring * wgt
    a = np.roll(rolled, -m, axis=1)
    if axis == 0: a = a.transpose(1, 0, 2)
    return np.clip(a, 0, 255)


def main():
    names = sorted(p.stem for p in (KIT / 'resultats').glob('*.png') if p.stem in MANIFEST)
    lists = {v: [] for v in VERSIONS}
    rows = []
    for name in names:
        entry = MANIFEST[name]
        orig = np.asarray(Image.open(ROOT / entry['source']).convert('RGBA'))
        oh, ow = orig.shape[:2]
        gen = Image.open(KIT / 'resultats' / f'{name}.png').convert('RGB')
        w = min(gen.width, 2048) // 4 * 4; h = int(round(w * oh / ow / 4)) * 4
        if h > 2048: h = 2048; w = int(round(h * ow / oh / 4)) * 4
        rgb = np.asarray(gen.resize((w, h), Image.LANCZOS), float)
        fixes = []
        for axis in (1, 0):
            if seam_ratio(orig[..., :3], axis) < 2.0 and seam_ratio(rgb, axis) > 1.6:
                rgb = fix_seam(rgb, axis); fixes.append('horizontal' if axis == 1 else 'vertical')
        alpha = np.asarray(Image.fromarray(orig[..., 3]).resize((w, h), Image.BILINEAR))
        variants = {'genshin': rgb, 'fidele': faithful(rgb, orig[..., :3].astype(float))}
        for version, pix in variants.items():
            out = HERE / 'out' / version; out.mkdir(parents=True, exist_ok=True)
            rgba = np.dstack([np.clip(np.round(pix), 0, 255).astype(np.uint8), alpha.astype(np.uint8)])
            Image.fromarray(rgba[..., :3]).save(out / f'{name}.png')
            (out / f'{name}.rgba').write_bytes(rgba.tobytes())
            lists[version].append({'name': name, 'page': PureWindowsPath(entry['source']).parent.name,
                                   'rgba_file': str(out / f'{name}.rgba'), 'width': w, 'height': h})
        print(f'{name}: {ow}x{oh} -> {w}x{h}, raccords corriges : {", ".join(fixes) or "aucun"}', flush=True)
        rows.append((name, orig, variants))
    for version in VERSIONS:
        (HERE / f'textures-{version}.json').write_text(json.dumps({'textures': lists[version]}, indent=1))
    # planche : original | genshin | fidele (chaque case = 2x2 repetitions pour juger les raccords)
    S = 240
    sheet = Image.new('RGB', (3 * S, len(rows) * S), (30, 30, 30))
    for r, (name, orig, variants) in enumerate(rows):
        cells = [orig[..., :3].astype(np.uint8)] + [np.clip(variants[v], 0, 255).astype(np.uint8) for v in VERSIONS]
        for c, cell in enumerate(cells):
            t = Image.fromarray(cell).resize((S // 2, S // 2), Image.LANCZOS)
            for i in range(2):
                for j in range(2): sheet.paste(t, (c * S + i * S // 2, r * S + j * S // 2))
    sheet.save(ROOT / 'qa/textures-versions.png')


if __name__ == '__main__':
    main()
