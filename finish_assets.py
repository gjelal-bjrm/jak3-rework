from pathlib import Path
import json
ROOT = Path(__file__).resolve().parent
manifest_path = ROOT / 'texture-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
generated = Path('C:/Users/Gjelal/.codex/generated_images/01a0a501-7cc7-7072-9c65-4e16af3cef4d')
extra = [
 ('wstd-floor-panel01.png', 'exec-2557d720-affe-4295-a32a-de3219b5a0cd.png', 'wasstada-tfrag', 'Faithful 2:1 reconstruction of the flat grey-green metal panel; retain the rusty narrow border, UV layout, subdued palette; fine matte grain and patina; no new seams or objects.'),
 ('wstd-scaffold-wall-01.png', 'exec-17974680-10bc-4fc0-acb9-be4744e165ba.png', 'wasstada-tfrag', 'Faithful reconstruction of the brown-olive softly corrugated metal sheet; retain exact vertical repeat rhythm and color; refine painted weathering; no new objects, seams or rivets.'),
 ('wstd-scaffold-wall-02.png', 'exec-2a3817fe-4126-4928-867f-b753c76ba8fa.png', 'wasstada-tfrag', 'Faithful reconstruction of the square grey metal panel; preserve rusty border geometry and existing edge fasteners; restrained painted grain, scratches and patina; flat diffuse illumination.'),
 ('wstd-scaffold-floor-01.png', 'exec-55805e8a-6c4a-43fb-99ea-270a0dd1e0a1.png', 'wasstadb-tfrag', 'Faithful reconstruction of the diagonal interlocking grey-green tread pattern; preserve pattern layout, scale, subdued original palette; refine metal edges and sandy deposits; flat texture, neutral light, no new objects.')]
for name, file, page, prompt in extra:
    if not any(x['file'] == name for x in manifest):
        manifest.append({'file': name, 'label': name[:-4], 'page': page, 'generated': str(generated / file),
                         'prompt_summary': prompt, 'tool': 'built-in ImageGen'})
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
inputs = ROOT / 'data/decompiler/config/jak3/ntsc_v1/inputs.jsonc'
text = inputs.read_text(encoding='utf-8')
text = text.replace('"levels_to_extract": ["WASSTADA.DGO"]', '"levels_to_extract": ["WASSTADA.DGO", "WASSTADB.DGO"]')
inputs.write_text(text, encoding='utf-8')
print(f'{len(manifest)} unique remaster textures ready for integration')
