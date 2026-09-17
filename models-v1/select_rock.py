from pathlib import Path
import json,math
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'native-rocks.json').read_text())
faces=[(i,f) for i,f in enumerate(data['faces']) if f['tree_type']=='tie' and f['geom']==0]
parent={}
def find(k):
    parent.setdefault(k,k)
    if parent[k]!=k:parent[k]=find(parent[k])
    return parent[k]
def key(p):return tuple(round(x*1000) for x in p)
for _,face in faces:
    keys=[key(v['p']) for v in face['vertices']]
    root=find(keys[0])
    for k in keys[1:]:parent[find(k)]=root
groups={}
for i,face in faces:groups.setdefault(find(key(face['vertices'][0]['p'])),[]).append(i)
records=[]
for indices in groups.values():
    points=[v['p'] for i in indices for v in data['faces'][i]['vertices']]
    lo=[min(p[a] for p in points) for a in range(3)];hi=[max(p[a] for p in points) for a in range(3)]
    centre=[(a+b)*.5 for a,b in zip(lo,hi)]
    records.append({'face_indices':indices,'triangles':len(indices),'min':lo,'max':hi,'centre':centre,
       'distance':math.dist(centre,[1998,243,-438])})
records.sort(key=lambda x:x['distance'])
(HERE/'rock-components.json').write_text(json.dumps(records))
print(json.dumps([{k:v for k,v in x.items() if k!='face_indices'} for x in records[:18]],indent=2))
