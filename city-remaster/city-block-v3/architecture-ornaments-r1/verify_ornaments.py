from pathlib import Path
from collections import defaultdict,Counter
import json,math,hashlib,sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree
H=Path(__file__).resolve().parent
p=json.loads((H/'wascitya-patch.json').read_text());s=json.loads((H/'native.json').read_text());groups=defaultdict(list)
for f in p['add']:groups[f['geom']].append(f)
report={'status':'passed','patch_sha256':hashlib.sha256((H/'wascitya-patch.json').read_bytes()).hexdigest(),'lods':[],'checks':{}}
for lod,fs in groups.items():
 ps=[];tri=[];seen={};edges=Counter()
 for f in fs:
  ids=[]
  for v in f['vertices']:
   k=tuple(v['p'])
   if k not in seen:seen[k]=len(ps);ps.append(Vector(k))
   ids.append(seen[k])
  tri.append(ids)
  for i in range(3):edges[tuple(sorted((ids[i],ids[(i+1)%3])))]+=1
 adj=defaultdict(set)
 for (a,b),count in edges.items():adj[a].add(b);adj[b].add(a)
 un=set(range(len(ps)));parts=[]
 while un:
  root=un.pop();part={root};todo=[root]
  while todo:
   for n in adj[todo.pop()]:
    if n in un:un.remove(n);part.add(n);todo.append(n)
  parts.append(part)
 volumes=[]
 for part in parts:
  o=ps[next(iter(part))];volume=0
  for a,b,c in tri:
   if a in part:volume+=(ps[a]-o).dot((ps[b]-o).cross(ps[c]-o))/6
  volumes.append(volume)
 wallfs=[f for f in s['faces'] if f['geom']==lod and f['tree_type']=='tie' and f['tree']==1 and f['group']==2 and 'stucco' in f['material']]
 wp=[];wt=[]
 for f in wallfs:
  i=len(wp);wp.extend(Vector(v['p']) for v in f['vertices']);wt.append((i,i+1,i+2))
 bvh=BVHTree.FromPolygons(wp,wt,all_triangles=True)
 minimum=1e9;maximum=-1e9
 for v in ps:
  q,n,i,d=bvh.find_nearest(v);signed=(v-q).dot(n);minimum=min(minimum,signed);maximum=max(maximum,signed)
 checks={'seven_closed_components':len(parts)==7,'every_edge_two_faces':all(n==2 for n in edges.values()),'positive_component_volumes':min(volumes)>0,'no_vertices_buried_in_wall':minimum>=-.004}
 report['checks'].update({str(lod)+'/'+k:v for k,v in checks.items()});report['lods'].append({'lod':lod,'components':len(parts),'vertices':len(ps),'triangles':len(fs),'volumes_m3':volumes,'minimum_wall_clearance_m':minimum,'maximum_wall_clearance_m':maximum})
report['status']='passed' if all(report['checks'].values()) else 'failed'
(H/'ornament-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if report['status']!='passed':raise SystemExit(1)
