"""Derive exact visible-sand tests from native triangles, never from colour.

Collision PAT dirt is shared by the WCA sand and some hard surfaces. The table
allows only ground-01 at the foot's native ground-contact height, rejecting
other visible surfaces covering the same point. The grid only accelerates
triangle lookup; the final decision is a barycentric triangle/height test.
"""
from pathlib import Path
from collections import defaultdict,Counter
import json,math,hashlib
HERE=Path(__file__).resolve().parent
CELL=8.0;HEIGHT_TOLERANCE=.18
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def shape(f):
    a,b,c=[v['p']for v in f['vertices']]
    ux,uy,uz=[b[i]-a[i]for i in range(3)];vx,vy,vz=[c[i]-a[i]for i in range(3)]
    det=ux*vz-uz*vx;n=[uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx]
    length=math.sqrt(sum(x*x for x in n))
    if abs(det)<1e-6 or length==0 or abs(n[1])/length<.05:return None
    return [a[0],a[2],ux,uz,vx,vz,a[1],uy,vy,1/det,1.0 if f['material']=='wascity-ground-01'else 0.0]
def cells(f):
    points=[v['p']for v in f['vertices']]
    for x in range(math.floor(min(p[0]for p in points)/CELL),math.floor(max(p[0]for p in points)/CELL)+1):
        for z in range(math.floor(min(p[2]for p in points)/CELL),math.floor(max(p[2]for p in points)/CELL)+1):yield x,z
def height_at(t,x,z):
    dx=x-t[0];dz=z-t[1]
    v=(dx*t[5]-dz*t[4])*t[9];w=(t[2]*dz-t[3]*dx)*t[9]
    if v<-.00002 or w<-.00002 or v+w>1.00002:return None
    return t[6]+v*t[7]+w*t[8]
def plane_height(t,x,z):
    dx=x-t[0];dz=z-t[1]
    return t[6]+(dx*t[5]-dz*t[4])*t[9]*t[7]+(t[2]*dz-t[3]*dx)*t[9]*t[8]
def overlaps_sand_height(f,sand_face):
    ps=[v['p']for v in f['vertices']];ss=[v['p']for v in sand_face['vertices']]
    for axis in (0,2):
        if max(p[axis]for p in ps)<min(p[axis]for p in ss)or min(p[axis]for p in ps)>max(p[axis]for p in ss):return False
    if min(p[1]for p in ps)>max(p[1]for p in ss)+2*HEIGHT_TOLERANCE or max(p[1]for p in ps)<min(p[1]for p in ss)-2*HEIGHT_TOLERANCE:return False
    poly=[(p[0],p[2])for p in ps];clip=[(p[0],p[2])for p in ss]
    direction=1 if ((clip[1][0]-clip[0][0])*(clip[2][1]-clip[0][1])-(clip[1][1]-clip[0][1])*(clip[2][0]-clip[0][0]))>0 else -1
    for a,b in zip(clip,clip[1:]+clip[:1]):
        if not poly:return False
        def side(p):return direction*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        output=[];prev=poly[-1];vp=side(prev)
        for curr in poly:
            vc=side(curr)
            if (vc>=0)!=(vp>=0):
                t=vp/(vp-vc);output.append((prev[0]+t*(curr[0]-prev[0]),prev[1]+t*(curr[1]-prev[1])))
            if vc>=0:output.append(curr)
            prev=curr;vp=vc
        poly=output
    if not poly:return False
    ft,st=shape(f),shape(sand_face);diff=[plane_height(ft,*p)-plane_height(st,*p)for p in poly]
    return min(diff)<=2*HEIGHT_TOLERANCE and max(diff)>=-2*HEIGHT_TOLERANCE
def visible_at(rows,grid,p):
    x,y,z=p;ids=grid.get((math.floor(x/CELL),math.floor(z/CELL)),[]);found=False;hits=[]
    for i in ids:
        t=rows[i];h=height_at(t,x,z)
        if h is not None and abs(y-h)<=HEIGHT_TOLERANCE:
            hits.append({'height':h,'sand':bool(t[10]),'index':i})
            if t[10]==0:return False,hits
            found=True
    return found,hits
def goal_array(name,typ,values):
    chunks=[]
    for start in range(0,len(values),14):
        vals=values[start:start+14]
        chunks.append('    '+' '.join((f'{v:.9f}'if typ=='float'else str(v))for v in vals))
    return f"(define {name} (new 'static 'array {typ} {len(values)}\n"+'\n'.join(chunks)+'))\n'
