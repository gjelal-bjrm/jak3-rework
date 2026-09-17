"""Strict, reversible grass contact insertion. Dry-run by default; no build/deploy."""
from pathlib import Path
import argparse, hashlib, json, math, shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHADER = 'game/graphics/opengl_renderer/shaders/shrub.vert'
MATERIAL = 'engine-src/game/graphics/opengl_renderer/background/PalaceMaterials.h'
KERNEL = 'engine-src/game/kernel/jak3/kmachine.cpp'
GOAL = 'goal_src/jak3/engine/target/logic-target.gc'
HEADER = 'engine-src/game/graphics/opengl_renderer/GrassContacts.h'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return Path(path).read_text(encoding='utf-8-sig')

def edits():
    glsl = read(HERE / 'contact.glsl')
    hook = read(HERE / 'hook.gc')
    shader = [
      ('vec3 palaceFoliagePosition(vec3 position,vec2 uv) {\n', glsl+'\nvec3 palaceFoliagePosition(vec3 position,vec2 uv) {\n'),
      ('    return position+vec3(horizontal.x,lift,horizontal.y)*bend*4096.0;\n',
       '    return position+vec3(horizontal.x,lift,horizontal.y)*bend*4096.0\n'
       '           +marketGrassContact(position,uv);\n')]
    goal = [
      (';; DECOMP BEGINS\n', ';; DECOMP BEGINS\n\n(define-extern pc-remaster-grass-contact (function vector int none))\n'),
      ('(defbehavior joint-points target ()\n','(defbehavior joint-points target ()\n'+hook)]
    return {
      **{tree+'/'+SHADER:shader for tree in ('engine-src','data')},
      **{tree+'/'+GOAL:goal for tree in ('engine-src','data')},
      MATERIAL:[
        ('#include "LiquidSnapshot.h"\n','#include "LiquidSnapshot.h"\n#include "game/graphics/opengl_renderer/GrassContacts.h"\n'),
        ('    m_kinds.clear();\n','    m_kinds.clear();\n    m_grass_region = level.level_name == "wascitya" ? 1 : (level.level_name == "wascityb" ? 2 : 0);\n'),
        ('    PalaceMaterialAudit::bind(program,kind ? m_names[texture] : std::string(),kind);\n',
         '    GrassContacts::bind(program, market_shrub ? m_grass_region : 0);\n'
         '    PalaceMaterialAudit::bind(program,kind ? m_names[texture] : std::string(),kind);\n'),
        ('  std::vector<int> m_kinds;\n','  int m_grass_region = 0;\n  std::vector<int> m_kinds;\n')],
      KERNEL:[
        ('#include "game/graphics/opengl_renderer/WaterContacts.h"\n',
         '#include "game/graphics/opengl_renderer/WaterContacts.h"\n#include "game/graphics/opengl_renderer/GrassContacts.h"\n'),
        ('static u64 prototype_water_contact(u32 packet) {\n',
         'static u64 prototype_grass_contact(u32 packet, u32 region) {\n'
         '  GrassContacts::push(Ptr<float>(packet).c(), static_cast<int>(region));\n'
         '  return 0;\n}\n\nstatic u64 prototype_water_contact(u32 packet) {\n'),
        ('  make_function_symbol_from_c("pc-remaster-water-contact", (void*)prototype_water_contact);\n',
         '  make_function_symbol_from_c("pc-remaster-water-contact", (void*)prototype_water_contact);\n'
         '  make_function_symbol_from_c("pc-remaster-grass-contact", (void*)prototype_grass_contact);\n')]}

def inverse(source, relative):
    for old,new in reversed(edits()[relative]):
        assert source.count(new)==1, 'Missing/modified grass insertion: '+relative
        source=source.replace(new,old,1)
    return source

