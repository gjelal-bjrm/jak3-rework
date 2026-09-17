from pathlib import Path
from PIL import Image,ImageChops
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1'
report=[]
for entry in json.loads((HERE/'texture-validation.json').read_text()):
    path=HERE/'native-audit/gpu'/(entry['key']+'.png')
    if not path.exists():continue
    gpu=Image.open(path).convert('RGBA')
    expected=Image.open(ROOT/'data/custom_assets/jak3/texture_replacements'/entry['placements'][0]['path']).convert('RGBA')
    same=gpu.size==expected.size and gpu.tobytes()==expected.tobytes()
    report.append({'key':entry['key'],'gpu_size':gpu.size,'matches_replacement_pixels':same,
      'gpu_pixel_sha256':hashlib.sha256(gpu.tobytes()).hexdigest(),
      'expected_pixel_sha256':hashlib.sha256(expected.tobytes()).hexdigest()})
(HERE/'native-audit/gpu-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
assert report and all(x['matches_replacement_pixels'] for x in report)