def main():
    faces=[];sources=[]
    for level in ('wascitya','wascityb'):
        p=HERE/(level+'-surfaces.json');j=json.loads(p.read_text())
        sources.append({'level':level,'export':str(p),'export_sha256':sha(p),'source_fr3':j['source_fr3']})
        faces.extend(j['faces'])
    unique={}
    for f in faces:
        key=(f['material'],tuple(sorted(tuple(v['p'])for v in f['vertices'])))
        if key not in unique and shape(f) is not None:unique[key]=f
    candidates=list(unique.values());sand=[f for f in candidates if f['material']=='wascity-ground-01']
    sand_ranges={};sand_cells=defaultdict(list)
    for f in sand:
        ys=[v['p'][1]for v in f['vertices']]
        for c in cells(f):
            sand_cells[c].append(f)
            lo,hi=sand_ranges.get(c,(math.inf,-math.inf));sand_ranges[c]=(min(lo,min(ys)),max(hi,max(ys)))
    rows=[];grid=defaultdict(list);meta=[]
    for f in candidates:
        ys=[v['p'][1]for v in f['vertices']]
        occupied=[c for c in cells(f)if c in sand_ranges and min(ys)<=sand_ranges[c][1]+HEIGHT_TOLERANCE and max(ys)>=sand_ranges[c][0]-HEIGHT_TOLERANCE]
        if not occupied:continue
        if f['material']!='wascity-ground-01':
            neighbours={id(s):s for c in occupied for s in sand_cells[c]}
            if not any(overlaps_sand_height(f,s) for s in neighbours.values()):continue
        index=len(rows);rows.append(shape(f));meta.append({'material':f['material'],'tree_type':f['tree_type'],
            'tree':f['tree'],'draw':f['draw'],'stream_index':f['stream_index']})
        for c in occupied:grid[c].append(index)
    xmin=min(c[0]for c in grid);xmax=max(c[0]for c in grid);zmin=min(c[1]for c in grid);zmax=max(c[1]for c in grid)
    nx=xmax-xmin+1;nz=zmax-zmin+1;starts=[0];indices=[]
    for z in range(zmin,zmax+1):
        for x in range(xmin,xmax+1):indices.extend(grid[x,z]);starts.append(len(indices))
    # Keep coordinates near zero for single-precision barycentric evaluation.
    local=[list(t)for t in rows]
    for t in local:t[0]-=xmin*CELL;t[1]-=zmin*CELL
    text=';; REMASTER-SAND-SURFACES-BEGIN\n;; Generated by build_surface_table.py from native TFRAG/TIE triangles.\n'
    text+=f'(defconstant remaster-sand-origin-x {xmin*CELL:.1f})\n(defconstant remaster-sand-origin-z {zmin*CELL:.1f})\n'
    text+=f'(defconstant remaster-sand-grid-x {nx})\n(defconstant remaster-sand-grid-z {nz})\n'
    text+=goal_array('*remaster-sand-cell-starts*','int32',starts)
    text+=goal_array('*remaster-sand-cell-tris*','int32',indices)
    text+=goal_array('*remaster-sand-triangles*','float',[v for row in local for v in row])
    text+=';; REMASTER-SAND-SURFACES-END\n'
    (HERE/'surface-table.gc').write_text(text)
    probes=[]
    for p in [(2240.2834,7.0479,-40.7634),(2245.0,7.919,-41.0)]:
        result,hits=visible_at(rows,grid,p);assert result,(p,hits)
        probes.append({'point_m':p,'expected':True,'result':result,'hits':hits})
    # Provide native hard-surface locations adjacent to the city sand for live QA.
    hard=[]
    for f in candidates:
        if f['material'] not in ('wascitya-stone-top','wascity-cement-road'):continue
        p=[sum(v['p'][a]for v in f['vertices'])/3 for a in range(3)]
        if not 2150<p[0]<2320 or not -150<p[2]<70:continue
        result,hits=visible_at(rows,grid,p)
        if not result:hard.append({'point_m':p,'material':f['material'],'expected':False,'result':result})
    hard.sort(key=lambda r:math.dist(r['point_m'],probes[0]['point_m']));probes.extend(hard[:8])
    assert hard,'No nearby negative native probe'
    # Elevated bridge/rock levels cannot activate a buried sand triangle.
    for p in [probes[0]['point_m']]:
        raised=[p[0],p[1]+2,p[2]];result,_=visible_at(rows,grid,raised);assert not result
        probes.append({'point_m':raised,'expected':False,'result':result})
    report={'status':'passed','sources':sources,'allowed_texture':'wascity-ground-01','height_tolerance_m':HEIGHT_TOLERANCE,
        'cell_size_m':CELL,'grid_origin_m':[xmin*CELL,zmin*CELL],'grid_dimensions':[nx,nz],
        'triangles':len(rows),'sand_triangles':sum(t[10]==1 for t in rows),'cell_triangle_references':len(indices),
        'worst_cell_triangles':max(len(v)for v in grid.values()),'mean_nonempty_cell_triangles':sum(len(v)for v in grid.values())/len(grid),
        'table_sha256':sha(HERE/'surface-table.gc'),'probes':probes,'native_visual_validation':False,
        'collision_modified':False,'classification':'exact texture identity plus indexed native triangle and height; all overlapping other materials reject'}
    (HERE/'surface-table.json').write_text(json.dumps({'rows':rows,'metadata':meta,'grid':{f'{x},{z}':v for (x,z),v in grid.items()}},separators=(',',':')))
    (HERE/'surface-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ('status','triangles','sand_triangles','grid_dimensions','cell_triangle_references','worst_cell_triangles','table_sha256','probes')},indent=2))
if __name__=='__main__':main()
