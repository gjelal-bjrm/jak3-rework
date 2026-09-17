"""Inventory connected native object surfaces without guessing object identities."""
from pathlib import Path
from collections import Counter,defaultdict
import json
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'native-objects.json').read_text())
selected=[(i,f) for i,f in enumerate(data['faces']) if f['geom']==0]
groups=defaultdict(list)
for i,f in selected:groups[(f['tree_type'],f['tree'],f['proto'])].append((i,f))
components=[]
for key,faces in groups.items():
    parent=list(range(len(faces)))
    def find(i):
        while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
        return i
    vertices={}
    for fi,(_,face) in enumerate(faces):
        for v in face['vertices']:
            p=tuple(round(x*1000) for x in v['p'])
            if p in vertices:parent[find(fi)]=find(vertices[p])
            else:vertices[p]=fi
    connected=defaultdict(list)
    for fi,face in enumerate(faces):connected[find(fi)].append(face)
    for items in connected.values():
        points=[v['p'] for _,f in items for v in f['vertices']]
        low=[min(p[a] for p in points) for a in range(3)]
        high=[max(p[a] for p in points) for a in range(3)]
        components.append({'tree_type':key[0],'tree':key[1],'proto':key[2],
            'min':low,'max':high,'centre':[(a+b)/2 for a,b in zip(low,high)],
            'triangles':len(items),'materials':dict(Counter(f['material'] for _,f in items)),
            'face_indices':[i for i,_ in items]})
components.sort(key=lambda c:(c['tree_type'],c['proto'],c['centre']))
for i,c in enumerate(components):c['id']=i
(HERE/'object-components.json').write_text(json.dumps(components))
summary=[]
for key,faces in groups.items():
    chunks=[c for c in components if (c['tree_type'],c['tree'],c['proto'])==key]
    summary.append({'tree_type':key[0],'tree':key[1],'proto':key[2],
        'triangles':len(faces),'components':len(chunks),
        'materials':dict(Counter(f['material'] for _,f in faces)),
        'largest':[{'id':c['id'],'triangles':c['triangles'],'centre':c['centre'],'extent':[b-a for a,b in zip(c['min'],c['max'])]} for c in sorted(chunks,key=lambda c:-c['triangles'])[:8]]})
(HERE/'object-inventory.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
