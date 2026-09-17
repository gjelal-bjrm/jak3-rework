"""Coverage ledger for the entire palace environment and its mechanical props."""
from pathlib import Path
from PIL import Image
import json,struct,hashlib
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'terrain-v1'
ORIGINAL=ROOT.parents[1]/'active/jak3/data/decompiler_out/jak3'
raw=(ORIGINAL/'levels/waspala/waspala-background.glb').read_bytes()
length=struct.unpack_from('<I',raw,12)[0];scene=json.loads(raw[20:20+length])
usage={}
for mesh in scene['meshes']:
 for primitive in mesh['primitives']:
  name=scene['materials'][primitive['material']].get('name','')
  usage[name]=usage.get(name,0)+scene['accessors'][primitive['indices']]['count']//3
integrated={entry['key']:entry for entry in json.loads((HERE/'texture-validation.json').read_text())}
assets={}
for page in ('waspala-tfrag','waspala-alpha','waspala-shrub','waspala-pris'):
 for path in sorted((ORIGINAL/'textures'/page).glob('*.png')):
  if page=='waspala-pris' and not path.stem.startswith('waspala-'):continue
  entry=assets.setdefault(path.stem,{'key':path.stem,'originals':[],
      'background_triangles':usage.get(path.stem,0)})
  im=Image.open(path).convert('RGBA')
  entry['originals'].append({'page':page,'path':str(path),'size':im.size,'alpha_range':im.getchannel('A').getextrema()})
  if path.stem=='common-black':entry['status']='preserved utility constant (not a surface texture)'
  elif path.stem in integrated:entry['status']='replacement packaged for extraction'
  else:entry['status']='remaining'
report={'scope':'King room first: all environment surfaces, glass, vegetation, throne and mechanical props. Water and fire effects are tracked separately.',
        'assets':list(assets.values()),'total_surface_textures':len(assets)-1,
        'integrated_surface_textures':sum(x['status']=='replacement packaged for extraction' for x in assets.values()),
        'remaining':[x['key'] for x in assets.values() if x['status']=='remaining']}
(HERE/'coverage.json').write_text(json.dumps(report,indent=2))
print(f'Palace coverage: {report["integrated_surface_textures"]}/{report["total_surface_textures"]} textures integrated')
