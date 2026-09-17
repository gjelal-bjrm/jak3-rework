"""Blender BVH vertex AO candidate. No installed/root mesh is overwritten."""
from pathlib import Path
import json,struct,math,hashlib,time
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent
RAYS=128;RADIUS=.70;GAIN=.40;EDGE=.34
def sha(raw):return hashlib.sha256(raw).hexdigest()
def mid(a,b):
    r=[(x+y)*.5 for x,y in zip(a,b)];n=Vector(r[3:6]).normalized();r[3:6]=n;return tuple(r)
def split(a,b,c,out):
    ab=(Vector(a[:3])-Vector(b[:3])).length_squared
    bc=(Vector(b[:3])-Vector(c[:3])).length_squared
    ca=(Vector(c[:3])-Vector(a[:3])).length_squared
    if max(ab,bc,ca)<=EDGE*EDGE:out.extend((a,b,c));return
    if ab>=max(bc,ca):m=mid(a,b);split(a,m,c,out);split(m,b,c,out)
    elif bc>=ca:m=mid(b,c);split(a,b,m,out);split(a,m,c,out)
    else:m=mid(c,a);split(a,b,m,out);split(m,b,c,out)
def main():
    output=[]
    for layout in ('lounge','conversation'):
        started=time.time();meta=json.loads((SOURCE/(layout+'.json')).read_text());raw=(SOURCE/meta['binary']).read_bytes()
        source=list(struct.iter_unpack('<12f',raw));positions=[Vector(r[:3])for r in source]
        bvh=BVHTree.FromPolygons(positions,[tuple(range(i,i+3))for i in range(0,len(positions),3)],all_triangles=True,epsilon=0)
        expanded=[];ranges=[]
        for draw in meta['draws']:
            first=len(expanded)
            for i in range(draw['first'],draw['first']+draw['count'],3):split(*source[i:i+3],expanded)
            ranges.append(dict(draw,first=first,count=len(expanded)-first))
        hemisphere=[]
        for k in range(RAYS):
            r=math.sqrt((k+.5)/RAYS);angle=k*2.399963229728653
            hemisphere.append((r*math.cos(angle),r*math.sin(angle),math.sqrt(1-r*r)))
        cache={};factors=[];result=[]
        for row in expanded:
            key=tuple(round(x,5)for x in row[:6])
            if key not in cache:
                pos=Vector(row[:3]);normal=Vector(row[3:6]).normalized()
                tangent=normal.cross(Vector((0,1,0))if abs(normal.y)<.9 else Vector((1,0,0))).normalized()
                bitangent=normal.cross(tangent);origin=pos+normal*.0025;occlusion=0
                for x,y,z in hemisphere:
                    direction=tangent*x+bitangent*y+normal*z
                    hit,_,_,distance=bvh.ray_cast(origin,direction,RADIUS)
                    if hit is not None:occlusion+=(1-distance/RADIUS)**2
                cache[key]=1-GAIN*occlusion/RAYS
            ao=cache[key];factors.append(ao)
            result.append((*row[:8],row[8]*ao,row[9]*ao,row[10]*ao,row[11]))
        binary=b''.join(struct.pack('<12f',*r)for r in result);target=HERE/(layout+'.bin');target.write_bytes(binary)
        revised=dict(meta,vertex_count=len(result),draws=ranges,sha256=sha(binary))
        revised['vertex_ao']={'source_sha256':sha(raw),'rays':RAYS,'radius_m':RADIUS,'gain':GAIN,
          'max_triangle_edge_m':EDGE,'meaning':'static geometry contact occlusion; equal RGB multiplier; alpha and palette unchanged',
          'minimum':min(factors),'mean':sum(factors)/len(factors)}
        (HERE/(layout+'.json')).write_text(json.dumps(revised,indent=2)+'\n')
        output.append({'layout':layout,'source_sha256':sha(raw),'candidate_sha256':sha(binary),
          'source_vertices':len(source),'candidate_vertices':len(result),'unique_samples':len(cache),
          'minimum_ao':min(factors),'mean_ao':sum(factors)/len(factors),'seconds':time.time()-started})
        print(json.dumps(output[-1]),flush=True)
    (HERE/'bake-report.json').write_text(json.dumps({'status':'candidate','parameters':{'rays':RAYS,'radius_m':RADIUS,'gain':GAIN,'edge_m':EDGE},'rooms':output},indent=2)+'\n')
if __name__=='__main__':main()
