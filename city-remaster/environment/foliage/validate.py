"""Independent geometry/identity checks before native import; writes only a report."""
import hashlib,json,math
from pathlib import Path
from collections import defaultdict,Counter
HERE=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def key(f):return tuple(f[k]for k in ('tree_type','geom','tree','draw','group','stream_index','instance'))
def component(f):return tuple(f[k]for k in ('tree_type','geom','tree','instance'))
def group(f):return tuple(f[k]for k in ('tree_type','geom','tree','draw','group','instance'))
def norm(v):return math.sqrt(sum(x*x for x in v))
def main():
    native=json.loads((HERE/'native.json').read_text());patch=json.loads((HERE/'patch.json').read_text())
    mapping=json.loads((HERE/'map.json').read_text());report=json.loads((HERE/'report.json').read_text())
    originals={key(f):f for f in native['faces']};removed={key(f):f for f in patch['remove']}
    checks={'source_pinned':sha(HERE/'native.json')==report['source_sha256']==mapping['native_export_sha256'],
        'patch_pinned':sha(HERE/'patch.json')==report['patch_sha256'],
        'reviewed_author_pinned':sha(Path(report['reviewed_author']))==report['reviewed_author_sha256'],
        'all_and_only_remaining_palms_removed':set(originals)==set(removed)and len(originals)==len(patch['remove'])==20384,
        'removal_positions_exact':all(removed[k]['original_positions']==[v['p']for v in f['vertices']]for k,f in originals.items()),
        'preserve_bvh_requested':patch['preserve_bvh'] is True}
    colors=defaultdict(set);materials={};groups={group(f)for f in native['faces']}
    for f in native['faces']:colors[component(f)].update(v['color']for v in f['vertices']);materials[component(f)]=f['material']
    checks.update({k:True for k in ('all_added_groups_selected','finite_vertex_values','unit_normals','native_palette_weights','triangles_nondegenerate','dedicated_textures_exactly_scoped')})
    counts=Counter();min_area=math.inf;max_ne=max_we=0;vertices_by_component=defaultdict(set)
    for f in patch['add']:
        comp=component(f);counts[comp]+=1;checks['all_added_groups_selected']&=group(f)in groups
        expected='market-palm-trunk-v1' if materials[comp]=='wascity-palm-trunk' else 'market-palm-leaf-v1' if materials[comp]=='wascity-palm-leaf-worn' else None
        checks['dedicated_textures_exactly_scoped']&=f.get('texture')==expected
        for v in f['vertices']:
            checks['finite_vertex_values']&=all(math.isfinite(x)for name in ('p','normal','uv','color_weights')for x in v[name])
            ne=abs(norm(v['normal'])-1);we=abs(sum(v['color_weights'])-1);max_ne=max(ne,max_ne);max_we=max(we,max_we)
            checks['unit_normals']&=ne<.001
            checks['native_palette_weights']&=we<1e-5 and min(v['color_weights'])>=0 and max(v['color_weights'])<=1 and set(v['color_indices'])<=colors[comp]
            # Spatial duplicates must retain the same modeled silhouette.
            vertices_by_component[comp].add(tuple(v['p']))
        a,b,c=[v['p']for v in f['vertices']];u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
        area=norm([u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]])/2
        min_area=min(min_area,area);checks['triangles_nondegenerate']&=area>1e-9
    checks['all_416_component_lods_rebuilt']=set(counts)==set(colors)and len(counts)==416
    checks['market_palms_untouched']=all(k[3]not in ((486,487)if k[0]=='tie'else (0,1,2,3,4,5,45,46,47,48,49,50,51,52))for k in counts)
    checks['decreasing_lods']=all(report['triangles_by_lod'][str(i)]>report['triangles_by_lod'][str(i+1)]for i in range(3))
    checks['lod0_budget']=report['triangles_by_lod']['0']<=13*12300
    inv={(i['tree_type'],i['instance'],i['geom']):i for i in native['instance_inventory']}
    checks['anchors_matrices_wind_unchanged']=all(a['matrix_columns']==inv[a['kind'],a['instance'],a['lod']]['matrix_columns']and a['wind_index']==inv[a['kind'],a['instance'],a['lod']].get('wind_index')and a['stiffness']==inv[a['kind'],a['instance'],a['lod']].get('stiffness')for a in report['assets'])
    checks['coincident_wind_silhouettes_equal']=all(vertices_by_component['tie_wind',lod,1,int(inst)]==vertices_by_component['tie_wind',lod,1,seed]for inst,seed in mapping['wind_geometry_seed_aliases'].items()for lod in range(4))
    checks['coincident_trunk_silhouettes_equal']=all(vertices_by_component['tie',lod,1,pair[0]]==vertices_by_component['tie',lod,1,pair[1]]for pair in mapping['coincident_native_trunk_groups']for lod in range(4))
    checks['approved_texture_pixels_unchanged']=all(sha(Path(t['rgba_file']))==t['sha256'] and Path(t['rgba_file']).stat().st_size==t['width']*t['height']*4 for t in report['textures'])
    result={'status':'passed'if all(checks.values())else 'FAILED','checks':checks,'patch_sha256':sha(HERE/'patch.json'),
        'triangles_by_lod':report['triangles_by_lod'],'max_normal_error':max_ne,'max_weight_error':max_we,'min_area_m2':min_area,
        'native_visual_validation':False,'live_files_written':False}
    (HERE/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert all(checks.values())
if __name__=='__main__':main()
