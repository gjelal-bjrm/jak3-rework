"""Installe les shaders de la meteo (atmosphere, precipitations) dans data/, engine-src/ et les trois
variantes (empreintes), comme les autres shaders du prototype."""
from pathlib import Path
import hashlib, json, shutil
H = Path(__file__).resolve().parent; R = H.parents[1]
REL = 'game/graphics/opengl_renderer/shaders/'


def main():
    files = json.loads((R / 'variant-files.json').read_text(encoding='utf-8'))
    hashes = json.loads((R / 'variant-hashes.json').read_text(encoding='utf-8'))
    for name in ('modern_weather_fog.vert', 'modern_weather_fog.frag', 'modern_weather_particles.vert',
                 'modern_weather_particles.frag'):
        rel = REL + name
        for root in (R / 'data', R / 'engine-src'):
            (root / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(H / name, root / rel)
        for variant in ('original', 'remaster-v1', 'remaster'):
            target = R / 'variants' / variant / rel; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(H / name, target)
            hashes.setdefault(variant, {})[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
        if rel not in files: files.append(rel)
        print('installe :', rel, hashes['remaster'][rel][:12])
    (R / 'variant-files.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
    (R / 'variant-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__': main()
