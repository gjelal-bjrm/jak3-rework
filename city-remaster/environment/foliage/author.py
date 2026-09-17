"""Extend the reviewed complete-palm author to every remaining WCB palm.

Run with Blender --background --python city-remaster/environment/foliage/author.py.
All output stays in this directory. No live FR3 or market author is changed.
"""
import hashlib, importlib.util, json, sys
from pathlib import Path
from collections import defaultdict
import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parent
SOURCE=CITY/'palms/author.py'
EXPECTED_AUTHOR='6d0a20d7c825dc43963009012e3536319396240dfa6dd8635a9719e783497e92'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2)+'\n')

def main():
    assert sha(SOURCE)==EXPECTED_AUTHOR,'Reviewed author changed: inspect before reusing'
    mapping=json.loads((HERE/'map.json').read_text());native=json.loads((HERE/'native.json').read_text())
    assert sha(HERE/'native.json')==mapping['native_export_sha256']
    spec=importlib.util.spec_from_file_location('reviewed_market_palms',SOURCE)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    core.NATIVE=native;core.MAP=mapping;core.HERE=HERE;core.ORIGIN=Vector((1650,25,-520))
    core.FACEMAP=defaultdict(list)
    for f in native['faces']:core.FACEMAP[(f['tree_type'],f['instance'],f['geom'])].append(f)
    core.INVMAP={(i['tree_type'],i['instance'],i['geom']):i for i in native['instance_inventory']}
    core.reset();report={'source':'native.json','source_sha256':sha(HERE/'native.json'),
        'source_fr3':mapping['source_fr3'],'reviewed_author':str(SOURCE),'reviewed_author_sha256':sha(SOURCE),
        'native_wind_preserved_by_bridge':True,'assets':[],'native_visual_validation':False,'live_files_written':False,
        'preserved_market_trunks':[486,487],'coincident_native_trunk_groups':mapping['coincident_native_trunk_groups']}
    tissue=ROOT/'models-v2/leaf-tissue.rgba';bark=CITY/'palms/trunk-tissue.rgba'
    textures=[{'name':core.LEAF_TEXTURE,'page':'remaster-market-plants','width':1024,'height':1024,'rgba_file':str(tissue)},
        {'name':core.TRUNK_TEXTURE,'page':'remaster-market-plants','width':887,'height':1774,'rgba_file':str(bark)}]
    for t in textures:assert Path(t['rgba_file']).stat().st_size==t['width']*t['height']*4
    removal=[{**{k:f[k] for k in ('tree_type','geom','tree','draw','group','stream_index','instance')},
        'original_positions':[v['p'] for v in f['vertices']]} for f in native['faces']]
    header={'description':'Complete remaining WCB palms using reviewed market geometry; preserve all native anchors and wind',
        'level':'wascityb','source_fr3':mapping['source_fr3'],'preserve_bvh':True,'new_textures':textures,'remove':removal}
    # Stream additions per component rather than retaining the full city patch
    # as several copies of hundreds of thousands of Python dictionaries.
    lod0=[];by_trunk={};first=True
    with (HERE/'patch.json').open('w') as out:
        out.write(json.dumps(header,separators=(',',':'))[:-1]+',"add":[')
        for palm in mapping['palms']:
            trunk_id=palm['trunk_source']['instance'];by_trunk[trunk_id]=[]
            for part in palm['parts_geom0']:
                kind,instance=part['tree_type'],part['instance']
                for lod in range(4):
                    a=core.Author(kind,instance,lod)
                    # Duplicate native visibility instances occupy exactly the
                    # same spatial matrix. Keep their detailed silhouettes equal.
                    if kind=='tie_wind':a.instance=mapping['wind_geometry_seed_aliases'][str(instance)]
                    if kind=='tie':details=core.trunk(a)
                    elif 'leaf' in a.material:details=core.crown(a)
                    else:details=core.beard(a)
                    a.instance=instance
                    tris=a.finish();removed,added,distance=a.records()
                    if not first:out.write(',')
                    out.write(json.dumps(added,separators=(',',':'))[1:-1]);first=False
                    report['assets'].append({'kind':kind,'instance':instance,'lod':lod,'removed':len(removed),
                        'triangles':tris,'details':details,'max_native_surface_distance_m':distance,
                        'matrix_columns':a.inv['matrix_columns'],'wind_index':a.inv.get('wind_index'),
                        'stiffness':a.inv.get('stiffness'),'trunk':trunk_id})
                    a.asset.obj['native_lod']=lod
                    a.asset.obj.hide_render=lod!=0;a.asset.obj.hide_set(lod!=0)
                    if lod==0:lod0.append(a.asset.obj);by_trunk[trunk_id].append(a.asset.obj)
            print('Complete palm',trunk_id,'authored; components',len(report['assets']),flush=True)
        out.write(']}')
    report['removed']=len(removal);report['added']=sum(a['triangles'] for a in report['assets'])
    report['triangles_by_lod']={str(lod):sum(a['triangles'] for a in report['assets'] if a['lod']==lod) for lod in range(4)}
    report['patch_sha256']=sha(HERE/'patch.json');report['textures']=[dict(t,sha256=sha(Path(t['rgba_file']))) for t in textures]
    write(HERE/'report.json',report)
    # Representative inner-city and shore palms inspect the transformed forms.
    core.preview(by_trunk[488]+by_trunk[489],'inner-city-palms.png')
    core.preview(by_trunk[493]+by_trunk[494]+by_trunk[497],'shore-palms.png')
    core.preview(lod0,'wcb-palms-overview.png')
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':obj.hide_render=obj.get('native_lod',0)!=0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'wcb-complete-palms.blend'))
    print(json.dumps({k:report[k] for k in ('removed','added','triangles_by_lod','patch_sha256')},indent=2),flush=True)

if __name__=='__main__':main()