def source_before(relative):
    """For parent validators: exact predecessor path, only after strict inverse."""
    manifest=json.loads(read(HERE/'manifest.json'))
    entry=manifest['files'][relative]
    path=ROOT/relative
    blade_roots=ROOT/'city-remaster/grass-contact-v2/apply.py'
    if relative.endswith('/'+SHADER) and blade_roots.with_name('manifest.json').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('grass_roots_predecessor',blade_roots)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        path=module.source_before(relative)
    city_fire=ROOT/'city-remaster/city-fire-v2/apply.py'
    if relative==KERNEL and city_fire.with_name('manifest.json').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('city_fire_predecessor',city_fire)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        path=module.source_before(relative)
    cactus=ROOT/'city-remaster/environment/geometry-001/material_response.py'
    if relative==MATERIAL and cactus.with_name('material-response.json').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('cactus_response_predecessor',cactus)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        path=module.source_before()
    assert sha(path.read_bytes())==entry['after_sha256']
    before=Path(entry['before_path'])
    assert sha(before.read_bytes())==entry['before_sha256']
    assert inverse(read(path),relative)==read(before)
    return before

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def displacement(p,uv,contacts,time):
    h=max(0,min(1,1-uv[1]/4096));bend=h*h*(3-2*h)
    strength=0;direction=(0,0)
    for x,y,z,t in contacts:
        ax,az=p[0]-x,p[2]-z;dist=math.hypot(ax,az)
        dy=p[1]-y
        value=(1-smooth(.12,.78,dist))*smooth(-.20,-.03,dy)*(1-smooth(1.25,1.85,dy))*(1-smooth(.08,1,max(0,time-t)))
        if value>strength:
            strength=value;direction=(ax/dist,az/dist)if dist>.005 else(.83205,.55470)
    return direction[0]*.28*strength*bend,-.08*strength*bend,direction[1]*.28*strength*bend

def verify_math():
    c=[(0,0,0,0)];tip=(.25,.65,0)
    assert displacement(tip,(100,4096),c,0)==(0,0,0)
    assert displacement(tip,(100,0),c,0)==displacement(tip,(100,0),c*16,0)
    assert displacement((1,.6,0),(100,0),c,0)==(0,0,0)
    assert displacement((.2,3,0),(100,0),c,0)==(0,0,0)
    assert displacement(tip,(100,0),c,1)==(0,0,0)
    steps=[math.sqrt(sum(a*a for a in displacement(tip,(100,0),c,t)))for t in (0,.1,.3,.6,.9,1)]
    assert all(a>=b for a,b in zip(steps,steps[1:])) and steps[0]>.10
    return {'roots_fixed':True,'outside_radius_unchanged':True,'other_floor_unchanged':True,
      'duplicates_do_not_amplify':True,'smooth_monotonic_recovery':True,
      'zero_after_one_second':True,'sample_displacement_by_age_m':steps,
      'max_displacement_m':math.hypot(.28,.08),'native_visual_validation':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');args=p.parse_args()
    existing=json.loads(read(HERE/'manifest.json'))if(HERE/'manifest.json').exists()else None
    entries={};outputs={}
    for relative,changes in edits().items():
        path=ROOT/relative;raw=path.read_bytes();source=read(path)
        newline='\r\n'if b'\r\n'in raw else'\n'
        if existing:
            before=source_before(relative);updated=source
            entries[relative]=existing['files'][relative]
        else:
            updated=source
            for old,new in changes:
                assert updated.count(old)==1,'Unexpected anchor: '+relative+': '+old[:80]
                updated=updated.replace(old,new,1)
            assert inverse(updated,relative)==source
            before=HERE/'before'/relative
            entries[relative]={'before_path':str(before),'before_sha256':sha(raw),
                              'after_sha256':sha(updated.replace('\n',newline).encode())}
            if args.apply:
                assert not before.exists() or before.read_bytes()==raw
                before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(raw)
        outputs[path]=updated.replace('\n',newline).encode()
    assert outputs[ROOT/'engine-src'/SHADER]==outputs[ROOT/'data'/SHADER]
    assert read(ROOT/'engine-src'/GOAL)==read(ROOT/'data'/GOAL)
    checks=verify_math()
    manifest={'status':'applied'if args.apply else'prepared','scope':'Jak only; WCA/WCB; market-shrub-orange-v1 only',
      'files':entries,'new_header':HEADER,'new_header_sha256':sha((HERE/'GrassContacts.h').read_bytes()),
      'goals':['logic-target'],'native_validation':False,'checks':checks}
    if args.apply:
        for path,raw in outputs.items():
            if path.read_bytes()!=raw:path.write_bytes(raw)
        if not(ROOT/HEADER).exists()or(ROOT/HEADER).read_bytes()!=(HERE/'GrassContacts.h').read_bytes():
            shutil.copyfile(HERE/'GrassContacts.h',ROOT/HEADER)
        (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (HERE/'validation.json').write_text(json.dumps({'status':'passed','applied':args.apply,'checks':checks},indent=2)+'\n')
    print(json.dumps({'status':'passed','applied':args.apply,'files':list(entries),'checks':checks},indent=2))

if __name__=='__main__':main()
