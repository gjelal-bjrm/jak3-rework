"""Independent checks of authored market-palm patch; no live level mutation."""
import hashlib,json,math
from pathlib import Path
from collections import defaultdict

HERE=Path(__file__).resolve().parent;CITY=HERE.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','group','stream_index','instance'))
def group(f):return tuple(f[k] for k in ('tree_type','geom','tree','draw','group','instance'))
def component(f):return tuple(f[k] for k in ('tree_type','geom','tree','instance'))
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

def main():
    native=json.loads((CITY/'market-plants-native.json').read_text())
    patch=json.loads((HERE/'palms-patch.json').read_text())
    report=json.loads((HERE/'palms-report.json').read_text())
    originals=[f for f in native['faces'] if f['tree_type'] in ('tie','tie_wind')]
    source={key(f):f for f in originals};removed={key(f):f for f in patch['remove']}
    checks={}
    checks['source_snapshot_hash_matches']=sha(CITY/'market-plants-native.json')==report['source_sha256']
    checks['all_and_only_complete_two_palms_removed']=set(source)==set(removed) and len(source)==len(originals)==len(patch['remove'])==3136
    checks['remove_positions_match_source']=all(removed[k]['original_positions']==[v['p'] for v in f['vertices']] for k,f in source.items())
    source_colors=defaultdict(set)
    for f in originals:source_colors[component(f)].update(v['color'] for v in f['vertices'])
    source_groups={group(f) for f in originals}
    checks['only_selected_native_groups_added']=all(group(f) in source_groups for f in patch['add'])
    checks['finite_vertex_data']=True;checks['unit_world_normals']=True;checks['native_color_weights_valid']=True;checks['triangles_nondegenerate']=True
    min_area=float('inf');normal_error=0;weight_error=0
    counts=defaultdict(int)
    for f in patch['add']:
        counts[(f['tree_type'],f['geom'],f['instance'])]+=1
        for v in f['vertices']:
            values=v['p']+v['normal']+v['uv']+v['color_weights']
            checks['finite_vertex_data'] &= all(math.isfinite(x) for x in values)
            e=abs(math.sqrt(dot(v['normal'],v['normal']))-1);normal_error=max(e,normal_error)
            checks['unit_world_normals'] &= e<.001
            w=v['color_weights'];weight_error=max(weight_error,abs(sum(w)-1))
            # Color indices address the tree palette, not an individual draw.
            # A vertex may interpolate across adjacent native draws of the same
            # component; it must never borrow colors from a different instance.
            checks['native_color_weights_valid'] &= len(w)==3 and abs(sum(w)-1)<1e-5 and min(w)>=0 and max(w)<=1 and set(v['color_indices'])<=source_colors[component(f)]
        a,b,c=[v['p'] for v in f['vertices']];n=cross(sub(b,a),sub(c,a));area=math.sqrt(dot(n,n))*.5
        min_area=min(area,min_area);checks['triangles_nondegenerate'] &= area>1e-9
    expected={(f['tree_type'],f['geom'],f['instance']) for f in originals}
    checks['all_64_component_lod_groups_reconstructed']=set(counts)==expected and len(expected)==64
    checks['decreasing_lod_budget']=all(int(report['triangles_by_lod'][str(i)])>int(report['triangles_by_lod'][str(i+1)]) for i in range(3))
    checks['lod0_below_30000_triangles']=sum(n for (typ,lod,inst),n in counts.items() if lod==0)<30000
    inv={(i['tree_type'],i['instance'],i['geom']):i for i in native['instance_inventory']}
    checks['native_anchor_matrix_wind_metadata_preserved']=all(a['matrix_columns']==inv[(a['kind'],a['instance'],a['lod'])]['matrix_columns'] and a['wind_index']==inv[(a['kind'],a['instance'],a['lod'])].get('wind_index') and a['stiffness']==inv[(a['kind'],a['instance'],a['lod'])].get('stiffness') for a in report['assets'])
    textures={t['name']:t for t in patch['new_textures']};checks['dedicated_textures_present']=set(textures)=={'market-palm-leaf-v1','market-palm-trunk-v1'}
    checks['texture_bytes_and_sizes_valid']=all(Path(t['rgba_file']).stat().st_size==t['width']*t['height']*4 for t in textures.values())
    checks['only_authored_green_blades_use_tissue']=all(f.get('texture')=='market-palm-leaf-v1' for f in patch['add'] if f['tree_type']=='tie_wind' and f['instance'] in range(6))
    checks['only_authored_trunks_use_bark']=all(f.get('texture')=='market-palm-trunk-v1' for f in patch['add'] if f['tree_type']=='tie')
    checks['native_beard_atlas_unreplaced']=all('texture' not in f for f in patch['add'] if f['tree_type']=='tie_wind' and f['instance']>=45)
    out={'status':'passed' if all(checks.values()) else 'FAILED','checks':checks,'max_normal_length_error':normal_error,'max_color_weight_sum_error':weight_error,'minimum_triangle_area_m2':min_area,'triangles_by_lod':report['triangles_by_lod'],'patch_sha256':sha(HERE/'palms-patch.json'),'textures':[{**t,'sha256':sha(Path(t['rgba_file']))} for t in textures.values()],'native_visual_validation':False,'limitation':'Blender preview and structural checks only. Bridge round trip, in-game wind, culling, colour and GPU normal use need native validation.'}
    (HERE/'validation.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));assert all(checks.values())
if __name__=='__main__':main()
