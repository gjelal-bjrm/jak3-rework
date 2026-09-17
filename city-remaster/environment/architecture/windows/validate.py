"""Validate authored window patches without importing or changing native FR3s."""
from pathlib import Path
from collections import defaultdict
import hashlib,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(f):return tuple(f[k]for k in('tree_type','geom','tree','draw','stream_index'))
def cross2(a,b):return float(a[0]*b[1]-a[1]*b[0])

def area(p):
    if len(p)<3:return 0.
    return abs(sum(cross2(p[i],p[(i+1)%len(p)])for i in range(len(p))))*.5
def clipped(poly,boundary):
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)];result=[]
        for j,p in enumerate(poly):
            q=poly[j-1];dp=cross2(b-a,p-a);dq=cross2(b-a,q-a)
            if (dp<=0)!=(dq<=0):result.append(q+(p-q)*(dq/(dq-dp)))
            if dp<=0:result.append(p)
        poly=result
        if not poly:break
    return area(poly)

def main():
    author=json.loads((HERE/'author-report.json').read_text());report={'status':'passed','checks':{},'levels':{}}
    for level,row in author.items():
        source=json.loads((HERE/f'{level}-native.json').read_text());patch=json.loads((HERE/f'{level}-patch.json').read_text())
        old={key(f):f for f in source['faces']};selected=[f for f in source['faces']if f['material']=='wascity-metal-segments']
        checks={}
        checks['source_export_hash_pinned']=patch['source_fr3']==source['source_fr3']
        checks['patch_hash_matches_author']=sha(HERE/f'{level}-patch.json')==row['patch_sha256']
        checks['only_confirmed_metal_window_frames_removed']={key(f)for f in patch['remove']}=={key(f)for f in selected}
        checks['no_duplicate_removals']=len({key(f)for f in patch['remove']})==len(patch['remove'])
        checks['original_positions_exact']=all(f['original_positions']==[v['p']for v in old[key(f)]['vertices']]for f in patch['remove'])
        checks['no_texture_or_collision_replacement']=not patch.get('textures')and not patch.get('new_textures')and patch['preserve_bvh']is True
        architecture=json.loads((HERE.parent/f'{level}-native.json').read_text())
        checks['disjoint_from_stucco_architecture_keys']=not({key(f)for f in patch['remove']}&{key(f)for f in architecture['faces']})
        original_groups=defaultdict(list);new_groups=defaultdict(list)
        for f in selected:original_groups[f['tree'],f['geom'],f['instance']].append(f)
        for f in patch['add']:new_groups[f['tree'],f['geom'],f['instance']].append(f)
        checks['exact_frame_instance_lod_inventory']=set(original_groups)==set(new_groups)
        matrices={(r['tree'],r['geom'],r['instance']):r for r in source['instance_inventory']if r['tree_type']=='tie'}
        finite=True;normals=True;colors=True;group_draws=True;radius=True;min_area=float('inf');worst_rad=0.
        for group,faces in new_groups.items():
            before=original_groups[group];palette={v['color']for f in before for v in f['vertices']};draws={(f['draw'],f['group'])for f in before}
            pos=np.array([[v['p']for v in f['vertices']]for f in faces]);normal=np.array([v['normal']for f in faces for v in f['vertices']])
            weights=np.array([v['color_weights']for f in faces for v in f['vertices']]);uv=np.array([v['uv']for f in faces for v in f['vertices']])
            finite &= all(np.isfinite(a).all()for a in(pos,normal,weights,uv))
            normals &= np.max(abs(np.linalg.norm(normal,axis=1)-1))<.0001
            colors &= bool(np.min(weights)>=0 and np.max(weights)<=1 and np.max(abs(weights.sum(axis=1)-1))<1e-7)
            colors &= all(set(v['color_indices'])<=palette for f in faces for v in f['vertices'])
            group_draws &= all((f['draw'],f['group'])in draws and f['tree_type']=='tie'for f in faces)
            triangles=np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)*.5;min_area=min(min_area,float(triangles.min()))
            origin=np.array(matrices[group]['origin_m']);oldp=np.array([v['p']for f in before for v in f['vertices']])
            delta=float(np.linalg.norm(pos.reshape(-1,3)-origin,axis=1).max()-np.linalg.norm(oldp-origin,axis=1).max());worst_rad=max(worst_rad,delta);radius &= delta<.002
        checks.update(finite_vertices_uv_weights=bool(finite),unit_world_normals=bool(normals),convex_native_palette_weights=bool(colors),
                      native_material_vis_groups_preserved=bool(group_draws),nondegenerate_triangles=min_area>1e-9,
                      within_original_instance_radius=bool(radius))
        aperture_area=0.
        for template in row['templates']:
            boundary=np.array(template['aperture'])[:,:2];centre=boundary.mean(axis=0)
            # Keep a 2cm numerical margin inside the original opening, not a new aperture.
            boundary=centre+(boundary-centre)*.99
            vertices=np.array(template['p'])[:,:2]
            for face in template['faces']:
                # Quads/convex bevel faces; fan suffices to detect any occlusion.
                for j in range(1,len(face)-1):aperture_area+=clipped([vertices[k]for k in(face[0],face[j],face[j+1])],boundary)
        checks['original_aperture_clear_all_lods']=aperture_area<1e-6
        report['levels'][level]={'checks':{k:bool(v)for k,v in checks.items()},'removed':len(patch['remove']),'added':len(patch['add']),
                                 'minimum_triangle_area_m2':min_area,'maximum_radius_delta_m':worst_rad,'projected_aperture_occlusion_m2':aperture_area,
                                 'patch':str(HERE/f'{level}-patch.json'),'patch_sha256':row['patch_sha256']}
        for k,v in checks.items():report['checks'][level+'/'+k]=bool(v)
        print(level,[k for k,v in checks.items()if not v],flush=True)
    report['status']='passed'if all(report['checks'].values())else'failed'
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n');assert report['status']=='passed'
    print(len(report['checks']),'window author checks PASS; native import audit still required')
if __name__=='__main__':main()
