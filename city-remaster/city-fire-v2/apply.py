"""Strict source-only insertion, no build, registration, deploy or game control."""
from pathlib import Path
import argparse,hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
KERNEL='engine-src/game/kernel/jak3/kmachine.cpp'
PALACE='engine-src/game/graphics/opengl_renderer/PalaceFire.h'
GOAL='goal_src/jak3/engine/common-obs/generic-obs.gc'
def read(p):return Path(p).read_text(encoding='utf-8-sig')
def sha(b):return hashlib.sha256(b).hexdigest()
def edits():
    hook=read(HERE/'hook.gc')
    goal=[
      ('(defmethod deactivate ((this part-spawner))\n',hook+'\n(defmethod deactivate ((this part-spawner))\n'),
      ('(defmethod deactivate ((this part-spawner))\n  "Make a process dead, clean it up, remove it from the active pool, and return to dead pool."\n',
       '(defmethod deactivate ((this part-spawner))\n  "Make a process dead, clean it up, remove it from the active pool, and return to dead pool."\n  (pc-remaster-spawner-fire this 0)\n'),
      ('       (set! (-> self enable) #f)\n       #t\n',
       '       (set! (-> self enable) #f)\n       (pc-remaster-spawner-fire self 0)\n       #t\n'),
      ('      (spawn (-> self part) (-> self root trans))\n',
       '      (if (zero? (pc-remaster-spawner-fire self 1))\n          (spawn (-> self part) (-> self root trans))\n          )\n')]
    return {
      **{tree+'/'+GOAL:goal for tree in ('engine-src','data')},
      KERNEL:[
       ('#include "game/graphics/opengl_renderer/WaterContacts.h"\n',
        '#include "game/graphics/opengl_renderer/WaterContacts.h"\n#include "game/graphics/opengl_renderer/CityFireSources.h"\n'),
       ('static u64 prototype_water_contact(u32 packet) {\n',
        'static u64 prototype_city_fire(u32 region, u32 aid, u32 position, u32 quaternion, u32 active) {\n'
        '  return CityFireSources::publish(static_cast<int>(region), aid, Ptr<float>(position).c(),\n'
        '                                  Ptr<float>(quaternion).c(), static_cast<int>(active));\n}\n\n'
        'static u64 prototype_water_contact(u32 packet) {\n'),
       ('void InitMachine_PCPort() {\n',
        'void InitMachine_PCPort() {\n  CityFireSources::reset();\n'
        '  make_function_symbol_from_c("pc-remaster-city-fire", (void*)prototype_city_fire);\n')],
      PALACE:[
       ('#include "game/graphics/opengl_renderer/background/LiquidSnapshot.h"\n',
        '#include "game/graphics/opengl_renderer/background/LiquidSnapshot.h"\n#include "game/graphics/opengl_renderer/CityFire.h"\n'),
       ('  void render(SharedRenderState* state) {\n',
        '  void render(SharedRenderState* state) {\n    m_city_fire.render(state);\n'),
       ('  std::unique_ptr<Shader> m_volume,m_light,m_embers;\n',
        '  CityFire m_city_fire;\n  std::unique_ptr<Shader> m_volume,m_light,m_embers;\n')]}
def inverse(source,relative):
    for old,new in reversed(edits()[relative]):
      assert source.count(new)==1,'City fire insertion changed: '+relative
      source=source.replace(new,old,1)
    return source
def source_before(relative):
    record=json.loads(read(HERE/'manifest.json'))['files'][relative]
    current=read(ROOT/relative);before=Path(record['before_path'])
    # Other features may add disjoint source blocks after this insertion. Callers
    # that need its exact hash must peel their own insertion before this layer.
    assert inverse(current,relative)==read(before),'Unexpected downstream edit: '+relative
    assert sha(before.read_bytes())==record['before_sha256']
    return before
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    existing=json.loads(read(HERE/'manifest.json'))if(HERE/'manifest.json').exists()else None
    entries={};outputs={}
    for relative,changes in edits().items():
      path=ROOT/relative;raw=path.read_bytes();source=read(path);updated=source
      if existing:
        entry=existing['files'][relative];assert inverse(source,relative)==read(entry['before_path'])
        entries[relative]=entry;continue
      for old,new in changes:
        assert updated.count(old)==1,(relative,'ambiguous anchor',old)
        updated=updated.replace(old,new,1)
      assert inverse(updated,relative)==source
      newline='\r\n'if b'\r\n'in raw else'\n';newraw=updated.replace('\n',newline).encode()
      before=HERE/'before'/relative
      entries[relative]={'before_path':str(before),'before_sha256':sha(raw),'after_sha256':sha(newraw)}
      if args.apply:
        before.parent.mkdir(parents=True,exist_ok=True);assert not before.exists();before.write_bytes(raw)
      outputs[path]=newraw
    new_files={}
    for name in ('CityFire.h','CityFireSources.h','CityFireAttachments.inc'):
      new_files['engine-src/game/graphics/opengl_renderer/'+name]=HERE/name
    for shader in (HERE/'shaders').glob('*'):
      for tree in ('engine-src','data'):new_files[tree+'/game/graphics/opengl_renderer/shaders/'+shader.name]=shader
    for relative,source in new_files.items():
      dest=ROOT/relative
      if dest.exists():assert dest.read_bytes()==source.read_bytes(),relative
      outputs[dest]=source.read_bytes()
    if args.apply:
      for path,raw in outputs.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
      (HERE/'manifest.json').write_text(json.dumps({'status':'applied','files':entries,
         'new_files':{k:sha(v.read_bytes())for k,v in new_files.items()},'required_object':'generic-obs',
         'archive_installation':False,'native_validation':False},indent=2)+'\n')
    print(json.dumps({'mode':'applied'if args.apply else'dry-run','modified':list(entries),'new_files':list(new_files)},indent=2))
if __name__=='__main__':main()
