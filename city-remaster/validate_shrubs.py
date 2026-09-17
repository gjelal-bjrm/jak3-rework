"""Read-only validation of the authored shrub patch and its isolated texture."""
from pathlib import Path
import json, math, struct, hashlib
from collections import Counter

HERE = Path(__file__).resolve().parent


def native_float(p):
    return tuple(struct.unpack('<f', struct.pack('<f', n*4096))[0]/4096 for n in p)


def area_sq(a,b,c):
    u=[b[i]-a[i] for i in range(3)]; v=[c[i]-a[i] for i in range(3)]
    return sum(x*x for x in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))*.25


def main():
    native=json.loads((HERE/'market-plants-native.json').read_text())
    patch=json.loads((HERE/'market-shrubs-patch.json').read_text())
    report=json.loads((HERE/'market-shrubs-report.json').read_text())
    selected={r['instance'] for r in report['instances']}
    fields=('tree_type','geom','tree','draw','group','stream_index')
    originals={tuple(f[k] for k in fields): f for f in native['faces']
               if f['tree_type']=='shrub' and f['tree']==0 and f['instance'] in selected}
    removed={tuple(f[k] for k in fields): f for f in patch['remove']}
    assert len(selected)==69 and len(originals)==len(removed)==len(patch['remove'])==2622
    assert removed.keys()==originals.keys()
    assert patch['source_fr3']==native['source_fr3']
    for key, face in removed.items():
        assert face['original_positions']==[v['p'] for v in originals[key]['vertices']]
    assert len(patch['new_textures'])==1
    texture=patch['new_textures'][0]
    assert texture['name']=='market-shrub-orange-v1' and texture['page']=='remaster-market-plants'
    rgba=Path(texture['rgba_file']).read_bytes()
    assert len(rgba)==texture['width']*texture['height']*4
    assert set(rgba[3::4])=={128}
    palette={v['color'] for f in originals.values() for v in f['vertices']}
    edges=Counter(); directed_edges=Counter(); min_area=float('inf'); uvlo=[float('inf')]*2; uvhi=[-float('inf')]*2
    for triangle in patch['add']:
        assert triangle['tree_type']=='shrub' and triangle['geom']==0 and triangle['tree']==0
        assert triangle['draw']==9 and triangle['texture']==texture['name']
        assert len(triangle['vertices'])==3
        points=[]
        for v in triangle['vertices']:
            assert all(math.isfinite(x) for field in ('p','uv','normal','color_weights') for x in v[field])
            assert all(x in palette for x in v['color_indices'])
            assert abs(sum(v['color_weights'])-1)<1e-4 and min(v['color_weights'])>-1e-4
            assert len(v['rgba'])==3 and all(isinstance(x,int) and 0<=x<=255 for x in v['rgba'])
            for a, x in enumerate(v['uv']):
                uvlo[a]=min(uvlo[a],x);uvhi[a]=max(uvhi[a],x)
                assert 0<=x<=4096
            points.append(native_float(v['p']))
        a2=area_sq(*points);min_area=min(min_area,a2)
        assert a2>0, 'Degenerate triangle after native float conversion'
        for a,b in zip(points, points[1:]+points[:1]):
            edges[tuple(sorted((a,b)))]+=1
            directed_edges[(a,b)]+=1
    # Closed volumes remain closed after coordinates are rounded to native f32.
    assert all(count==2 for count in edges.values()), Counter(edges.values())
    assert all(directed_edges[(a,b)]==directed_edges[(b,a)] for a,b in edges)
    volumes=[]; cursor=0
    for instance in report['instances']:
        origin=instance['origin_m']; volume=0
        for triangle in patch['add'][cursor:cursor+instance['authored_triangles']]:
            a,b,c=[[v['p'][i]-origin[i] for i in range(3)] for v in triangle['vertices']]
            volume += (a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        assert volume>0, 'Closed blades face inward'
        volumes.append(volume); cursor+=instance['authored_triangles']
    assert report['max_radius_ratio']<1.04
    assert len(patch['add'])==report['added_triangles']
    result={'passed':True,'source_fr3':patch['source_fr3'],'instances':len(selected),
            'removed_triangles':len(removed),'added_triangles':len(patch['add']),
            'closed_mesh_edges':len(edges),'minimum_native_triangle_area_m2':math.sqrt(min_area),
            'outward_volume_range_m3':[min(volumes),max(volumes)],
            'uv_min':uvlo,'uv_max':uvhi,'texture_alpha':128,
            'texture_sha256':hashlib.sha256(rgba).hexdigest(),
            'max_radius_ratio':report['max_radius_ratio'],
            'native_visual_validation':'Pending root integration; no game/build/deploy performed'}
    (HERE/'market-shrubs-validation.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
