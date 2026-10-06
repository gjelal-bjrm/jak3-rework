"""Controle des textures Codex avant integration : planches « original | nouveau », suspects en tete.

Lancement (Python de Blender : numpy + PIL) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" textures-remaster/review.py [--depuis AAAA-MM-JJ]

Textures controlees : celles preparees par prepare.py (fiches out/*.json) dont le resultat Codex date de --depuis ou
plus tard, hors refusees (rejets.json) et hors deja acceptees (revues.json). Chaque texture recoit un score de
suspicion, d'apres les refus des lots precedents :
  - dessin change : original structure (panneau, motif, inscription) mais disposition differente ;
  - degrade doux (halo, lumiere, carte de reflets) devenu une peinture granuleuse ;
  - couleur trahie (ecart de teinte avant correction, luminosite tres changee) ;
  - noms a risque (reflets, halos, lumieres, feu, yeux, inscriptions).
Sorties : qa/codex-revue-NN.png (56 paires par planche, les plus suspectes d'abord) et
textures-remaster/revue-metriques.json. Apres controle : refus dans rejets.json (nom -> raison), le reste est
ajoute a revues.json par --accepter.
"""
from pathlib import Path
import json, sys, time
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
QA = ROOT / 'qa'
RISKY = ('env', 'glow', 'light', 'lamp', 'halo', 'flare', 'shine', 'beam', 'fire', 'flame', 'coal', 'eye', 'sign',
         'logo', 'text', 'letter', 'number', 'poster', 'screen', 'map', 'icon', 'font', 'face', 'skull', 'lens')


def load(path, size=None):
    img = Image.open(path).convert('RGB')
    if size: img = img.resize(size, Image.BILINEAR)
    return np.asarray(img, float) / 255.


def luma(x): return x @ np.array([.2126, .7152, .0722])


def lab(x):
    lin = np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)
    m = np.array([[.4124, .3576, .1805], [.2126, .7152, .0722], [.0193, .1192, .9505]])
    xyz = lin @ m.T / np.array([.9505, 1., 1.089])
    f = np.where(xyz > .008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def roughness(x):
    """Grain : ecart moyen au voisinage (laplacien) rapporte a la luminosite (64 x 64)."""
    y = luma(x)
    lap = np.abs(4 * y[1:-1, 1:-1] - y[:-2, 1:-1] - y[2:, 1:-1] - y[1:-1, :-2] - y[1:-1, 2:])
    return float(lap.mean() / (y.mean() + .05))


def metrics(name, entry, manifest):
    e = manifest[name]
    orig_path, new_path = ROOT / e['source'], HERE / 'out' / f'{name}.png'
    o16, n16 = luma(load(orig_path, (16, 16))), luma(load(new_path, (16, 16)))
    o64, n64 = load(orig_path, (64, 64)), load(new_path, (64, 64))
    so = float(o16.std() / (o16.mean() + .05))
    corr = float(np.corrcoef(o16.ravel(), n16.ravel())[0, 1]) if o16.std() > 1e-4 and n16.std() > 1e-4 else 1.
    lo, ln = lab(o64).reshape(-1, 3).mean(0), lab(n64).reshape(-1, 3).mean(0)
    ro, rn = roughness(o64), roughness(n64)
    score, why = 0., []
    if so > .15 and corr < .5: score += (.5 - corr) * 4; why.append(f'dessin {corr:.2f}')
    if ro < .05 and rn > max(2.5 * ro, .05): score += 2.; why.append(f'grain {ro:.2f}->{rn:.2f}')
    gap = entry.get('hue_gap', 0.)
    if gap > 30: score += (gap - 30) / 20; why.append(f'teinte {gap:.0f}')
    if abs(ln[0] - lo[0]) > 15: score += abs(ln[0] - lo[0]) / 30; why.append(f'lum {ln[0] - lo[0]:+.0f}')
    if any(k in name for k in RISKY): score += 1.5; why.append('nom')
    return {'name': name, 'score': round(score, 2), 'why': ', '.join(why), 'corr': round(corr, 2),
            'structure': round(so, 2), 'grain': [round(ro, 3), round(rn, 3)], 'level': e['level'],
            'source': str(orig_path), 'new': str(new_path)}


def thumb(path, box):
    img = Image.open(path).convert('RGBA')
    a = np.asarray(img).copy(); a[..., 3] = np.minimum(255, a[..., 3].astype(int) * 2)   # alpha PS2 : 128 = opaque
    img = Image.alpha_composite(Image.new('RGBA', img.size, (255, 0, 255, 255)), Image.fromarray(a)).convert('RGB')
    img.thumbnail((box, box), Image.NEAREST if max(img.size) < box else Image.LANCZOS)
    if max(img.size) < box:
        k = box / max(img.size); img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.NEAREST)
    return img


