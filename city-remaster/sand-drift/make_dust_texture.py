"""Texture haute resolution de la bouffee de poussiere (remplace dirtpuff01, 256x256).

Nuage rond au contour erode par du bruit fractal, volutes internes, grain fin, plus clair en haut
(soleil). Alpha en forme de nuage, maximum ~0,9 pour garder l'intensite de l'original (dont le
sprite atteignait l'opacite maximale au centre). La couleur du sprite (170,150,120) est appliquee par
le jeu : la texture reste claire et presque neutre.

Ecrit dirtpuff01-hd.png (apercu) et dirtpuff01-hd.rgba (u32 w, u32 h, RGBA8) puis installe le .rgba dans
data/custom_assets/jak3/city-dust/ et dans les trois variantes (empreintes).
"""
from pathlib import Path
import hashlib, json, math, random, shutil, struct
from PIL import Image, ImageFilter
H = Path(__file__).resolve().parent; R = H.parents[1]
SIZE = 256
REL = 'custom_assets/jak3/city-dust/dirtpuff01-hd.rgba'


def value_noise(size, cells, seed):
    rnd = random.Random(seed)
    grid = [[rnd.random() for _ in range(cells + 1)] for _ in range(cells + 1)]
    out = [[0.0] * size for _ in range(size)]
    for y in range(size):
        fy = y / size * cells; iy = int(fy); ty = fy - iy; ty = ty * ty * (3 - 2 * ty)
        for x in range(size):
            fx = x / size * cells; ix = int(fx); tx = fx - ix; tx = tx * tx * (3 - 2 * tx)
            a, b = grid[iy][ix], grid[iy][ix + 1]; c, d = grid[iy + 1][ix], grid[iy + 1][ix + 1]
            out[y][x] = (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty
    return out


def fbm(size, seed, octaves=(4, 8, 16, 32), weights=(.5, .25, .15, .1)):
    layers = [value_noise(size, c, seed + i) for i, c in enumerate(octaves)]
    total = sum(weights)
    return [[sum(w * l[y][x] for w, l in zip(weights, layers)) / total for x in range(size)] for y in range(size)]


def main():
    n1 = fbm(SIZE, 11); n2 = fbm(SIZE, 23, (6, 12, 24, 48)); grain = value_noise(SIZE, 64, 41)
    img = Image.new('RGBA', (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            u = (x + .5) / SIZE * 2 - 1; v = (y + .5) / SIZE * 2 - 1
            r = math.hypot(u, v)
            ang = math.atan2(v, u)
            # rayon du nuage module par le bruit (volutes), contour doux
            edge = .62 + .30 * (n1[y][x] - .5) * 2
            body = max(0.0, min(1.0, (edge - r) / .30))
            body = body * body * (3 - 2 * body)
            volutes = .55 + .45 * max(0.0, min(1.0, (n2[y][x] - .35) / .35))
            g = .85 + .15 * grain[y][x]
            alpha = body * volutes * g
            # plus clair vers le haut (soleil), plus dense au centre-bas
            lit = .82 + .18 * (-v) * .5 + .10 * (n2[y][x] - .5)
            base = (0.97, 0.94, 0.88)
            rgb = tuple(int(max(0, min(255, c * lit * 255))) for c in base)
            px[x, y] = (rgb[0], rgb[1], rgb[2], int(max(0, min(230, alpha * 235))))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    img.save(H / 'dirtpuff01-hd.png')
    raw = struct.pack('<II', SIZE, SIZE) + img.tobytes()
    (H / 'dirtpuff01-hd.rgba').write_bytes(raw)
    # installation : data + variantes + empreintes (comme les shaders)
    files = json.loads((R / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((R / 'variant-hashes.json').read_text(encoding='utf-8'))
    for base in [R / 'data'] + [R / 'variants' / v for v in ('original', 'remaster-v1', 'remaster')]:
        target = base / REL; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(H / 'dirtpuff01-hd.rgba', target)
    for v in ('original', 'remaster-v1', 'remaster'):
        hashes.setdefault(v, {})[REL] = hashlib.sha256((R / 'variants' / v / REL).read_bytes()).hexdigest()
    if REL not in files: files.append(REL)
    (R / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (R / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
    print('texture poussiere HD installee :', REL, hashes['remaster'][REL][:12])


if __name__ == '__main__': main()
