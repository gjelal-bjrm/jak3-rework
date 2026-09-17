"""Validate and combine Blender patches against a clean extracted native level."""
from pathlib import Path
import json,hashlib,subprocess,sys,math
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
source=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'waspala-before-models.fr3'
destination=Path(sys.argv[2]) if len(sys.argv)>2 else HERE/'waspala-objects.fr3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config_path=HERE/'model-set.json'
config=json.loads(config_path.read_text()) if config_path.exists() else {}
parts=config.get('parts',['brazier-patch.json','planter-patch.json','throne-patch.json','foliage-patch.json'])
combined={'description':'Validated palace Blender models; source triangle positions checked by native importer','remove':[],'add':[]}
if config.get('texture_manifest'):
    combined['textures']=json.loads((HERE/config['texture_manifest']).read_text())
seen=set();summaries=[]
for name in parts:
    part=json.loads((HERE/name).read_text())
    for face in part['remove']:
        key=tuple(face.get(k,'tie') for k in ('tree_type','geom','tree','draw','stream_index'))
        assert key not in seen,('Overlapping model replacements',name,key)
        seen.add(key)
    for face in part['add']:
        assert len(face['vertices'])==3
        for v in face['vertices']:
            assert all(math.isfinite(x) for x in v['p']+v['uv']+v['normal']+v['color_weights'])
            assert abs(sum(v['color_weights'])-1)<.001
    combined['remove'].extend(part['remove']);combined['add'].extend(part['add'])
    summaries.append({'file':name,'sha256':sha(HERE/name),'removed':len(part['remove']),'added':len(part['add'])})
    print(name,len(part['remove']),'->',len(part['add']),flush=True)
    del part
# The fuel faces must be byte-for-byte identical in world position. The accepted
# fire shader uses their eight-plane height field, so moving them is a regression.
native=json.loads((HERE/'native-objects.json').read_text())['faces']
coal_draws={(f['geom'],f['tree'],f['draw']) for f in native if f['tree_type']=='tie' and f['material']=='waspala-fire-coal'}
def signature(vertices):return tuple(sorted(tuple(round(x,5) for x in v['p']) for v in vertices))
before=sorted(signature(f['vertices']) for f in native if f['tree_type']=='tie' and f['material']=='waspala-fire-coal')
after=sorted(signature(f['vertices']) for f in combined['add'] if f.get('tree_type','tie')=='tie' and (f['geom'],f['tree'],f['draw']) in coal_draws)
assert before==after,'The native fuel bowl moved: refusing the model build'
del native
path=HERE/'combined-patch.json';path.write_text(json.dumps(combined,separators=(',',':')))
report={'source':str(source),'source_sha256':sha(source),'parts':summaries,
        'removed_triangles':len(combined['remove']),'added_triangles':len(combined['add']),
        'fuel_faces_exactly_preserved':len(before),'overlapping_replacements':0}
del combined
result=subprocess.run([str(ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'),str(source),str(path),str(destination)])
assert result.returncode==0,f'Native model importer failed: {result.returncode}'
report['output']=str(destination);report['output_sha256']=sha(destination)
(HERE/'native-model-validation.json').write_text(json.dumps(report,indent=2))
print('Native model build validated:',destination,flush=True)
