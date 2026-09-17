"""Package ImageGen textures for OpenGOAL. Resizing/alpha conversion only."""
from pathlib import Path
from PIL import Image
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
manifest = json.loads((ROOT / 'texture-manifest.json').read_text(encoding='utf-8'))
originals = ROOT.parents[1] / 'active/jak3/data/decompiler_out/jak3/textures'
destination = ROOT / 'data/custom_assets/jak3/texture_replacements'
masters = ROOT / 'art/masters'
destination.mkdir(parents=True, exist_ok=True)
masters.mkdir(parents=True, exist_ok=True)
report = []
for entry in manifest:
    original_path = originals / entry.get('page', 'wasstada-tfrag') / entry['file']
    original = Image.open(original_path).convert('RGBA')
    master = masters / entry['file']
    if not master.exists():
        shutil.copy2(entry['generated'], master)
    output_size = (original.width * 4, original.height * 4)
    texture = Image.open(master).convert('RGB').resize(output_size, Image.Resampling.LANCZOS)
    alpha = original.getchannel('A').resize(output_size, Image.Resampling.NEAREST)
    texture.putalpha(alpha)
    placements = []
    for page in ('wasstada-tfrag', 'wasstadb-tfrag'):
        candidate = originals / page / entry['file']
        if not candidate.exists():
            continue
        # Only share a replacement when both original copies have identical pixels.
        candidate_image = Image.open(candidate).convert('RGBA')
        if candidate_image.size != original.size or candidate_image.tobytes() != original.tobytes():
            raise ValueError(f'Differing original texture: {candidate}')
        output = destination / page / entry['file']
        output.parent.mkdir(parents=True, exist_ok=True)
        texture.save(output, optimize=True)
        placements.append(str(output.relative_to(destination)))
    report.append({'file': entry['file'], 'original_size': original.size,
                   'replacement_size': output_size, 'alpha_extrema': alpha.getextrema(),
                   'source_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
                   'placements': placements,
                   'replacement_sha256': hashlib.sha256((destination / placements[0]).read_bytes()).hexdigest()})
(ROOT / 'texture-validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
