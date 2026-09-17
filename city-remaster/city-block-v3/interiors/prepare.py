"""Reproducible rooms/characters conversion and strict renderer insertion."""
from pathlib import Path
import argparse,hashlib,json,shutil,struct
from PIL import Image
from room_config import rooms_for
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ASSETS='custom_assets/jak3/city-interiors'
RENDER='engine-src/game/graphics/opengl_renderer/'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def active_windows():
 revision=HERE.parent/'architecture/revision-004/installed.json'
 if not revision.exists():revision=HERE.parent/'architecture/revision-003/installed.json'
 if revision.exists():
  record=json.loads(revision.read_text())
  anchors=Path(record['window_anchors'])
  assert sha(anchors)==record['window_anchors_sha256'],'Window revision changed after installation'
  return json.loads(anchors.read_text())
 return json.loads((HERE.parent/'architecture/window-anchors.json').read_text())
def edits():
 return {
  RENDER+'OpenGLRenderer.h':[
   ('#include "game/graphics/opengl_renderer/PalaceFire.h"\n','#include "game/graphics/opengl_renderer/PalaceFire.h"\n#include "game/graphics/opengl_renderer/CityInteriors.h"\n'),
   ('  PalaceFire m_palace_fire;\n','  CityInteriors m_city_interiors;\n  PalaceFire m_palace_fire;\n')],
  RENDER+'OpenGLRenderer.cpp':[
   ('      m_palace_fire.render(&m_render_state);','      m_city_interiors.render(&m_render_state);\n      m_palace_fire.render(&m_render_state);')]
 }
def inverse(source,relative):
 for old,new in reversed(edits()[relative]):
  assert source.count(new)==1,(relative,'missing/ambiguous interior hook')
  source=source.replace(new,old,1)
 return source
def source_before(relative):
 record=json.loads((HERE/'source-manifest.json').read_text())['files'][relative]
 before=Path(record['before_path'])
 assert sha(before)==record['before_sha256']
 assert inverse((ROOT/relative).read_text(encoding='utf-8-sig'),relative)==before.read_text(encoding='utf-8-sig')
 return before
def main():
 dest=ROOT/'data'/ASSETS;dest.mkdir(parents=True,exist_ok=True)
 for name in ('lounge','conversation','sitting-male','conversing-male','conversing-female'):
  origin=HERE if name in ('lounge','conversation')else HERE.parent/'inhabitants'
  meta=json.loads((origin/(name+'.json')).read_text())
  shutil.copy2(origin/meta['binary'],dest/meta['binary'])
  for draw in meta['draws']:
   if 'texture'in draw:
    png=origin/draw['texture'];out=dest/Path(draw['texture']).with_suffix('.rgba');out.parent.mkdir(parents=True,exist_ok=True)
    image=Image.open(png).convert('RGBA');out.write_bytes(struct.pack('<II',*image.size)+image.tobytes())
    draw['texture']=out.relative_to(dest).as_posix()
  (dest/(name+'.json')).write_text(json.dumps(meta,indent=2))
 for source,name in [('wood-hd-v2.png','wood'),('market-cotton-hd.png','fabric')]:
  image=Image.open(HERE.parents[1]/source).convert('RGBA');(dest/(name+'.rgba')).write_bytes(struct.pack('<II',*image.size)+image.tobytes())
 windows=active_windows()
 for ext in ('.bin','.json'):shutil.copy2(HERE/'shared-room-v2'/('corner-conversation'+ext),dest/('corner-conversation'+ext))
 (dest/'runtime.json').write_text(json.dumps({'schema':'city-physical-rooms-v2','windows':windows,'rooms':rooms_for(windows),'scope':'Spargus authored apertures; shared physical rooms; visual interiors only'},indent=2))
 record_path=HERE/'source-manifest.json';record=json.loads(record_path.read_text())if record_path.exists()else{'files':{}}
 for relative,changes in edits().items():
  path=ROOT/relative
  if relative in record['files']:source_before(relative);continue
  raw=path.read_bytes();text=raw.decode('utf-8-sig').replace('\r\n','\n');new=text
  for old,replacement in changes:
   assert new.count(old)==1,(relative,old)
   new=new.replace(old,replacement,1)
  assert inverse(new,relative)==text
  before=HERE/'before'/relative;before.parent.mkdir(parents=True,exist_ok=True);assert not before.exists();before.write_bytes(raw)
  path.write_bytes(new.replace('\n','\r\n'if b'\r\n'in raw else'\n').encode())
  record['files'][relative]={'before_path':str(before),'before_sha256':sha(before),'after_sha256':sha(path)}
 newfiles={RENDER+'CityInteriors.h':HERE/'CityInteriors.h'}
 for name in ('city_interior.vert','city_interior.frag'):
  for tree in ('engine-src','data'):newfiles[tree+'/game/graphics/opengl_renderer/shaders/'+name]=HERE/name
 for relative,source in newfiles.items():shutil.copy2(source,ROOT/relative)
 record['new_files']={k:sha(v)for k,v in newfiles.items()};record_path.write_text(json.dumps(record,indent=2))
 files=json.loads((ROOT/'variant-files.json').read_text());hashes=json.loads((ROOT/'variant-hashes.json').read_text())
 relatives=[p.relative_to(ROOT/'data').as_posix()for p in dest.rglob('*')if p.is_file()]+['game/graphics/opengl_renderer/shaders/'+n for n in ('city_interior.vert','city_interior.frag')]
 for relative in relatives:
  if relative not in files:files.append(relative)
  for variant in ('original','remaster-v1'):
   p=ROOT/'variants'/variant/relative
   if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/'data'/relative,p)
   hashes[variant][relative]=sha(p)
 (ROOT/'variant-files.json').write_text(json.dumps(files,indent=2));(ROOT/'variant-hashes.json').write_text(json.dumps(hashes,indent=2))
 (HERE/'asset-manifest.json').write_text(json.dumps({'assets':{r:sha(ROOT/'data'/r)for r in relatives},'actors':'original Spargus GLBs, posed in Blender','geometry':'furnished room meshes; window anchors authored in building mesh'},indent=2))
 print('Prepared room assets and strict renderer hooks:',len(relatives),'files')
if __name__=='__main__':main()
