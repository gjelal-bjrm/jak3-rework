"""Kit ChatGPT pour les matieres HD de l'arene de Spargus (etape 1 du remaster de l'arene).

Produit arena-remaster/chatgpt/ (hors Git : contient des textures du jeu) :
  - envoyer/<nom>.png   : texture d'origine agrandie au format accepte par ChatGPT (1024x1024 ou 1536x1024),
                          etiree si besoin (elle sera recompressee a son format d'origine a l'integration) ;
  - resultats/          : dossier ou deposer les images generees, sous le MEME nom (<nom>.png) ;
  - KIT.html            : page a ouvrir : pour chaque texture, l'image a envoyer, le texte a copier et le nom
                          du fichier a enregistrer, par ordre de priorite.
"""
from pathlib import Path
import html, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'arena-remaster/chatgpt'
SRC = ROOT / 'data/decompiler_out/jak3/textures'
LEVELS = ['wasstada-tfrag', 'wasstadb-tfrag', 'wasstadc-tfrag', 'wasstada-shrub']

# nom -> (priorite, description de la matiere)
MATERIALS = {
    # ---- Priorite 1 : grandes surfaces vues partout dans l'arene
    'wstd-rockwall-01': (1, 'weathered orange-red desert sandstone cliff, vertical eroded rock strata and fractured blocks'),
    'wstd-small-rockwall-01': (1, 'orange sandstone rock face, smooth wind-eroded bulges with fine cracks and grainy mineral surface'),
    'wstd-interior-rock01': (1, 'reddish-brown cave rock wall, layered sediment and rough chipped stone'),
    'common_sandstone_ground01': (1, 'pale sandy sandstone ground, compacted sand with fine grit and faint scratches'),
    'wstd-floor-panel01': (1, 'riveted grey-green steel floor plate, worn scratched metal with rust stains and grime in the edges'),
    'wstd-floor-panel02': (1, 'riveted steel floor plates with a seam across, worn grey metal, rust stains and dirt'),
    'wstd-floor-panel03': (1, 'blue-grey painted steel floor plate, chipped paint, scratches and rust spots'),
    'wstd-platform-floor': (1, 'heavy perforated steel grating plate with round holes in a grid and a raised bevelled rim, worn gunmetal'),
    'wstd-platform-wall': (1, 'patched sheet-metal wall made of overlapping riveted olive-green steel panels, dents and grime'),
    'wstd-platform-base': (1, 'dark rusted metal base band with vertical ribs, heavy wear and soot'),
    'wstd-scaffold-wall-01': (1, 'corrugated sheet metal wall, vertical ridges, olive-brown oxidised steel with rust streaks'),
    'wstd-scaffold-wall-02': (1, 'large riveted rusty steel plate, mottled grey and brown oxidation, dents'),
    'wstd-scaffold-wall-03': (1, 'rusted brown steel plate with riveted border, streaks of oxidation'),
    'wstd-scaffold-floor-01': (1, 'diamond-pattern metal lattice floor plate, weathered green-grey steel'),
    'wstd-stands-shell': (1, 'large rusty brown riveted metal plate from arena stands, weathered and stained'),
    'wstd-stands-shell01': (1, 'blue-grey riveted steel panel from arena stands, worn paint and rust spots'),
    'wstd-stands-shell02': (1, 'olive-green painted steel panel, faded and scratched, grime'),
    'wstd-stands-seats01': (1, 'worn pale stone bench seat surface, polished by use, small chips and dust'),
    'wstd-stands-seats02': (1, 'dark metal bench edge band, black steel with worn highlights'),
    'wstd-stands-plate01': (1, 'patchwork of blue-grey and olive riveted steel plates on arena stands, worn paint'),
    'wstd-stands-plate02': (1, 'patchwork of riveted steel plates, blue-grey and brown, scratched and rusty'),
    'wstd-stands-plate03': (1, 'patchwork of riveted steel plates, grey-blue with olive patches'),
    'wstd-stands-plate04': (1, 'blue steel wall with brown rusty patch plates riveted on top'),
    'wstd-stands-plate05': (1, 'blue steel wall with rusty brown square patch plates'),
    'wstd-stands-ceiling': (1, 'dark red-brown metal ceiling panel with heavy riveted frame and diagonal braces'),
    'wstd-torchbowl-01': (1, 'large blue-green bronze brazier bowl metal, riveted bands, verdigris patina'),
    # ---- Priorite 2 : surfaces moyennes
    'common_sandstone_taper01': (2, 'carved sandstone with swirling engraved ornament, sand-worn edges'),
    'common_sandstone_trim01': (2, 'sandstone trim moulding band, sand-worn'),
    'wstd-scaffold-plate-01': (2, 'olive-grey weathered steel plate with a horizontal seam'),
    'wstd-scaffold-wall-edge': (2, 'rusty metal edge band with riveted border'),
    'wstd-scaffold-bar': (2, 'weathered steel bar, worn metal and rust'),
    'wstd-scaffold-strut': (2, 'dark rusted steel strut beam'),
    'wstd-scaffold-teeth': (2, 'rusty metal band with rough saw-tooth edge'),
    'wstd-stands-ceilingplate': (2, 'dark corrugated metal ceiling plate'),
    'wstd-stands-lowall01': (2, 'low wall band of rusty riveted plates'),
    'wstd-stands-plateedge': (2, 'blue steel edge trim with rivets'),
    'wstd-stands-rib': (2, 'dark blue metal structural rib'),
    'wstd-stands-stairs01': (2, 'worn steel stair edge band'),
    'wstd-stands-stairs02': (2, 'dark steel stair riser band'),
    'wstd-mount-post': (2, 'dark corrugated metal post'),
    'wstd-spike-01': (2, 'pale bone-yellow carved spike plates with ornamental curves, weathered'),
    'wstd-torchbowl-02': (2, 'bronze brazier rim band with verdigris patina'),
    'wstd-ladder': (2, 'weathered wooden ladder planks, sun-bleached grey wood'),
    'wstd-flag': (2, 'red and orange war banner fabric with a flame motif, coarse woven cloth, frayed'),
    # ---- Priorite 3 : zone de combat et trone
    'wstd-fight-plat-box-end': (3, 'olive-green metal box panel with two tall arched window slots and ribbed dark grilles'),
    'wstd-fight-plat-box-side': (3, 'olive-green riveted metal box side panel, worn'),
    'wstd-fight-plat-box-top': (3, 'worn wooden plank top with a zigzag metal inlay strip'),
    'wstd-fight-plat-door': (3, 'patchwork olive-green metal door made of overlapping plates'),
    'wstd-fight-plat-floor-01': (3, 'patchwork of riveted olive steel floor plates'),
    'wstd-fight-plat-floor-02': (3, 'patchwork of olive steel floor plates with a corrugated band at the bottom'),
    'wstd-fight-plat-floor-03': (3, 'olive-grey steel floor plate with a dark diamond grate strip'),
    'wstd-fight-plat-lrg-floor-01': (3, 'large patchwork of riveted dark green steel plates with a raised frame'),
    'wstd-fight-plat-lrg-floor-02': (3, 'patchwork of dark green steel plates with a glowing cyan square light socket'),
    'wstd-fight-plat-lrg-floor-03': (3, 'patchwork of dark green steel plates with a glowing cyan square light socket'),
    'wstd-fight-plat-lrg-floor-04': (3, 'patchwork of dark green steel plates with a glowing cyan square light socket'),
    'wstd-fight-plat-lrg-floor-05': (3, 'patchwork of dark green steel plates with a glowing cyan square light socket'),
    'wstd-fight-plat-tube': (3, 'grey ribbed metal pipe'),
    'wstd-fight-plat-wall-01': (3, 'olive metal wall of overlapping plates with dark gaps'),
    'wstd-fight-plat-wall-02': (3, 'olive riveted metal wall plates'),
    'wstd-fight-plat-wall-03': (3, 'dark metal wall band with diagonal grille'),
    'wstd-tentacle-barrel': (3, 'dark olive metal barrel with riveted bands and a curved hatch'),
    'wstd-tentacle-plate01': (3, 'blue-grey rough metal plate, weathered'),
    'wstd-tentacle-plate02': (3, 'rusty brown metal plate, weathered'),
    'wstd-tentacle-plate03': (3, 'rusty square metal plate with corner rivets'),
    'wstd-throne-arch01': (3, 'blue steel arch band with a brass stripe'),
    'wstd-throne-arch02': (3, 'dark olive metal arch band'),
    'wstd-throne-chair01': (3, 'blue steel throne backrest with a gold-brass inverted chevron emblem'),
    'wstd-throne-floor01': (3, 'hexagonal stone floor tiles, grey-brown, worn edges'),
    'wstd-throne-floor02': (3, 'hexagonal stone tiles with a metal pipe channel and ribbed metal floor'),
    'wstd-throne-plat02': (3, 'blue steel trim band with rivets'),
    'wstd-throne-plat03': (3, 'blue steel wall with a brass top band and riveted lower band'),
    'wstd-throne-table-big': (3, 'blue-grey steel table top with engraved wave lines'),
    'wstd-throne-wall01': (3, 'dark blue riveted steel wall plate with rust spots'),
    'wstd-throne-wall02': (3, 'dark weathered wood planks, grain and knots'),
    'wstd-rock-shrubs': (3, 'orange desert rock with grainy lichen'),
    'wstd-torchbowl-coal-01': (3, 'glowing hot coals, yellow-orange embers with black charred pieces'),
}

