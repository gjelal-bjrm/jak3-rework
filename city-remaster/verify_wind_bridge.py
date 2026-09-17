"""Offline bridge checks: native wind, isolated textures, byte-preserved neighbours."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import struct
import subprocess
import zstandard

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BRIDGE=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'
WORK=HERE/'wind-validation'
CHECKS=[]


def check(name,condition):
    assert condition,name
    CHECKS.append(name)


def write(path,obj):
    path.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')


def run(*args,code=0):
    result=subprocess.run([str(BRIDGE),*map(str,args)],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==code,(args,result.returncode,result.stdout,result.stderr)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decompress(path):
    raw=path.read_bytes();size=struct.unpack_from('<Q',raw)[0]
    return zstandard.ZstdDecompressor().decompress(raw[8:],max_output_size=size)


def norm(v):
    length=math.sqrt(sum(c*c for c in v));return [c/length for c in v]


def main():
    WORK.mkdir(exist_ok=True)
    doc=json.loads((HERE/'market-plants-native.json').read_text())
    source=Path(doc['source_fr3']['path']) if 'path' in doc['source_fr3'] else Path(doc['selection']['source_fr3']['path'])
    identity={'sha256':sha(source),'bytes':source.stat().st_size}
    check('current market source pinned',identity['sha256']==doc['source_fr3']['sha256'])
    base={'level':doc['level'],'source_fr3':identity,'preserve_bvh':True,'remove':[],'add':[]}
    write(WORK/'noop.json',base)
    run(source,WORK/'noop.json',WORK/'noop.fr3')
    check('noop serialized bytes identical',decompress(source)==decompress(WORK/'noop.fr3'))

    fixtures=[next(f for f in doc['faces'] if f['tree_type']==kind and f['geom']==0) for kind in ('tie','tie_wind','shrub')]
    patch=deepcopy(base)
    (WORK/'test.rgba').write_bytes(bytes([137,114,60,128])*4)
    patch['new_textures']=[{'name':'bridge-test-isolated','page':'bridge-offline-tests','width':2,'height':2,
                            'rgba_file':str(WORK/'test.rgba')}]
    expected_normal=norm([.3,.7,-.4])
    for source_face in fixtures:
        metadata={k:source_face[k]for k in ('tree_type','geom','tree','draw','group','instance')}
        patch['remove'].append({**metadata,'stream_index':source_face['stream_index'],
                                'original_positions':[v['p']for v in source_face['vertices']]})
        vertices=[]
        for i,v in enumerate(source_face['vertices']):
            vertex={'p':v['p'],'uv':v['uv'],'normal':expected_normal,
                    'color_indices':[a['color']for a in source_face['vertices']],
                    'color_weights':[int(i==j)for j in range(3)]}
            if 'rgba' in v:vertex['rgba']=v['rgba']
            vertices.append(vertex)
        patch['add'].append({**metadata,'texture':'bridge-test-isolated','vertices':vertices})
    write(WORK/'isolated.json',patch)
    run(source,WORK/'isolated.json',WORK/'isolated.fr3')
    run('--audit-patch',source,WORK/'isolated.json',WORK/'isolated.fr3',WORK/'preservation.json')
    audit=json.loads((WORK/'preservation.json').read_text())
    for key in ('level_identity','hfrag_unchanged','collision_unchanged','merc_unchanged','index_textures_unchanged'):
        check(key,audit[key])
    check('every old texture byte-identical',all(t['unchanged']for t in audit['textures']))
    check('exactly one dedicated texture appended',audit['appended_textures']==1)
    check('every TFRAG byte-identical',all(t['unchanged']for t in audit['tfrag']))
    for tree in audit['tie']:
        label=f"TIE {tree['geom']}/{tree['tree']} "
        for key in ('bvh_unchanged','packed_vertices_prefix','packed_matrix_groups_prefix','packed_matrices_unchanged',
                    'color_indices_prefix','palette_active_prefix','wind_instances_unchanged','wind_groups_unchanged'):
            check(label+key,tree[key])
        chosen=[f for f in fixtures if f['tree_type']=='tie' and(f['geom'],f['tree'])==(tree['geom'],tree['tree'])]
        check(label+'only selected static draw changed',tree['unmatched_original_static_draws']==[f['draw']for f in chosen])
        chosen=[f for f in fixtures if f['tree_type']=='tie_wind' and(f['geom'],f['tree'])==(tree['geom'],tree['tree'])]
        check(label+'only selected wind group changed',tree['changed_wind_groups']==[
              {k:f[k]for k in ('draw','group','instance')}for f in chosen])
        check(label+'unselected static faces preserve winding/material/visibility',tree['static_triangles']['unselected_unchanged'])
        check(label+'unselected wind faces preserve winding/material/visibility',tree['wind_triangles']['unselected_unchanged'])
    for tree in audit['shrub']:
        label=f"SHRUB {tree['tree']} "
        for key in ('palette_unchanged','packed_vertices_prefix','packed_instance_groups_prefix','packed_matrices_prefix','indices_prefix'):
            check(label+key,tree[key])
        chosen=[f for f in fixtures if f['tree_type']=='shrub' and f['tree']==tree['tree']]
        check(label+'only selected draw changed',tree['changed_original_draws']==[f['draw']for f in chosen])
        check(label+'unselected faces preserve winding/material',tree['triangles']['unselected_unchanged'])

    selection=deepcopy(doc['selection']);selection.pop('instances',None)
    selection['materials']=['bridge-test-isolated'];selection['geoms']=[0]
    selection['source_fr3']={'sha256':sha(WORK/'isolated.fr3'),'bytes':(WORK/'isolated.fr3').stat().st_size}
    write(WORK/'selected.json',selection)
    run('--export-selected',WORK/'isolated.fr3',WORK/'selected.json',WORK/'selected.json.out')
    result=json.loads((WORK/'selected.json.out').read_text())
    for instance in result['instance_inventory']:
        if instance['tree_type']=='tie_wind':
            check('wind instance matrices and parameters byte-equivalent in export',instance in doc['instance_inventory'])
    isolated=[f for f in result['faces']if f['material']=='bridge-test-isolated']
    check('dedicated material reaches exactly selected triangles',len(isolated)==3)
    for f in isolated:
        old=next(s for s in fixtures if s['tree_type']==f['tree_type'])
        for v in f['vertices']:
            original=min(old['vertices'],key=lambda o:math.dist(o['p'],v['p']))
            check(f['tree_type']+' world vertex preserved',math.dist(original['p'],v['p'])<.002)
            check(f['tree_type']+' UV contract unchanged',math.dist(original['uv'],v['uv'])<1e-6)
            if f['tree_type']=='tie_wind':
                dot=max(-1.,min(1.,sum(a*b for a,b in zip(expected_normal,norm(v['normal'])))))
                check('anisotropic world normal error under one degree',math.degrees(math.acos(dot))<1.)

    bad=deepcopy(patch);bad['source_fr3']['sha256']='0'*64;write(WORK/'bad-hash.json',bad)
    run(source,WORK/'bad-hash.json',WORK/'rejected.fr3',code=2)
    check('wrong source writes no FR3',not(WORK/'rejected.fr3').exists())
    bad=deepcopy(patch)
    next(f for f in bad['remove']if f['tree_type']=='tie_wind')['instance']+=1
    write(WORK/'bad-instance.json',bad);run(source,WORK/'bad-instance.json',WORK/'rejected.fr3',code=2)
    check('wrong wind instance writes no FR3',not(WORK/'rejected.fr3').exists())
    bad=deepcopy(patch)
    next(f for f in bad['remove']if f['tree_type']=='tie_wind')['original_positions'][0][0]+=10
    write(WORK/'bad-position.json',bad);run(source,WORK/'bad-position.json',WORK/'rejected.fr3',code=2)
    check('wrong wind origin writes no FR3',not(WORK/'rejected.fr3').exists())
    write(WORK/'validation.json',{'passed':len(CHECKS),'checks':CHECKS,'source_fr3':identity,
                                 'bridge_sha256':sha(BRIDGE),'native_game_validation':False})
    print(f'{len(CHECKS)} bridge preservation/geometry checks passed; no live files modified')


if __name__=='__main__':main()
