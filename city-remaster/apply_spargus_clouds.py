"""Install or undo the isolated Spargus cloud source changes; never build/restart/package."""
from pathlib import Path
import argparse,hashlib,json

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
MANIFEST=HERE/'spargus-clouds-manifest.json'
BACKUP=HERE/'sky-source-baseline'
PREFIX='engine-src/game/graphics/opengl_renderer/'
EDITS={
 PREFIX+'DirectRenderer.h':[
  ('#include "game/graphics/opengl_renderer/ocean/ModernOcean.h"',
   '#include "game/graphics/opengl_renderer/ocean/ModernOcean.h"\n#include "game/graphics/opengl_renderer/SpargusClouds.h"'),
  ('  ModernOcean m_modern_ocean;','  ModernOcean m_modern_ocean;\n  SpargusClouds m_spargus_clouds;')],
 PREFIX+'DirectRenderer.cpp':[
  ('  ASSERT(tex);\n\n  glActiveTexture(GL_TEXTURE20 + unit);',
   '  ASSERT(tex);\n\n'
   '  // Only the Jak 3 sky bucket may substitute its native cloud mask.\n'
   '  tex=m_spargus_clouds.replacement(render_state,GLuint(*tex),\n'
   '                                    state.texture_base_ptr,m_name=="sky");\n\n'
   '  glActiveTexture(GL_TEXTURE20 + unit);')]
}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--undo',action='store_true');args=parser.parse_args()
    old=json.loads(MANIFEST.read_text())if MANIFEST.exists()else None
    if args.undo:
        assert old,'No applied manifest'
        for name,record in old['files'].items():
            path=ROOT/name
            assert path.is_file()and sha(path.read_bytes())==record['after_sha256'],name+' changed after apply'
        for name,record in old['files'].items():
            path=ROOT/name
            if record['before_sha256'] is None:path.unlink()
            else:
                raw=(BACKUP/name).read_bytes();assert sha(raw)==record['before_sha256'];path.write_bytes(raw)
        print('Source restoration complete; runtime/package unchanged');return
    staged={}
    for name,edits in EDITS.items():
        raw=(ROOT/name).read_bytes();out=raw
        nl='\r\n'if b'\r\n'in raw else '\n'
        if old:assert sha(raw)==old['files'][name]['after_sha256'],name+' changed since apply'
        for before,after in edits:
            before=before.replace('\n',nl).encode();after=after.replace('\n',nl).encode()
            if out.count(after)==1:continue
            assert out.count(before)==1,(name,'anchor')
            out=out.replace(before,after,1)
        staged[name]=out
    for name in ('SpargusClouds.h','spargus_clouds.vert','spargus_clouds.frag'):
        targets=[PREFIX+name]if name.endswith('.h')else[PREFIX+'shaders/'+name,'data/game/graphics/opengl_renderer/shaders/'+name]
        for target in targets:staged[target]=(HERE/name).read_bytes()
    records={}
    for name,out in staged.items():
        path=ROOT/name
        original=path.read_bytes()if path.exists()else None
        if old:
            assert original is not None and sha(original)==old['files'][name]['after_sha256'],name+' changed since apply'
            before=old['files'][name]['before_sha256']
        else:
            before=sha(original)if original is not None else None
            if original is not None:
                backup=BACKUP/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original)
        records[name]={'before_sha256':before,'after_sha256':sha(out)}
    for name,out in staged.items():(ROOT/name).write_bytes(out)
    MANIFEST.write_text(json.dumps({'scope':'Jak3 SKY procedural clouds; recent WCA/WCB/lwasbbv and Spargus camera bounds',
        'private_resolution':[1024,1024],'native_visual_validation':False,'files':records},indent=2)+'\n')
    print('Applied 7 source/shader files; no build, packaging or restart')


if __name__=='__main__':main()
