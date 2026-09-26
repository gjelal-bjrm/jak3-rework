"""Controle de tous les feux fixes : une capture par foyer (camera libre), planche qa/fires-<scene>.png.

  python qa_fires.py arena     (18 braseros de l'arene)
  python qa_fires.py palace    (24 vasques du palais)
Le jeu doit etre ouvert sur la scene (lanceur ou launch.py). Chaque foyer est vu de face, depuis le cote du
centre du lieu, un peu au-dessus des braises : c'est la que les defauts se voient (feu cache, coupe, deborde).
"""
from pathlib import Path
import json, math, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def arena():
    out = []
    for x, y, z, R, rim, bowl in json.load(open(ROOT / 'arena-remaster/objects/brazier-coals.json')):
        out.append((x, y, z, max(bowl, 1.)))
    return out, (2320., -470.)


def palace():
    text = (ROOT / 'engine-src/game/graphics/opengl_renderer/PalaceFireSources.inc').read_text()
    rows = re.findall(r'\{([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),', text.replace(' ', ''))
    return [(float(a), float(b), float(c), float(d) * 2.5) for a, b, c, d in rows], (2000., -460.)


def main(scene):
    sources, centre = {'arena': arena, 'palace': palace}[scene]()
    names = []
    for i, (x, y, z, size) in enumerate(sources):
        dx, dz = centre[0] - x, centre[1] - z; L = math.hypot(dx, dz) or 1.
        d = 4. + size * 2.6
        eye = f'{x + dx / L * d:.2f},{y + size * .55:.2f},{z + dz / L * d:.2f}'
        target = f'{x:.2f},{y + size * .35:.2f},{z:.2f}'
        name = f'fire-{scene}-{i:02d}'
        subprocess.run([sys.executable, str(ROOT / 'qa_live.py'), scene, name, '--freecam', f'{eye}/{target}',
                        '--keep-freecam', '--wait', '0.5'], capture_output=True)
        names.append(name)
    subprocess.run([sys.executable, str(ROOT / 'qa_live.py'), scene, 'fire-reset', '--eval',
                    "(remove-setting-by-arg0 *setting-control* 'mode-name)", '--wait', '0.3'], capture_output=True)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 18)
    W, H, cols = 480, 270, 4
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * W, rows * H), (20, 20, 20)); draw = ImageDraw.Draw(sheet)
    for k, n in enumerate(names):
        shot = ROOT / 'qa' / f'live-{n}-00.png'
        if not shot.exists(): continue
        sheet.paste(Image.open(shot).convert('RGB').resize((W, H)), ((k % cols) * W, (k // cols) * H))
        draw.text(((k % cols) * W + 6, (k // cols) * H + 4), f'{scene} {k:02d}', fill=(255, 255, 0), font=font)
    out = ROOT / 'qa' / f'fires-{scene}.png'
    sheet.save(out); print(out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'arena')
