"""Compare vertex AO candidate and untouched room meshes through real shaders."""
from pathlib import Path
import importlib.util,json,math,hashlib
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('interior_gpu',HERE.parent/'qa_gpu.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
q.OUT=HERE/'qa';q.OUT.mkdir(exist_ok=True)
def main():
    g=q.Renderer();reports=[]
    try:
        actors={}
        for name in ('sitting-male','conversing-male','conversing-female'):
            meta=json.loads((q.ACTORS/(name+'.json')).read_text());raw=(q.ACTORS/meta['binary']).read_bytes();s=meta['frame_stride_bytes']
            actors[name]=(meta,[g.buffer(raw[:s]),g.buffer(raw[s:2*s])])
        q.set_camera(g,[0,1.9,5.4],[0,1.35,-1.8])
        for layout in ('lounge','conversation'):
            images=[]
            for state,folder in [('before',HERE.parent),('ao',HERE)]:
                meta=json.loads((folder/(layout+'.json')).read_text());raw=(folder/meta['binary']).read_bytes();assert q.sha(raw)==meta['sha256']
                buffer=g.buffer(raw);q.clear();q.mesh_object(g,meta,folder,(buffer,buffer))
                placements=[('sitting-male',(0,.09,-2.5),0)]if layout=='lounge'else[
                    ('conversing-male',(-.58,.058,-1.6),math.radians(60)),('conversing-female',(.58,.058,-1.6),math.radians(-60))]
                for name,offset,yaw in placements:
                    actor,buffers=actors[name];q.mesh_object(g,actor,q.ACTORS,buffers,offset,yaw,0,True)
                images.append(g.pixels(layout+'-'+state+'.png'))
            reports.append({'layout':layout,**q.difference(*images)})
        (HERE/'gpu-comparison.json').write_text(json.dumps({'status':'rendered','driver':g.driver,'shader_sha256':g.sources,'rooms':reports,'native_game_validation':False},indent=2)+'\n')
        print(json.dumps(reports,indent=2))
    finally:g.close()
if __name__=='__main__':main()
