from pathlib import Path
import json,sys,math
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent;R=H.parents[2]
baseline=json.loads((R/'city-remaster/environment/architecture/wascitya-native.json').read_text())
def tree(fs):
 ps=[];tri=[]
 for f in fs:
  i=len(ps);ps.extend(Vector(v['p']) for v in f['vertices']);tri.append((i,i+1,i+2))
 return BVHTree.FromPolygons(ps,tri,all_triangles=True)
choices=[]
for region,instances in [('east',[0]),('west',[4]),('low',[58,59,60,70]),('north',[3])]:
 s=json.loads((H/f'native-{region}.json').read_text());fs=[f for f in s['faces'] if f['geom']==0]
 base=[f for f in baseline['faces'] if f['geom']==0 and f['tree']==1 and f['instance'] in instances]
 keys={(f['tree_type'],f['tree'],f['draw'],f['group']) for f in base}
 ishouse=lambda f:(f['tree_type'],f['tree'],f['draw'],f['group']) in keys
 house=[f for f in fs if ishouse(f)];alltree=tree(fs);housetree=tree(house)
 groundfs=[f for f in fs if f['tree_type']=='tfrag'];ground=tree(groundfs)
 points=[Vector(v['p']) for f in base for v in f['vertices']];center=Vector([(min(p[a] for p in points)+max(p[a] for p in points))/2 for a in range(3)])
 candidates=[]
 for f in base:
  ps=[Vector(v['p']) for v in f['vertices']];norm=(ps[1]-ps[0]).cross(ps[2]-ps[0]);area=norm.length/2
  if area<(1 if region=='round' else 5) or abs(norm.normalized().y)>.35:continue
  c=sum(ps,Vector())/3;n=Vector((norm.x,0,norm.z)).normalized()
  if (c-center).dot(n)<0:n=-n
  for step in (5,9,14):
   foot=c+n*step;foot.y=95
   groundhit=ground.ray_cast(foot,Vector((0,-1,0)),150)
   if groundhit[0] is None:continue
   gy=groundhit[0].y
   for dy in ((3.1,4.2,5.5,8,11,14) if region=='round' else (3.1,4.2,5.5)):
    outside=c+n*step;outside.y=gy+dy;hit=alltree.ray_cast(outside,-n,step+3)
    if hit[0] is None or not ishouse(fs[hit[2]]):continue
    c2=hit[0];width=3.2 if region!='round' else 2.7;height=2.8 if region!='round' else 2.5;r=Vector((n.z,0,-n.x));samplehits=[];ok=True
    for x in (-.4,0,.4):
     for y in (-.4,0,.4):
      p=c2+r*x*width+Vector((0,y*height,0));hp=alltree.ray_cast(p+n*step,-n,step+3)
      if hp[0] is None or not ishouse(fs[hp[2]]) or (hp[0]-p).length>.6:ok=False
      samplehits.append(list(hp[0]) if hp[0] is not None else None)
    if not ok:continue
    # The room behind this facade must stay clear of unrelated native objects.
    blockers=[]
    for x in (-.35,0,.35):
     for y in (-.35,0,.35):
      origin=c2+r*x*width+Vector((0,y*height,0))-n*.15
      hp=alltree.ray_cast(origin,-n,3.5)
      if hp[0] is not None and not ishouse(fs[hp[2]]):blockers.append(fs[hp[2]]['material'])
    candidates.append({'region':region,'instances':instances,'center':list(c2),'normal':list(n),'width':width,'height':height,'ground_y':gy,'camera':list(c2+n*step+Vector((0,1.7-dy,0))),'area':area,'blockers':blockers,'distance':step})
 unique={tuple(round(v,1) for v in x['center']+x['normal']):x for x in candidates}
 candidates=sorted(unique.values(),key=lambda x:(len(x['blockers']),abs(x['center'][1]-x['ground_y']-3.1),-x['area'],x['distance']))
 choices.append({'region':region,'candidates':candidates[:25]})
 print(region,len(candidates),json.dumps(candidates[:5]))
(H/'survey.json').write_text(json.dumps(choices,indent=2))
