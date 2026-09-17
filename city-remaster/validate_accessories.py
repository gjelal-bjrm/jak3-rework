"""Read-only native-contract validation for the five market accessories."""
import json, math
from pathlib import Path
from import_market import Glb, validate_model
HERE=Path(__file__).resolve().parent
NAMES=['market-crate-lod0','market-basket-a-lod0','market-basket-b-lod0','market-sack-a-lod0','market-sack-b-lod0']
reports=[]
for name in NAMES:
    path=HERE/(name+'.glb');report=validate_model(path);g=Glb(path)
    source=report['source']['bounds_metres_y_up'];current=report['authored']['bounds_metres_y_up']
    bounds_error=max(abs(a-b) for aa,bb in zip(source,current) for a,b in zip(aa,bb))
    assert bounds_error<.00001,(name,'Indexed bounds drift',bounds_error)
    assert all(max(m['image_size'])>=1024 for m in report['authored']['materials']),(name,'Non-HD material')
    unreferenced=0;degenerate=0;normal_error=0.
    for mesh in g.g['meshes']:
        for prim in mesh['primitives']:
            pos=g.values(prim['attributes']['POSITION']);idx=[v[0] for v in g.values(prim['indices'])]
            normals=g.values(prim['attributes']['NORMAL'])
            unreferenced+=len(pos)-len(set(idx))
            normal_error=max(normal_error,max(abs(math.sqrt(sum(x*x for x in n))-1) for n in normals))
            for i in range(0,len(idx),3):
                p,q,r=[pos[j] for j in idx[i:i+3]];a=[q[j]-p[j] for j in range(3)];b=[r[j]-p[j] for j in range(3)]
                cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
                if sum(v*v for v in cross)<1e-20:degenerate+=1
    assert not unreferenced,(name,'Unused helper vertices',unreferenced)
    assert not degenerate,(name,'Zero-area triangles',degenerate)
    assert normal_error<.0001,(name,'Non-unit normals',normal_error)
    report['additional_geometry_checks']={'bounds_max_error_m':bounds_error,'unused_helper_vertices':unreferenced,'zero_area_triangles':degenerate,'maximum_unit_normal_error':normal_error,'all_embedded_materials_hd':True}
    reports.append(report)
(HERE/'accessories-import-validation.json').write_text(json.dumps({'passed':True,'models':reports,'native_visual_validation':False},indent=2))
print(json.dumps([{'control':r['control'],'triangles':r['authored']['triangles'],'materials':len(r['authored']['materials']),'bounds_error_m':r['additional_geometry_checks']['bounds_max_error_m']} for r in reports],indent=2))
