"""Combine the reviewed support/palm/shrub assets on an isolated WCB copy.

No live data is changed. Dedicated materials append to the native texture table.
The baseline must be the installed Merc market batch, with no later mutations.
"""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,math,shutil,subprocess
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent

def sha(path):
    with path.open('rb') as h:return hashlib.file_digest(h,'sha256').hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,j):p.write_text(json.dumps(j,indent=2),encoding='utf-8')
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','group','stream_index'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='market-static-001');parser.add_argument('--apply-to-stage',action='store_true');a=parser.parse_args()
    stage=(HERE/'staging'/a.stage).resolve();assert stage.parent==HERE/'staging'
    stage.mkdir(exist_ok=True);output=stage/'wascityb.fr3';assert not output.exists(),'Use a new stage for a new candidate'
    live=ROOT/'data/out/jak3/fr3/wascityb.fr3';installed=read(HERE/'installed.json')
    merc=next(x for x in installed['levels'] if x['path'].endswith('/wascityb.fr3'))
    live_hash=sha(live);source=live
    if live_hash!=merc['output_sha256']:
        previous=read(HERE/'static-installed.json')
        assert previous['output_sha256']==live_hash and previous['base_sha256']==merc['output_sha256'],'Untracked live static change'
        source=Path(previous['base_path'])
        assert sha(source)==merc['output_sha256'],'Static refinement baseline changed'
    base=stage/'before-wascityb.fr3'
    if base.exists():assert sha(base)==sha(source)
    else:shutil.copy2(source,base)
    patches=[HERE/'supports/patch.json',HERE/'palms/palms-patch.json',HERE/'market-shrubs-patch.json']
    combined={'level':'wascityb','source_fr3':{'sha256':sha(base),'bytes':base.stat().st_size},'preserve_bvh':True,'new_textures':[],'remove':[],'add':[]}
    parts=[]
    for p in patches:
        j=read(p);assert j.get('level','wascityb')=='wascityb'
        combined['remove'].extend(j['remove']);combined['add'].extend(j['add']);combined['new_textures'].extend(j.get('new_textures',[]))
        parts.append({'path':str(p),'sha256':sha(p),'removed':len(j['remove']),'added':len(j['add'])})
    for kind in ['wood','metal']:
        p=HERE/f'support-{kind}-hd.png';im=Image.open(p).convert('RGBA')
        # Native opaque alpha is 128, not PNG's 255. RGB bytes are copied
        # exactly; this is engine-format conversion, not an image retouch.
        pixels=bytearray(im.tobytes());pixels[3::4]=bytes([128])*im.width*im.height
        raw=HERE/'supports'/f'{kind}.rgba';raw.write_bytes(pixels)
        combined['new_textures'].append({'name':f'market-support-{kind}-v1','page':'remaster-market-supports','width':im.width,'height':im.height,'rgba_file':str(raw)})
    keys=[key(f) for f in combined['remove']];assert len(keys)==len(set(keys)),'Overlapping native removals'
    # Both exports predate these static changes. Every removal must match its
    # exact native face, preventing accidental edits to neighbouring objects.
    known={key(f):f for n in ['market-block-native.json','market-plants-native.json'] for f in read(HERE/n)['faces']}
    for f in combined['remove']:
        source=known[key(f)];assert f['original_positions']==[v['p'] for v in source['vertices']]
    names=[t['name'] for t in combined['new_textures']];assert len(names)==len(set(names))
    for t in combined['new_textures']:
        assert Path(t['rgba_file']).stat().st_size==t['width']*t['height']*4
    min_area=math.inf;max_normal_error=0
    for f in combined['add']:
        if 'texture' in f:assert f['texture'] in names
        assert len(f['vertices'])==3
        for v in f['vertices']:
            assert all(math.isfinite(x) for k in ['p','uv','normal','color_weights'] for x in v[k])
            max_normal_error=max(max_normal_error,abs(math.sqrt(sum(x*x for x in v['normal']))-1))
            assert abs(sum(v['color_weights'])-1)<.0001
        p=[v['p'] for v in f['vertices']];u=[p[1][i]-p[0][i] for i in range(3)];v=[p[2][i]-p[0][i] for i in range(3)]
        area=math.sqrt(sum(x*x for x in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))*.5
        min_area=min(min_area,area)
    assert max_normal_error<.002 and min_area>1e-12,(max_normal_error,min_area)
    patch=stage/'combined-patch.json';patch.write_text(json.dumps(combined,separators=(',',':')))
    report={'scope':'14 posts, 14 arms, 28 links, 2 complete palms, 69 grass tufts around WCB market','base':str(base),'base_sha256':sha(base),'output':str(output),'patch':str(patch),'patch_sha256':sha(patch),'parts':parts,'removed':len(keys),'added':len(combined['add']),'added_by_type_lod':dict(Counter(f"{f['tree_type']}/{f['geom']}" for f in combined['add'])),'dedicated_textures':names,'minimum_triangle_area_m2':min_area,'maximum_normal_length_error':max_normal_error,'preserve_bvh':True,'native_visual_validation':False,'status':'Author constraints passed; native preservation audit pending'}
    report['replaces_live_sha256']=live_hash
    if a.apply_to_stage:
        with (stage/'bridge.log').open('w') as log:
            subprocess.run([str(ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'),str(base),str(patch),str(output)],stdout=log,stderr=subprocess.STDOUT,check=True)
        report['output_sha256']=sha(output)
    write(stage/'author-validation.json',report)
    print(json.dumps({k:report[k] for k in ['status','removed','added','dedicated_textures','minimum_triangle_area_m2']},indent=2))

if __name__=='__main__':main()
