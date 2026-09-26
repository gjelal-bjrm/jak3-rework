"""Textures HD du kit Codex (tout le decor, style « Genshin ») -> textures pretes pour le jeu.

Lancement (Python de Blender : numpy + PIL) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" textures-remaster/prepare.py

Pour chaque image de textures-remaster/codex/resultats/ (nouvelle ou modifiee) :
  1. texture repetee dans l'image (champ `tiles` du manifeste) : on garde la repetition du milieu (la moins
     touchee par les bords), aux proportions de la texture d'origine ;
  2. taille : plus grand cote 1024 (au-dela, le chargement des niveaux ralentit sans gain visible en jeu) ;
  3. raccords : si la texture d'origine se repete sans couture, les bords de la nouvelle sont corriges ;
  4. alpha d'origine (textures a alpha uniforme seulement : les decoupes sont exclues du kit).
Sorties : out/<nom>.rgba (+ .png d'apercu) et textures.json (liste pour remaster-build/build.py).
"""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'arena-remaster/textures'))
from prepare_textures import seam_ratio, fix_seam      # meme correction des raccords que l'arene

KIT = HERE / 'codex'
OUT = HERE / 'out'
MAX_SIDE = 1024


def main():
    manifest = {e['name']: e for e in json.loads((KIT / 'manifest.json').read_text(encoding='utf-8'))}
    OUT.mkdir(exist_ok=True)
    listing, made = [], 0
    for png in sorted((KIT / 'resultats').glob('*.png')):
        e = manifest.get(png.stem)
        if not e: continue
        rgba = OUT / f'{png.stem}.rgba'
        entry = None
        if rgba.exists() and rgba.stat().st_mtime >= png.stat().st_mtime:
            meta = json.loads((OUT / f'{png.stem}.json').read_text())
            entry = meta
        else:
            ow, oh = e['source_size']; nx, ny = e['tiles']
            gen = Image.open(png).convert('RGB')
            tw, th = gen.width / nx, gen.height / ny
            ix, iy = nx // 2, ny // 2                          # repetition du milieu
            tile = gen.crop((round(ix * tw), round(iy * th), round((ix + 1) * tw), round((iy + 1) * th)))

            w = max(4, int(min(MAX_SIDE, tile.width) // 4 * 4))
            h = max(4, int(round(w * oh / ow / 4)) * 4)
            if h > MAX_SIDE: h = MAX_SIDE; w = max(4, int(round(h * ow / oh / 4)) * 4)
            pix = np.asarray(tile.resize((w, h), Image.LANCZOS), float)
            orig = np.asarray(Image.open(ROOT / e['source']).convert('RGBA'))
            for axis in (1, 0):
                if seam_ratio(orig[..., :3], axis) < 2.0 and seam_ratio(pix, axis) > 1.6: pix = fix_seam(pix, axis)
            alpha = np.full((h, w), int(orig[..., 3].max()), np.uint8)
            out = np.dstack([np.clip(np.round(pix), 0, 255).astype(np.uint8), alpha])
            rgba.write_bytes(out.tobytes())
            Image.fromarray(out[..., :3]).save(OUT / f'{png.stem}.png')
            entry = {'name': png.stem, 'rgba_file': str(rgba), 'width': w, 'height': h}
            (OUT / f'{png.stem}.json').write_text(json.dumps(entry))
            made += 1
        listing.append(entry)
    (HERE / 'textures.json').write_text(json.dumps({'textures': listing}, indent=1))
    print(f'{len(listing)} textures pretes ({made} nouvelles)')


if __name__ == '__main__':
    main()