def sheets(items, prefix, cols=8, rows=7, box=120):
    cw, ch = 2 * box + 12, box + 18
    pages = [items[i:i + cols * rows] for i in range(0, len(items), cols * rows)]
    out = []
    for k, page in enumerate(pages):
        sheet = Image.new('RGB', (cols * cw, rows * ch), (24, 24, 24)); d = ImageDraw.Draw(sheet)
        for i, m in enumerate(page):
            x, y = (i % cols) * cw, (i // cols) * ch
            sheet.paste(thumb(m['source'], box), (x + 2, y + 2)); sheet.paste(thumb(m['new'], box), (x + box + 8, y + 2))
            label = f"{len(out) * cols * rows + i + 1} {m['name'][:30]}"
            d.text((x + 2, y + box + 4), label, fill=(255, 220, 80) if m['score'] >= 1.5 else (200, 200, 200))
        path = QA / f'{prefix}-{k:02d}.png'; sheet.save(path); out.append(path)
    return out


def main(args):
    since = None
    if '--depuis' in args: since = time.mktime(time.strptime(args[args.index('--depuis') + 1], '%Y-%m-%d'))
    manifest = {e['name']: e for e in json.loads((HERE / 'codex/manifest.json').read_text(encoding='utf-8'))}
    # fiches ecrites par prepare.py au fil du traitement (on peut controler avant la fin de la preparation)
    listing = [json.loads(p.read_text()) for p in sorted((HERE / 'out').glob('*.json'))]
    rejects = json.loads((HERE / 'rejets.json').read_text(encoding='utf-8'))
    reviewed_path = HERE / 'revues.json'
    reviewed = set(json.loads(reviewed_path.read_text(encoding='utf-8'))) if reviewed_path.exists() else set()
    todo = []
    for entry in listing:
        name = entry['name']
        if name in rejects or name in reviewed or name not in manifest: continue
        if all(l.startswith('museum') for l in manifest[name]['levels']): continue   # personnages exposes
        res = HERE / 'codex/resultats' / f'{name}.png'
        if since and res.stat().st_mtime < since: continue
        todo.append(entry)
    if '--accepter' in args:   # tout ce qui reste (non refuse) est accepte
        reviewed |= {e['name'] for e in todo}
        reviewed_path.write_text(json.dumps(sorted(reviewed), indent=0), encoding='utf-8')
        print(f'{len(todo)} textures acceptees ({len(reviewed)} en tout)'); return
    found = sorted((metrics(e['name'], e, manifest) for e in todo), key=lambda m: -m['score'])
    (HERE / 'revue-metriques.json').write_text(json.dumps(found, indent=1), encoding='utf-8')
    paths = sheets(found, 'codex-revue')
    print(f'{len(found)} textures a controler, {sum(m["score"] >= 1.5 for m in found)} suspectes ; planches : '
          f'{paths[0].name} .. {paths[-1].name}' if paths else 'rien a controler')


if __name__ == '__main__':
    main(sys.argv[1:])
