"""Read-only triangle/winding QA; run in Blender Python, no meshes authored."""
from pathlib import Path
from collections import defaultdict, Counter
import json, math, hashlib, sys, gc
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(f):return f['geom'],f['tree'],f['draw'],f['group']
def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')

def validate(level):
    source_path=HERE.parent/'architecture'/(level+'-native.json');patch_path=HERE/(level+'-patch.json')
    source_hash=sha(source_path);patch_hash=sha(patch_path)
    source=json.loads(source_path.read_text());patch=json.loads(patch_path.read_text())
    groups=defaultdict(list);triples=defaultdict(set)
    for f in source['faces']:
        groups[key(f)].append(f)
        triples[(f['geom'],f['tree'],f['material'])].add(tuple(v['color']for v in f['vertices']))
    surfaces={}
    for k,faces in groups.items():
        points=[];polys=[]
        for face in faces:
            n=len(points);points.extend(v['p']for v in face['vertices']);polys.append((n,n+1,n+2))
        surfaces[k]=(BVHTree.FromPolygons(points,polys,all_triangles=True),faces)
    counts=Counter();issues=defaultdict(list);flipped=defaultdict(lambda:Counter());minimum_area=1e50;normal_error=0;weight_error=0
    def flag(name,value):
        counts[name]+=1
        if len(issues[name])<24:issues[name].append(value)
    for fi,face in enumerate(patch['add']):
        counts['added_triangles']+=1
        k=key(face);surf,original=surfaces[k]
        vs=face['vertices'];p=[Vector(v['p'])for v in vs];cross=(p[1]-p[0]).cross(p[2]-p[0]);area=.5*cross.length
        minimum_area=min(minimum_area,area)
        if area<=1e-10:flag('zero_area',{'triangle':fi,'area_m2':area})
        if cross.length>0:cross.normalize()
        centre=(p[0]+p[1]+p[2])/3;nearest,n,index,distance=surf.find_nearest(centre)
        native=original[index];material=native['material'];instance=native['instance']
        vertex_distances=[]
        for vi,v in enumerate(vs):
            if not all(math.isfinite(x)for field in('p','uv','normal','color_weights')for x in v[field]):
                flag('nonfinite',{'triangle':fi,'vertex':vi})
            normal=Vector(v['normal']);error=abs(normal.length-1);normal_error=max(normal_error,error)
            if error>2e-5:flag('nonunit_normal',{'triangle':fi,'vertex':vi,'length':normal.length})
            if area>1e-6 and normal.dot(cross)<.98:
                flag('normal_winding_disagreement',{'triangle':fi,'vertex':vi,'dot':normal.dot(cross),'area_m2':area})
            weights=v['color_weights'];weight_error=max(weight_error,abs(sum(weights)-1))
            if len(weights)!=3 or min(weights)<-1e-4 or max(weights)>1.0001 or abs(sum(weights)-1)>2e-5:
                flag('invalid_color_weights',{'triangle':fi,'vertex':vi,'weights':weights})
            if tuple(v['color_indices'])not in triples[(face['geom'],face['tree'],material)]:
                flag('unknown_source_color_triple',{'triangle':fi,'vertex':vi,'indices':v['color_indices'],'material':material})
            if distance<.02:vertex_distances.append(surf.find_nearest(p[vi])[3])
        # Only compare close planar wall interiors. New coping return/underside
        # faces normally lie off the old shell and must not be called flips.
        if distance<.02:
            counts['centres_within_2cm']+=1
            dot=cross.dot(n)
            if dot<-.95:
                counts['opposite_close_centres']+=1
                # Some native shells intentionally duplicate opposite faces.
                # An equally close, similarly oriented native face makes the
                # nearest-face choice ambiguous, not evidence of a hard flip.
                alternatives=surf.find_nearest_range(centre,.0201)
                if any(cross.dot(nn)>.95 and dd<=distance+.001 for _,nn,_,dd in alternatives):
                    counts['native_opposite_overlap_ambiguous']+=1
                    continue
                allclose=max(vertex_distances)<.02
                fp=[Vector(v['p'])for v in native['vertices']]
                native_vertical=abs(n.y)<.35
                original_top=max(q.y for q in fp)
                away_from_top=centre.y<original_top-.50
                groupname=f'lod{face["geom"]}/tree{face["tree"]}/instance{instance}/{material}'
                if allclose and native_vertical and area>.01 and away_from_top:
                    flipped[groupname]['main_wall_triangles']+=1
                    flipped[groupname]['main_wall_area_m2']+=area
                    flag('main_planar_wall_flip',{'triangle':fi,'native_stream_index':native['stream_index'],'group':list(k),
                      'instance':instance,'material':material,'area_m2':area,'normal_dot':dot,
                      'centre_m':list(centre),'nearest_distance_m':distance,'vertex_distances_m':vertex_distances})
                elif allclose and area>.001:
                    flipped[groupname]['other_coplanar_triangles']+=1
                    flag('other_coplanar_opposite',{'triangle':fi,'group':list(k),'instance':instance,
                      'material':material,'area_m2':area,'normal_dot':dot,'native_normal_y':n.y,
                      'centre_m':list(centre),'distance_below_native_top_m':original_top-centre.y})
                else:counts['close_nonplanar_or_tiny_opposite']+=1
        if fi and fi%100000==0:print(level,fi,'triangles checked',flush=True)
    checks={'patch_source_matches_export':patch['source_fr3']==source['source_fr3'],
      'all_triangle_areas_nonzero':counts['zero_area']==0,'all_components_finite':counts['nonfinite']==0,
      'normals_unit':counts['nonunit_normal']==0,'normals_match_export_winding':counts['normal_winding_disagreement']==0,
      'color_weights_barycentric':counts['invalid_color_weights']==0,
      'color_index_triples_from_original_material_palette':counts['unknown_source_color_triple']==0,
      'no_main_planar_wall_flips':counts['main_planar_wall_flip']==0,
      'source_files_unchanged':sha(source_path)==source_hash and sha(patch_path)==patch_hash}
    result={'level':level,'status':'passed'if all(checks.values())else'failed','checks':checks,
      'source_export_sha256':source_hash,'patch_sha256':patch_hash,'counts':dict(counts),
      'minimum_triangle_area_m2':minimum_area,'maximum_normal_unit_error':normal_error,
      'maximum_color_weight_sum_error':weight_error,'issues':dict(issues),
      'opposite_groups':dict(flipped),'method':'Actual exported triangles; native BVH by geom/tree/draw/group; compare geometric winding, normals, and native palette triples.',
      'main_wall_definition':'All vertices within 2cm of original shell, centre normal dot<-0.95, original |normal.y|<0.35, area>0.01m2, centre at least0.5m below nearest native face top. Excludes an equally close (within1mm) alternative native face with matching orientation.',
      'native_visual_validation':False}
    write(HERE/(level+'-independent-validation.json'),result)
    print(json.dumps({'level':level,'status':result['status'],'counts':result['counts'],'checks':checks}),flush=True)
    return result

def main():
    results=[]
    for level in('wascitya','wascityb'):
        results.append(validate(level));gc.collect()
    report={'status':'passed'if all(r['status']=='passed'for r in results)else'failed',
      'read_only':True,'author_and_patch_not_modified':True,'levels':results}
    write(HERE/'independent-validation.json',report)
    print('FINAL',report['status'],flush=True)

if __name__=='__main__':main()
