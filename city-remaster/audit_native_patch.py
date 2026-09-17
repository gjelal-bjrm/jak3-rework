"""Read-only before/after audit of a static/wind native mesh patch.

Reports hashes and preservation of every nonselected native triangle, including
winding, material, visibility, wind instance, and original vertex/palette bytes.
It never installs or rewrites a FR3 file.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BRIDGE=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'


def sha(path):
    with path.open('rb')as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def audit(before,after,patch_path,report_path):
    before,after,patch_path,report_path=map(lambda p:Path(p).resolve(),(before,after,patch_path,report_path))
    if report_path in (before,after,patch_path):raise ValueError('Report must not overwrite input data')
    native_report=report_path.with_name(report_path.stem+'-native.json')
    subprocess.run([str(BRIDGE),'--audit-patch',str(before),str(patch_path),str(after),str(native_report)],check=True,cwd=ROOT)
    native=json.loads(native_report.read_text(encoding='utf-8'))
    # Load the large author patch only after the native audit process has exited.
    patch=json.loads(patch_path.read_text(encoding='utf-8'))
    checks={}
    before_hash,after_hash,patch_hash=sha(before),sha(after),sha(patch_path)
    checks['pinned_source']=patch['source_fr3']['sha256']==before_hash
    checks['pinned_source_size']=patch['source_fr3'].get('bytes',before.stat().st_size)==before.stat().st_size
    checks['level_identity']=native['level_identity'] and patch['level']==native['level']
    for key in ('hfrag_unchanged','collision_unchanged','merc_unchanged','index_textures_unchanged'):
        checks[key]=native[key]
    checks['all_original_textures_byte_identical']=all(t['unchanged']for t in native['textures'])
    checks['only_declared_textures_appended']=0<=native['appended_textures']<=len({t['name']for t in patch.get('new_textures',[])})
    checks['all_tfrag_byte_identical']=all(t['unchanged']for t in native['tfrag'])
    selected=defaultdict(set);wind_selected=defaultdict(set)
    for face in patch['remove']:
        key=(face.get('tree_type','tie'),face['geom'],face['tree'])
        selected[key].add(face['draw'])
        if key[0]=='tie_wind':wind_selected[key].add((face['draw'],face['group'],face['instance']))
    added=removed=unselected=0
    for tree in native['tie']:
        geom,tid=tree['geom'],tree['tree'];label=f'tie/{geom}/{tid}'
        for key in ('bvh_unchanged','packed_vertices_prefix','packed_matrix_groups_prefix','packed_matrices_unchanged',
                    'color_indices_prefix','palette_active_prefix','wind_instances_unchanged','wind_groups_unchanged'):
            checks[label+'/'+key]=tree[key]
        checks[label+'/changed_static_draws_selected']=set(tree['unmatched_original_static_draws'])<=selected['tie',geom,tid]
        checks[label+'/changed_wind_ranges_selected']={tuple(g[k]for k in ('draw','group','instance'))for g in tree['changed_wind_groups']}<=wind_selected['tie_wind',geom,tid]
        for key in ('static_triangles','wind_triangles'):
            stats=tree[key];checks[label+'/'+key+'_unselected_identical']=stats['unselected_unchanged']
            added+=stats['added'];removed+=stats['removed'];unselected+=stats['unselected_count']
    for tree in native['shrub']:
        tid=tree['tree'];label=f'shrub/{tid}'
        for key in ('palette_unchanged','packed_vertices_prefix','packed_instance_groups_prefix','packed_matrices_prefix','indices_prefix'):
            checks[label+'/'+key]=tree[key]
        checks[label+'/changed_draws_selected']=set(tree['changed_original_draws'])<=selected['shrub',0,tid]
        stats=tree['triangles'];checks[label+'/unselected_faces_identical']=stats['unselected_unchanged']
        added+=stats['added'];removed+=stats['removed'];unselected+=stats['unselected_count']
    checks['all_requested_faces_removed']=removed==len(patch['remove'])
    checks['all_requested_faces_added']=added==len(patch['add'])
    result={'status':'passed' if all(checks.values()) else 'failed','checks':checks,
            'before':str(before),'after':str(after),'patch':str(patch_path),
            'before_sha256':before_hash,'after_sha256':after_hash,'patch_sha256':patch_hash,
            'bridge_sha256':sha(BRIDGE),'native_report':str(native_report),'native_report_sha256':sha(native_report),
            'removed_faces':removed,'added_faces':added,'unselected_faces_compared':unselected,
            'native_game_validation':False}
    report_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    failures=[key for key,value in checks.items()if not value]
    print(json.dumps({'status':result['status'],'checks':len(checks),'failures':failures,
                      'removed':removed,'added':added,'preserved_triangles':unselected},indent=2))
    if failures:raise SystemExit(1)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','patch','report'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();audit(args.before,args.after,args.patch,args.report)


if __name__=='__main__':main()
