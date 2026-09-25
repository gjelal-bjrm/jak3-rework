"""Kit Codex pour TOUTES les textures de decor restantes du jeu (style peint « Genshin », valide sur l'arene).

Lancement (Python de Blender : PIL + numpy) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" textures-remaster/make_codex_kit.py

Produit textures-remaster/codex/ (hors Git : contient des textures du jeu) :
  envoyer/<nom>.png, resultats/, manifest.json (ordre de l'histoire), INSTRUCTIONS-CODEX.md, PROMPT.txt.

Lecons de l'arene appliquees :
  - style « Genshin » demande des le depart (choix du joueur) ;
  - raccords parfaits sur les quatre bords (textures repetees en jeu) ;
  - plus d'image etiree : une texture allongee (2:1, 4:1...) est REPETEE pour remplir un format accepte
    (1024x1024, 1536x1024, 1024x1536) puis recoupee a l'integration (le dessin garde ses proportions) ;
  - une meme texture presente dans plusieurs lieux n'est generee qu'une fois (installee partout ensuite).
Exclus : personnages et PNJ (pages -pris), les 76 textures deja faites (arene), l'eau et les effets animes
(-water, -sprite, -warp : refaits par le rendu), cartes (-minimap), feuillages et decoupes transparentes
(alpha variable : la silhouette doit rester exacte), aplats minuscules ou unis.
"""
from pathlib import Path
import json, math, re, shutil
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'data/decompiler_out/jak3/textures'
OUT = ROOT / 'textures-remaster/codex'
DONE = {e['name'] for e in json.loads((ROOT / 'arena-remaster/chatgpt/manifest.json').read_text())}

# Ordre de l'histoire (prefixes de lieux), puis lieu -> description courte pour le contexte
STORY = [
    ('wasintro', 'the Wasteland desert where Jak is exiled (intro)'), ('introcst', 'the Wasteland desert (intro)'),
    ('wascity', 'Spargus, a sunny desert city of sandstone, wood, cloth and scrap metal'),
    ('waswide', 'Spargus city and its surroundings'), ('wasdoors', 'the gates of Spargus city'),
    ('arenacst', 'the Spargus arena'), ('wasstad', 'the Spargus arena'),
    ('waspala', "Damas' palace in Spargus, sandstone with turquoise water"), ('intpal', "Damas' palace"),
    ('desert', 'the open Wasteland desert, sand dunes and orange rock'), ('des', 'the Wasteland desert'),
    ('temple', 'the ancient Precursor temple in the desert, carved stone and old metal'),
    ('volcano', 'the volcano, dark basalt and lava'),
    ('ctysluma', 'the slums of Haven City, old wood and rusty metal'), ('ctyslum', 'the slums of Haven City'),
    ('slumbset', 'the slums of Haven City'), ('ctyport', 'the port of Haven City'),
    ('ctyfarm', 'the farm district of Haven City'), ('ctygen', 'Haven City'), ('ctyind', 'the industrial district of Haven City'),
    ('ctywide', 'Haven City, a futuristic walled city'), ('hiphog', 'the Hip Hog saloon in Haven City'),
    ('gungame', 'the gun course of Haven City'), ('freehq', 'the Freedom League headquarters'),
    ('onintent', "Onin's tent"), ('vinroom', "Vin's power station room"), ('powergd', 'the power station'),
    ('lcity', 'Haven City'), ('lcty', 'Haven City'), ('mine', 'the mines, rock tunnels and old machinery'),
    ('sew', 'the sewers of Haven City, wet stone and pipes'), ('forest', 'the lush forest'),
    ('mhcity', 'the Metal Head city, organic dark alien structures'), ('lmhcity', 'the Metal Head city'),
    ('factory', 'the war factory, industrial metal'), ('lfac', 'the war factory'),
    ('rubble', 'the destroyed parts of Haven City'), ('rublcst', 'the destroyed parts of Haven City'),
    ('stadium', 'the Haven stadium'), ('ltower', 'the Precursor tower'), ('tower', 'the Precursor tower'),
    ('nst', 'the Metal Head nest'), ('lnst', 'the Metal Head nest'), ('comb', 'the Precursor catacombs'),
    ('rail', 'the Precursor rail tunnels'), ('precur', 'the Precursor ship'), ('lprecur', 'the Precursor ship'),
    ('hang', 'the glider hangar'), ('halfpipe', 'the halfpipe course'), ('museum', 'the museum'),
    ('lpatt', 'Haven City'), ('lppatrol', 'Haven City'), ('lpatkcs', 'Haven City'), ('lblowcst', 'Haven City'),
    ('ltnjxhip', 'Haven City'), ('ltowcity', 'Haven City'), ('lfreeout', 'Haven City'), ('lctydest', 'Haven City'),
    ('lctyhijk', 'Haven City'), ('lctypatk', 'Haven City'), ('lctysnpr', 'Haven City'), ('loutro', 'the ending'),
    ('temp', 'the desert temple'), ('level-default', 'common scenery'),
]
KEEP = ('-tfrag', '-shrub', '-alpha')
HINTS = [('rock', 'rock'), ('stone', 'stone'), ('brick', 'bricks'), ('sand', 'sand'), ('dirt', 'dirt'),
         ('grass', 'grass'), ('moss', 'moss'), ('mud', 'mud'), ('metal', 'metal'), ('steel', 'steel'),
         ('rust', 'rusty metal'), ('iron', 'iron'), ('wood', 'wood'), ('plank', 'wooden planks'), ('bark', 'tree bark'),
         ('roof', 'roof'), ('tile', 'tiles'), ('pipe', 'pipes'), ('door', 'door'), ('window', 'window'),
         ('glass', 'glass'), ('cloth', 'cloth'), ('canvas', 'canvas'), ('rope', 'rope'), ('panel', 'panel'),
         ('plate', 'metal plate'), ('grate', 'metal grating'), ('trim', 'trim'), ('wall', 'wall'), ('floor', 'floor'),
         ('ground', 'ground'), ('path', 'path'), ('road', 'road'), ('precursor', 'ancient Precursor alien metal'),
         ('eco', 'glowing eco'), ('crystal', 'crystal'), ('lava', 'lava rock'), ('pillar', 'pillar'), ('column', 'column'),
         ('stucco', 'stucco'), ('cement', 'cement'), ('concrete', 'concrete'), ('marble', 'marble'), ('gold', 'gold'),
         ('bone', 'bone'), ('skull', 'carved skull'), ('vine', 'vines'), ('leaf', 'leaves'), ('leaves', 'leaves')]