PROMPT = ('Edit the attached Jak 3 game texture into a faithful high-resolution remaster texture: {mat}. '
          'Preserve EXACTLY the original layout, shapes, positions of every element, colours (hue), average brightness '
          'and contrast, and the tiling at the edges. Add much finer, realistic material detail visible at normal game '
          'distance (surface grain, wear, scratches, dirt), keeping the slightly stylised hand-painted Jak 3 art direction. '
          'Flat, evenly lit, orthographic texture filling the whole image: no perspective, no shadows cast by a light, '
          'no new objects, no text, no border. Output size {size}.')


CODEX = '''# Mission : textures HD de l'arène de Spargus (remaster Jak 3)

Tu dois générer {total} textures haute définition, une par une, avec ton outil de génération / retouche d'images.

## Où sont les fichiers

- Dossier de travail : `{dir}`
- `manifest.json` : la liste des textures, dans l'ordre de priorité. Pour chaque entrée :
  - `name` : le nom de la texture ;
  - `sent_size` : la taille exacte de l'image à produire (largeur, hauteur) ;
  - `prompt` : la consigne de retouche à appliquer.
- `envoyer/<name>.png` : l'image d'origine à retoucher (texture du jeu agrandie).
- `resultats/` : le dossier où enregistrer chaque résultat.

## Ce que tu dois faire, pour chaque entrée de `manifest.json`, dans l'ordre

1. Si `resultats/<name>.png` existe déjà, passe à la suivante (reprise possible après une interruption).
2. Utilise `envoyer/<name>.png` comme image de départ (retouche de l'image, pas une création à partir de rien).
3. Applique exactement la consigne `prompt` de l'entrée.
4. Produis une image de la taille `sent_size` (1024x1024, 1536x1024 ou 1024x1536).
5. Enregistre le résultat en PNG sous `resultats/<name>.png`, avec exactement le même nom que l'image de départ.
6. Ajoute une ligne dans `resultats/journal.txt` : `<name> : ok` ou `<name> : échec (raison)`.

## Règles importantes

- Ne modifie, ne renomme et ne supprime aucun fichier de `envoyer/` ni `manifest.json`.
- Une seule image par texture ; ne crée pas de variantes numérotées.
- Le résultat doit rester fidèle à l'original : même disposition, mêmes formes aux mêmes endroits, mêmes couleurs et même luminosité moyenne. Seul le niveau de détail augmente.
- Pas de texte, de bordure, de perspective ni d'ombre portée dans l'image.
- Si une génération échoue ou s'éloigne clairement de l'original (couleurs changées, motif différent), recommence une fois, puis passe à la suivante en le notant dans le journal.
- Ne touche à aucun autre dossier du projet.

Quand tout est fini, affiche le nombre de textures réussies et la liste des échecs.
'''


