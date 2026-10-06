"""Apercu agrandi de quelques textures (original | Codex prepare) : qa/codex-zoom.png
  python textures-remaster/zoom.py nom1 nom2 ..."""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
man = {e['name']: e for e in json.loads((HERE / 'codex/manifest.json').read_text(encoding='utf-8'))}
names = sys.argv[1:]; box = 300
sheet = Image.new('RGB', (2 * box + 30, len(names) * (box + 20)), (24, 24, 24)); d = ImageDraw.Draw(sheet)
for i, n in enumerate(names):
    for c, path in enumerate((ROOT / man[n]['source'], HERE / 'out' / f'{n}.png')):
        img = Image.open(path).convert('RGBA'); a = np.asarray(img).copy()
        if c == 0: a[..., 3] = np.minimum(255, a[..., 3].astype(int) * 2)
        img = Image.alpha_composite(Image.new('RGBA', img.size, (255, 0, 255, 255)), Image.fromarray(a)).convert('RGB')
        k = box / max(img.size); img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.NEAREST if c == 0 else Image.LANCZOS)
        sheet.paste(img, (c * (box + 20) + 5, i * (box + 20) + 2))
    d.text((5, i * (box + 20) + box + 4), n, fill=(255, 220, 80))
sheet.save(ROOT / 'qa/codex-zoom.png')
