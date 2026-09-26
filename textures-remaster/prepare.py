"""Textures HD du kit Codex (tout le decor, style « Genshin ») -> textures pretes pour le jeu.

Lancement (Python de Blender : numpy + PIL) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" textures-remaster/prepare.py

Pour chaque image de textures-remaster/codex/resultats/ (nouvelle ou modifiee) :
  1. texture repetee dans l'image (champ `tiles` du manifeste) : on garde la repetition du milieu (la moins
     touchee par les bords), aux proportions de la texture d'origine ;
  2. taille : plus grand cote 1024 (au-dela, le chargement des niveaux ralentit sans gain visible en jeu) ;
  3. raccords : si la texture d'origine se repete sans couture, les bords de la nouvelle sont corriges ;
  4. alpha d'origine (textures a alpha uniforme seulement : les decoupes sont exclues du kit) ;
  5. teinte : Codex rechauffe et eclaircit presque tout. Quand la teinte moyenne s'ecarte franchement de
     l'original (ecart a*b* > 20), elle y est ramenee a 80 % (luminosite moyenne a 50 %), sans toucher au
     dessin. Raison : le jeu colore les textures par l'eclairage des sommets ; dans le desert, un sol gris-vert
     devenu orange donnait orange x orange = jaune criard (verifie en jeu, qa/sand-diag.png).
Textures refusees apres controle (hors sujet, couleurs trahies) : rejets.json (nom -> raison) ; le jeu garde
l'original, et la liste sert a redemander ces textures a Codex.
Sorties : out/<nom>.rgba (+ .png d'apercu) et textures.json (liste pour remaster-build/build.py).
"""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'arena-remaster/textures'))
from prepare_textures import seam_ratio, fix_seam, srgb_to_lab, lab_to_srgb   # memes outils que l'arene

KIT = HERE / 'codex'
OUT = HERE / 'out'
MAX_SIDE = 1024
VERSION = 4                      # 3 : balance des blancs ; 4 : + FORCE_HUE ; teinte ramenee vers l'original (balance des blancs) si elle s'en ecarte franchement
HUE_LIMIT, HUE_BACK, LIGHT_BACK = 20.0, .8, .5
# teinte ramenee quel que soit l'ecart (constat en jeu) : dalles plates du desert, orange vif sur le sable pale
FORCE_HUE = {'des-rock-01'}


def keep_hue(pix, orig_rgb, force=False):
    """Teinte et luminosite moyennes ramenees vers l'original, dessin intact. Renvoie (pixels, ecart a*b*).

    Correction du type « balance des blancs » : chaque canal est multiplie (en lumiere lineaire) ; les zones sombres
    restent sombres et aucune teinte opposee n'apparait (un decalage uniforme de a*b* bleuissait les stries
    sombres, ex. tronc des palmiers)."""
    a = srgb_to_lab(pix); b = srgb_to_lab(orig_rgb.astype(float))
    d = b[..., 1:].reshape(-1, 2).mean(0) - a[..., 1:].reshape(-1, 2).mean(0)
    gap = float(np.linalg.norm(d))
    if gap <= HUE_LIMIT and not force: return pix, gap
    lin = lambda c: np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    srgb = lambda c: np.where(c <= .0031308, 12.92 * c, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - .055)
    L = np.array([.2126, .7152, .0722])
    x = lin(pix / 255.); o = lin(orig_rgb.astype(float) / 255.)
    mx = x.reshape(-1, 3).mean(0); mo = o.reshape(-1, 3).mean(0)
    balance = (mo / (mo @ L)) / (mx / (mx @ L))                       # rapport de teinte, luminosite egale
    y = x * balance ** HUE_BACK
    target = (mx @ L) ** (1 - LIGHT_BACK) * (mo @ L) ** LIGHT_BACK   # luminosite moyenne : a mi-chemin
    y *= target / max((y.reshape(-1, 3).mean(0) @ L), 1e-6)
    return np.clip(srgb(np.clip(y, 0, 1)) * 255, 0, 255), gap


def main():
    manifest = {e['name']: e for e in json.loads((KIT / 'manifest.json').read_text(encoding='utf-8'))}
    rejects = json.loads((HERE / 'rejets.json').read_text(encoding='utf-8')) if (HERE / 'rejets.json').exists() else {}
    OUT.mkdir(exist_ok=True)
    listing, made = [], 0
    for png in sorted((KIT / 'resultats').glob('*.png')):
        e = manifest.get(png.stem)
        if not e or png.stem in rejects: continue
        rgba = OUT / f'{png.stem}.rgba'
        entry = None
        meta = json.loads((OUT / f'{png.stem}.json').read_text()) if (OUT / f'{png.stem}.json').exists() else {}
        if rgba.exists() and rgba.stat().st_mtime >= png.stat().st_mtime and meta.get('version') == VERSION:
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
            pix, gap = keep_hue(pix, orig[..., :3], png.stem in FORCE_HUE)
            for axis in (1, 0):
                if seam_ratio(orig[..., :3], axis) < 2.0 and seam_ratio(pix, axis) > 1.6: pix = fix_seam(pix, axis)
            alpha = np.full((h, w), int(orig[..., 3].max()), np.uint8)
            out = np.dstack([np.clip(np.round(pix), 0, 255).astype(np.uint8), alpha])
            data = out.tobytes()
            if not (rgba.exists() and rgba.read_bytes() == data):    # identique : on garde la date (pas de reconstruction)
                rgba.write_bytes(data)
                Image.fromarray(out[..., :3]).save(OUT / f'{png.stem}.png')
                made += 1
            entry = {'name': png.stem, 'rgba_file': str(rgba), 'width': w, 'height': h, 'version': VERSION,
                     'hue_gap': round(gap, 1), 'hue_back': gap > HUE_LIMIT or png.stem in FORCE_HUE}
            (OUT / f'{png.stem}.json').write_text(json.dumps(entry))
        listing.append(entry)
    (HERE / 'textures.json').write_text(json.dumps({'textures': listing}, indent=1))
    back = sum(1 for x in listing if x.get('hue_back'))
    print(f'{len(listing)} textures pretes ({made} nouvelles ou modifiees, {len(rejects)} refusees, '
          f'{back} teintes ramenees vers celle de l original)')


if __name__ == '__main__':
    main()