def main():
    (OUT / 'envoyer').mkdir(parents=True, exist_ok=True)
    (OUT / 'resultats').mkdir(parents=True, exist_ok=True)
    index = {}
    for level in LEVELS:
        for f in (SRC / level).glob('*.png'):
            index.setdefault(f.stem, f)
    rows, manifest = [], []
    for name, (prio, mat) in sorted(MATERIALS.items(), key=lambda kv: (kv[1][0], kv[0])):
        src = index[name]
        im = Image.open(src).convert('RGB')
        w, h = im.size
        size = (1024, 1024) if w == h else ((1536, 1024) if w > h else (1024, 1536))
        im.resize(size, Image.LANCZOS).save(OUT / 'envoyer' / f'{name}.png')
        prompt = PROMPT.format(mat=mat, size=f'{size[0]}x{size[1]}')
        manifest.append({'name': name, 'priority': prio, 'source_size': [w, h], 'sent_size': list(size),
                         'source': str(src.relative_to(ROOT)), 'prompt': prompt})
        rows.append((prio, name, prompt, w, h))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    cards = []
    labels = {1: 'Priorité 1 — grandes surfaces (à faire en premier)', 2: 'Priorité 2 — surfaces moyennes',
              3: 'Priorité 3 — zone de combat et trône'}
    current = None
    for prio, name, prompt, w, h in rows:
        if prio != current:
            cards.append(f'<h2>{labels[prio]}</h2>'); current = prio
        cards.append(f'''<div class="card" id="{name}">
  <img src="envoyer/{name}.png" alt="{name}">
  <div class="body">
    <div class="name">{name}.png <span class="size">(origine {w}×{h})</span> <span class="state" data-name="{name}"></span></div>
    <textarea readonly>{html.escape(prompt)}</textarea>
    <button onclick="copyPrompt(this)">Copier le texte</button>
  </div>
</div>''')
    page = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Arène — textures ChatGPT</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#1e1f22;color:#e8e6e3;margin:0;padding:20px 28px;max-width:1100px}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:34px;border-bottom:1px solid #444;padding-bottom:6px}}
