from pathlib import Path
from PIL import Image
import json,struct,shutil
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1'
AUDIT=HERE/'native-audit'
(AUDIT/'originals').mkdir(parents=True,exist_ok=True)
(AUDIT/'gpu').mkdir(exist_ok=True)
for entry in json.loads((HERE/'coverage.json').read_text())['assets']:
    image=Image.open(entry['originals'][0]['path']).convert('RGBA')
    (AUDIT/'originals'/(entry['key']+'.rgba')).write_bytes(struct.pack('<II',*image.size)+image.tobytes())
(AUDIT/'mode.txt').write_text('1')
for entry in json.loads((HERE/'palace-batch4-results.json').read_text()):
    dest=HERE/'masters'/(entry['key']+'.png')
    if not dest.exists():shutil.copy2(entry['generated_path'],dest)
print('Audit originals ready; pending masters preserved without integration.')
