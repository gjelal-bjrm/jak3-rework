"""Prove the trunk-scar correction changes UVs only, never geometry or wind."""
import hashlib,json,math
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    old_path=HERE/'palms-patch-before-uv.json';new_path=HERE/'palms-patch.json'
    before=json.loads(old_path.read_text());after=json.loads(new_path.read_text())
    checks={
        'baseline_patch_hash':sha(old_path)=='bba76792893351fd8b930066484a6d15d8e424c63c6da4ac01becefaf47502d5',
        'all_non_add_sections_identical':{k:v for k,v in before.items() if k!='add'}=={k:v for k,v in after.items() if k!='add'},
        'same_face_count':len(before['add'])==len(after['add']),
        'all_face_metadata_identical':True,
        'positions_normals_colors_identical':True,
        'only_trunk_scar_uvs_changed':True,
        'changed_triangles_have_continuous_nonzero_uv_area':True,
        'shared_scar_points_have_shared_uvs':True,
    }
    changed=Counter();vertices=0;point_uvs={};max_u_span=0
    for old,new in zip(before['add'],after['add']):
        checks['all_face_metadata_identical'] &= {k:v for k,v in old.items() if k!='vertices'}=={k:v for k,v in new.items() if k!='vertices'}
        face_changed=False
        for a,b in zip(old['vertices'],new['vertices']):
            checks['positions_normals_colors_identical'] &= {k:v for k,v in a.items() if k!='uv'}=={k:v for k,v in b.items() if k!='uv'}
            if a['uv']!=b['uv']:face_changed=True;vertices+=1
        if face_changed:
            key=(new['tree_type'],new['geom'],new['instance']);changed[key]+=1
            checks['only_trunk_scar_uvs_changed'] &= new['tree_type']=='tie' and new['instance'] in (486,487) and new['geom'] in (0,1,2) and new.get('texture')=='market-palm-trunk-v1'
            uv=[v['uv'] for v in new['vertices']]
            area=abs((uv[1][0]-uv[0][0])*(uv[2][1]-uv[0][1])-(uv[1][1]-uv[0][1])*(uv[2][0]-uv[0][0]))*.5
            span=max(v[0] for v in uv)-min(v[0] for v in uv);max_u_span=max(span,max_u_span)
            checks['changed_triangles_have_continuous_nonzero_uv_area'] &= area>1e-8 and span<.6 and all(math.isfinite(x) for st in uv for x in st)
            for v in new['vertices']:
                point=(key,tuple(v['p']))
                if point in point_uvs:checks['shared_scar_points_have_shared_uvs'] &= point_uvs[point]==v['uv']
                else:point_uvs[point]=v['uv']
    expected={(typ,lod,instance):count for instance in (486,487) for typ,lod,count in [('tie',0,992),('tie',1,616),('tie',2,240)]}
    checks['all_and_only_3696_scar_triangles_changed']=dict(changed)==expected
    out={'status':'passed' if all(checks.values()) else 'FAILED','checks':checks,
         'before_patch_sha256':sha(old_path),'after_patch_sha256':sha(new_path),
         'before_author_sha256':sha(HERE/'author-before-uv.py'),'after_author_sha256':sha(HERE/'author.py'),
         'changed_triangles':sum(changed.values()),'changed_vertex_uv_references':vertices,
         'changed_by_component':[{'tree_type':key[0],'geom':key[1],'instance':key[2],'triangles':value} for key,value in sorted(changed.items())],
         'maximum_changed_triangle_u_span':max_u_span,
         'correction':'Cylindrical 3x7 UV mapping; atan2 angle unwrapped around scar centre, V from height. Same positions, normals, palette weights, records, textures and native wind anchors.',
         'runtime_or_fr3_modified':False,'native_visual_validation':False,
         'companion_fix':'GL_REPEAT for dedicated trunk/support wood is owned and tested separately by the parent/ocean agent.'}
    (HERE/'uv-only-validation.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2));assert all(checks.values())

if __name__=='__main__':main()