ol li{{margin:4px 0}} .card{{display:flex;gap:16px;background:#2a2c30;border-radius:8px;padding:12px;margin:12px 0}}
.card img{{width:220px;height:auto;image-rendering:auto;border-radius:4px;flex:none;object-fit:contain;background:#111}}
.body{{flex:1;display:flex;flex-direction:column;gap:8px}} .name{{font-weight:600;font-size:15px}} .size{{color:#999;font-weight:400}}
textarea{{width:100%;height:110px;background:#1b1c1f;color:#ddd;border:1px solid #444;border-radius:4px;font-size:12px;padding:6px;box-sizing:border-box}}
button{{align-self:flex-start;background:#3d6fd9;color:white;border:0;border-radius:4px;padding:6px 14px;cursor:pointer;font-size:13px}}
button.ok{{background:#2f8f4e}} code{{background:#333;padding:1px 5px;border-radius:3px}}
</style></head><body>
<h1>Textures HD de l'arène avec ChatGPT</h1>
<p>Pour chaque texture ci-dessous :</p>
<ol>
<li>Dans ChatGPT, ouvre une nouvelle conversation et joins l'image (glisse-la depuis cette page, ou prends-la dans le dossier <code>envoyer</code>).</li>
<li>Clique sur « Copier le texte », colle-le dans ChatGPT et envoie.</li>
<li>Télécharge l'image générée et enregistre-la dans le dossier <code>resultats</code>, avec <b>exactement le même nom</b> (par exemple <code>wstd-rockwall-01.png</code>).</li>
</ol>
<p>Commence par la priorité 1. Si une image ne te plaît pas (couleurs changées, motif différent), redemande à ChatGPT ou passe-la : je vérifierai chaque résultat avant de l'intégrer. Dis-moi quand un lot est prêt.</p>
{''.join(cards)}
<script>
function copyPrompt(b){{const t=b.parentElement.querySelector('textarea');navigator.clipboard.writeText(t.value).then(()=>{{b.textContent='Copié ✓';b.classList.add('ok');setTimeout(()=>{{b.textContent='Copier le texte';b.classList.remove('ok')}},1500)}})}}
</script></body></html>'''
    (OUT / 'KIT.html').write_text(page, encoding='utf-8')
    (OUT / 'INSTRUCTIONS-CODEX.md').write_text(CODEX.format(dir=OUT, total=len(rows)), encoding='utf-8')
    counts = {p: sum(1 for r in rows if r[0] == p) for p in (1, 2, 3)}
    print(f'kit : {len(rows)} textures (priorite 1 : {counts[1]}, 2 : {counts[2]}, 3 : {counts[3]}) -> {OUT}')


if __name__ == '__main__':
    main()
