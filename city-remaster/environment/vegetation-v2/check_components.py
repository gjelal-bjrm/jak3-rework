import bpy,collections
from pathlib import Path
p=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(p/'wascitya-sample-plants.blend'))
o=next(o for o in bpy.data.objects if o.get('type')=='cactus');m=o.data;m.calc_loop_triangles()
parent=list(range(len(m.vertices)))
def find(v):
 while parent[v]!=v:v=parent[v]
 return v
for f in m.polygons:
 for v in f.vertices:parent[find(v)]=find(f.vertices[0])
parts=collections.defaultdict(list)
for t in m.loop_triangles:parts[find(t.vertices[0])].append(t)
out=collections.Counter()
for ts in parts.values():
 vol=sum(m.vertices[t.vertices[0]].co.dot(m.vertices[t.vertices[1]].co.cross(m.vertices[t.vertices[2]].co))/6 for t in ts)
 out[(len(ts),ts[0].material_index,'positive' if vol>0 else 'negative')]+=1
print('COMPONENTS',len(parts),out)
