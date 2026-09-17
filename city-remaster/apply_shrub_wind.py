"""Bounded mode-2 wind for authored market shrubs; no build or packaging.

Default is validation/dry run. --apply inserts one branch in the two identical
shrub.vert copies. The strict inverse recovers the complete accepted shader.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse,hashlib,json,math

ROOT=Path(__file__).resolve().parents[1]
SHADER=Path('game/graphics/opengl_renderer/shaders/shrub.vert')
BASE_SHA256='a88631c931a390c2963781a21643ceb47f83ba39ddac687c5912b3b681b72d73'
ANCHOR='vec3 palaceFoliagePosition(vec3 position,vec2 uv) {\n'
BRANCH='''  // MARKET_SHRUB_WIND_BEGIN: only market-shrub-orange-v1 selects mode 2.
  if(palace_foliage==2) {
    // SHRUB UVs enter this shader in native fixed-point units. The rebuilt
    // closed blades use V=4096 at the root and V=0 at the tip.
    vec2 leafUV=uv/4096.0;
    float height=clamp(1.0-leafUV.y,0.0,1.0);
    float bend=height*height*(3.0-2.0*height);
    vec3 p=position/4096.0;
    float phase=dot(p.xz-vec2(1767.0,-330.0),vec2(.37,.29));
    float sway=.023*sin(palace_time*.91+phase)
              +.009*sin(palace_time*1.67-phase*.39);
    float crosswind=.009*sin(palace_time*1.13+phase*.71);
    float flutter=.004*sin(palace_time*3.17+phase*1.3+leafUV.x*11.0+height*2.0)*height;
    vec2 direction=normalize(vec2(3.0,2.0));
    vec2 sideways=vec2(-direction.y,direction.x);
    vec2 horizontal=direction*sway+sideways*(crosswind+flutter);
    float lift=.002*sin(palace_time*1.81+phase*.83)*height;
    // The analytic displacement bound is 3.46 cm. Roots remain exactly fixed.
    return position+vec3(horizontal.x,lift,horizontal.y)*bend*4096.0;
  }
  // MARKET_SHRUB_WIND_END
'''

def sha(data):return hashlib.sha256(data).hexdigest()
def without_market_shrub_wind(source):
    assert source.count(BRANCH)==1,'Missing or altered bounded shrub-wind branch'
    return source.replace(BRANCH,'',1)
def with_market_shrub_wind(source):
    if BRANCH in source:
        assert source.count(BRANCH)==1
        return source
    assert 'MARKET_SHRUB_WIND_' not in source,'Partial or changed wind insertion'
    assert source.count(ANCHOR)==1,'Unexpected shrub shader structure'
    return source.replace(ANCHOR,ANCHOR+BRANCH,1)

def displacement(p,uv,time):
    u,v=[value/4096 for value in uv];height=max(0,min(1,1-v));bend=height*height*(3-2*height)
    phase=(p[0]-1767)*.37+(p[2]+330)*.29
    sway=.023*math.sin(time*.91+phase)+.009*math.sin(time*1.67-phase*.39)
    across=.009*math.sin(time*1.13+phase*.71)+.004*math.sin(time*3.17+phase*1.3+u*11+height*2)*height
    dx,dz=3/math.sqrt(13),2/math.sqrt(13);lift=.002*math.sin(time*1.81+phase*.83)*height
    return ((dx*sway-dz*across)*bend,lift*bend,(dz*sway+dx*across)*bend)

def check_authored_uvs():
    patch_path=ROOT/'city-remaster/market-shrubs-patch.json'
    patch=json.loads(patch_path.read_text())
    faces=[f for f in patch['add'] if f.get('texture')=='market-shrub-orange-v1']
    assert faces and all(f['tree_type']=='shrub' for f in faces)
    vertices=[v for f in faces for v in f['vertices']]
    ranges=[[min(v['uv'][i] for v in vertices),max(v['uv'][i] for v in vertices)] for i in range(2)]
    assert ranges[1]==[0,4096],'Authored blade root/tip convention changed'
    roots=[v for v in vertices if v['uv'][1]==4096]
    tips=[v for v in vertices if v['uv'][1]==0]
    assert roots and tips
    times=[0,.37,1.25,4.7,9.1,31.0]
    assert all(displacement(v['p'],v['uv'],t)==(0,0,0) for v in roots[::max(1,len(roots)//80)] for t in times)
    samples=[displacement(v['p'],v['uv'],t) for v in tips[::max(1,len(tips)//100)] for t in times]
    peak=max(math.sqrt(sum(x*x for x in delta)) for delta in samples)
    bound=math.sqrt(.032**2+.013**2+.002**2)
    assert .001<peak<=bound<.04
    return {'authored_patch_sha256':sha(patch_path.read_bytes()),'faces':len(faces),'uv_ranges':ranges,'root_vertex_references':len(roots),'tip_vertex_references':len(tips),'roots_stationary':True,'tip_time_variation':True,'sampled_peak_displacement_m':peak,'analytic_max_displacement_m':bound,'mode_1_palace_branch_changed':False,'source_author':'city-remaster/author_shrubs.py; native UVs multiply by4096 after records inverse-V','native_visual_validation':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    paths=[ROOT/tree/SHADER for tree in ('engine-src','data')]
    before=[p.read_bytes() for p in paths]
    assert before[0]==before[1],'Engine/data shrub shader copies differ before patch'
    newline='\r\n' if b'\r\n' in before[0] else '\n'
    source=before[0].decode('utf-8').replace('\r\n','\n')
    updated=with_market_shrub_wind(source)
    original=without_market_shrub_wind(updated)
    original_bytes=original.replace('\n',newline).encode('utf-8')
    assert sha(original_bytes)==BASE_SHA256,'Shader differs from accepted complete baseline'
    after=updated.replace('\n',newline).encode('utf-8')
    validation=check_authored_uvs()
    manifest={'scope':'Only market-shrub-orange-v1 via palace_foliage=2 in shrub.vert','time_uniform':'palace_time','time_source':'LiquidSnapshot::seconds(), set by PalaceMaterials::bind (parent integration)','selector_uniform':'palace_foliage','selector_value':2,'texture':'market-shrub-orange-v1','strict_inverse':'city-remaster/apply_shrub_wind.py::without_market_shrub_wind','accepted_complete_shader_sha256':BASE_SHA256,'palace_mode_1_preserved_byte_for_byte_by_inverse':True,'engine_data_identical':True,'validation':validation,'files':[{'path':p.relative_to(ROOT).as_posix(),'before_sha256':sha(b),'after_sha256':sha(after)} for p,b in zip(paths,before)]}
    if args.apply:
        for p in paths:p.write_bytes(after)
        assert paths[0].read_bytes()==paths[1].read_bytes()==after
        manifest_path=ROOT/'city-remaster/shrub-wind-manifest.json'
        # Preserve initial provenance on an idempotent second --apply.
        if manifest_path.exists():
            existing=json.loads(manifest_path.read_text())
            if all(e['after_sha256']==sha(after) for e in existing.get('files',[])):
                manifest['files']=existing['files']
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    validation_path=ROOT/'city-remaster/shrub-wind-validation.json'
    validation_path.write_text(json.dumps({'status':'passed','applied':args.apply,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'shader_sha256':sha(after),'checks':validation},indent=2)+'\n')
    print(json.dumps({'status':'passed','applied':args.apply,'shader_sha256':sha(after),'wind':validation},indent=2))

if __name__=='__main__':main()
