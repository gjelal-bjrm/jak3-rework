"""Planche-contact des rafales de captures : python sheet.py <sortie.png> <prefixe1> [<prefixe2> ...]

Chaque prefixe (ex. qa/burst-coast, qa/burst-coast-1) devient une colonne ; ses captures NN.png les lignes.
Largeur d'une vignette : 640 px (option --width N).
"""
from pathlib import Path
from PIL import Image, ImageDraw
import glob, sys


def main(argv):
    width = 640
    if '--width' in argv:
        i = argv.index('--width'); width = int(argv[i + 1]); del argv[i:i + 2]
    out, prefixes = argv[0], argv[1:]
    columns = [sorted(glob.glob(f'{p}-[0-9][0-9].png')) for p in prefixes]
    height = width * 9 // 16; rows = max(len(c) for c in columns)
    sheet = Image.new('RGB', (width * len(columns), height * rows), (20, 20, 20)); draw = ImageDraw.Draw(sheet)
    for c, files in enumerate(columns):
        for r, f in enumerate(files):
            sheet.paste(Image.open(f).resize((width, height), Image.LANCZOS), (c * width, r * height))
            draw.text((c * width + 6, r * height + 6), Path(f).name, fill=(255, 255, 0))
    sheet.save(out); print(out, sheet.size, [len(c) for c in columns])


if __name__ == '__main__': main(sys.argv[1:])
