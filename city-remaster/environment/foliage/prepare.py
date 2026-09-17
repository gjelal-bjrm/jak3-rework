"""Select the thirteen remaining WCB palm instances from an immutable snapshot.

Read-only native export: no live file, model author or earlier stage is modified.
The two previously remastered market palms remain outside this patch.
"""
import hashlib, json, sys, subprocess
from pathlib import Path
from collections import defaultdict, Counter

HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parent
sys.path.insert(0,str(CITY))
from prepare_market_plants import identity, source_id, distance_to_triangle, geometry
BASE=CITY/'staging/market-static-003/wascityb.fr3'
BASE_SHA='de7ab0fd18e6f6400da5738c5a3b8446c7fb1b567baebde68e45132bb9faae1f'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,j):p.write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
def spatial_matrix(i):
    return tuple(v for column in i['matrix_columns'] for v in column[:3])

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    assert sha(BASE)==BASE_SHA,'Immutable native base changed'
    old_path=CITY/'all-plants-native.json';old=json.loads(old_path.read_text())
    old_groups=defaultdict(list)
    for f in old['faces']:old_groups[identity(f)].append(f)
    selected=sorted(k for k in old_groups if
        (k[0]=='tie' and k[3] not in (486,487)) or
        (k[0]=='tie_wind' and k[3] not in (*range(6),*range(45,53))))
    assert len(selected)==13*8*4
    selection={'level':'wascityb','source_fr3':{'path':str(BASE),'sha256':BASE_SHA,'bytes':BASE.stat().st_size},
        'tree_types':['tie','tie_wind'],
        'materials':['wascity-palm-trunk','wascity-palm-leaf-worn','wascity-palm-beard'],
        'instances':[source_id(k) for k in selected],
        'label':'WCB complete remaining palms; preserve accepted market palms 486/487'}
    write(HERE/'selection.json',selection)
    subprocess.run([sys.executable,str(CITY/'export_block.py'),'--selection',str(HERE/'selection.json'),
        '--output',str(HERE/'native.json')],check=True,cwd=ROOT,stdout=subprocess.DEVNULL)
    native=json.loads((HERE/'native.json').read_text());groups=defaultdict(list)
    for f in native['faces']:groups[identity(f)].append(f)
    assert set(groups)==set(selected),'Incomplete selected export'
    # Draw numbers may change after material insertion. Geometry and instance
    # identities must still agree with the original complete export.
    for k,fs in groups.items():
        assert Counter(tuple(tuple(v['p']) for v in f['vertices']) for f in fs)==Counter(
            tuple(tuple(v['p']) for v in f['vertices']) for f in old_groups[k]),k
    inv={identity(i):i for i in native['instance_inventory']}
    trunks={k:fs for k,fs in groups.items() if k[0]=='tie' and k[1]==0}
    coincident=defaultdict(list)
    for k in trunks:coincident[spatial_matrix(inv[k])].append(k)
    trunk_sets=[sorted(v) for v in coincident.values()]
    attached=defaultdict(list);distances={};aliases={}
    winds=defaultdict(list)
    for k in groups:
        if k[0]=='tie_wind' and k[1]==0:
            winds[(groups[k][0]['material'],spatial_matrix(inv[k]))].append(k)
    for _,wind_keys in sorted(winds.items()):
        wind_keys.sort();p=inv[wind_keys[0]]['origin_m']
        candidates=sorted((min(distance_to_triangle(p,*[v['p'] for v in f['vertices']])
            for f in trunks[ts[0]]),ts) for ts in trunk_sets)
        distance,ts=candidates[0];assert distance<2 and candidates[1][0]-distance>.5
        assert len(wind_keys)==len(ts),'Native duplicate topology differs from duplicate crowns'
        for rank,w in enumerate(wind_keys):
            attached[ts[rank]].append(w);aliases[str(w[3])]=wind_keys[0][3]
            distances[w]={'distance_to_indexed_trunk_m':distance,'next_distinct_trunk_distance_m':candidates[1][0]}
    palms=[]
    for trunk in sorted(trunks):
        parts=[trunk,*sorted(attached[trunk])]
        assert Counter(groups[k][0]['material'] for k in parts[1:])=={'wascity-palm-leaf-worn':3,'wascity-palm-beard':4}
        lods=[k for k in selected if any(k[0]==p[0] and k[2:]==p[2:] for p in parts)]
        for k in lods:assert inv[k]['matrix_columns']==inv[(k[0],0,k[2],k[3])]['matrix_columns']
        faces=[f for k in parts for f in groups[k]]
        palms.append({'id':f'wascityb/tie/tree-{trunk[2]}/trunk-{trunk[3]}',
            'trunk_source':source_id(trunk),'trunk_origin_m':inv[trunk]['origin_m'],
            'parts_geom0':[dict(source_id(k),material=groups[k][0]['material'],origin_m=inv[k]['origin_m'],**distances.get(k,{})) for k in parts],
            'all_lod_source_ids':[source_id(k) for k in lods],**geometry(faces)})
    report={'status':'complete targeted export; no live mutation','source_fr3':selection['source_fr3'],
        'native_export_sha256':sha(HERE/'native.json'),'original_export_sha256':sha(old_path),
        'palms':palms,'palms_instances':len(palms),'distinct_positions':len(trunk_sets),
        'preserved_market_trunks':[486,487],'preserved_market_wind':[0,1,2,3,4,5,45,46,47,48,49,50,51,52],
        'coincident_native_trunk_groups':[[k[3] for k in ts] for ts in trunk_sets if len(ts)>1],
        'wind_geometry_seed_aliases':aliases,
        'duplicate_policy':'Preserve every native identity, matrix and visibility group; spatially coincident wind components share deterministic geometry seeds.',
        'checks':{'all_13_palms_complete':len(palms)==13,'original_positions_identical':True,
            'all_lod_matrices_identical':True,'market_excluded':True,'source_unchanged':sha(BASE)==BASE_SHA}}
    write(HERE/'map.json',report)
    print(json.dumps({k:report[k] for k in ('palms_instances','distinct_positions','coincident_native_trunk_groups','checks')},indent=2))

if __name__=='__main__':main()