def story_rank(level):
    for i, (prefix, desc) in enumerate(STORY):
        if level.startswith(prefix): return i, desc
    return len(STORY), 'the world of Jak 3'


def canvas(w, h):
    """Nombre de repetitions (nx, ny) et format Codex, pour ne jamais etirer le dessin."""
    best = None
    for cw, ch in ((1024, 1024), (1536, 1024), (1024, 1536)):
        for n in range(1, 17):
            nx, ny = (1, n) if w >= h else (n, 1)
            err = abs(math.log((w * nx / (h * ny)) / (cw / ch)))
            if best is None or err < best[0] - 1e-6 or (abs(err - best[0]) < 1e-6 and nx * ny < best[1][0] * best[1][1]):
                best = (err, (nx, ny), (cw, ch))
    return best[1], best[2], best[0]


def main():
    found = {}
    for page in sorted(SRC.iterdir()):
        if not page.is_dir() or not page.name.endswith(KEEP): continue
        level = page.name.rsplit('-', 1)[0]
        for png in page.glob('*.png'):
            name = png.stem
            if name in DONE: continue
            im = Image.open(png); w, h = im.size
            if max(w, h) < 32: continue
            a = np.asarray(im.convert('RGBA'))
            if a[..., 3].min() != a[..., 3].max(): continue                  # decoupe transparente
            if a[..., :3].astype(float).std() < 3: continue                  # aplat uni
            rank, desc = story_rank(level)
            if name not in found or (rank, -w * h) < (found[name]['rank'], -found[name]['w'] * found[name]['h']):
                found[name] = {'name': name, 'level': level, 'rank': rank, 'context': desc, 'w': w, 'h': h,
                               'source': str(png.relative_to(ROOT)), 'levels': []}
            found[name]['levels'].append(level)
    entries = sorted(found.values(), key=lambda e: (e['rank'], e['level'], -e['w'] * e['h'], e['name']))
    if OUT.exists(): shutil.rmtree(OUT / 'envoyer', ignore_errors=True)
    (OUT / 'envoyer').mkdir(parents=True, exist_ok=True); (OUT / 'resultats').mkdir(exist_ok=True)
    manifest = []
    for k, e in enumerate(entries, 1):
        (nx, ny), (cw, ch), err = canvas(e['w'], e['h'])
        tile = Image.open(ROOT / e['source']).convert('RGB')
        big = Image.new('RGB', (e['w'] * nx, e['h'] * ny))
        for i in range(nx):
            for j in range(ny): big.paste(tile, (i * e['w'], j * e['h']))
        big.resize((cw, ch), Image.LANCZOS).save(OUT / 'envoyer' / f"{e['name']}.png")
        words = sorted({v for t, v in HINTS if t in e['name'].lower()})
        material = ', '.join(words) if words else 'scenery surface (identify the material from the image)'
        repeat = '' if nx * ny == 1 else (
            f" IMPORTANT: this image shows the SAME texture tile repeated {nx * ny} times "
            f"({'side by side' if nx > 1 else 'stacked vertically'}, {nx} x {ny}). Keep every repeat IDENTICAL and exactly "
            f"aligned on the same grid, with no border between them: the image will be cut back into one tile.")
        prompt = (f"Remaster this Jak 3 game texture ({material}) from {e['context']} in a hand-painted, stylised art style "
                  f"like Genshin Impact: clean painted shapes, crisp readable detail, rich natural colours, soft painterly "
                  f"shading. Keep EXACTLY the original layout: every shape, seam, rivet, plank, brick or ornament at the same "
                  f"place and the same size, same overall colours. It must tile SEAMLESSLY: left edge continues the right edge, "
                  f"top edge continues the bottom edge. Flat, evenly lit, orthographic texture filling the whole image: "
                  f"no perspective, no cast shadows, no new objects, no text, no border, no frame.{repeat} "
                  f"Output size {cw}x{ch}.")
        manifest.append({'order': k, 'name': e['name'], 'level': e['level'], 'levels': sorted(set(e['levels'])),
                         'source': e['source'], 'source_size': [e['w'], e['h']], 'tiles': [nx, ny],
                         'sent_size': [cw, ch], 'prompt': prompt})
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
    zones = []
    for m in manifest:
        z = story_rank(m['level'])[1]
        if not zones or zones[-1][0] != z: zones.append([z, 0])
        zones[-1][1] += 1
    return manifest, zones


if __name__ == '__main__':
    manifest, zones = main()
    print(len(manifest), 'textures')
    for z, n in zones[:80]: print(f'  {n:4d}  {z}')
