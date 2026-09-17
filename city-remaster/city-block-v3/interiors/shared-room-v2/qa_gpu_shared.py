"""Actual shared-room shaders/meshes in hidden WGL; no game or live asset writes."""
from pathlib import Path
import ctypes as C
import hashlib
import importlib.util
import json
import math
import statistics
import struct
import time

HERE=Path(__file__).resolve().parent
ROOM=HERE.parent
OUT=HERE/'qa'
spec=importlib.util.spec_from_file_location('shared_room_gpu_base',ROOM/'qa_gpu.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
q.OUT=OUT


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())


def main():
    OUT.mkdir(exist_ok=True)
    g=q.Renderer(1280,960)
    checks={};assets={};textures={};outputs=[];cost=[]
    try:
        models={}
        for name,folder in [('corner-conversation',HERE),('conversing-male',q.ACTORS),('conversing-female',q.ACTORS)]:
            path=folder/(name+'.json');meta=load(path);binary=folder/meta['binary'];raw=binary.read_bytes()
            assert sha(binary)==meta.get('sha256',meta.get('binary_sha256'))
            assert all(math.isfinite(x)for row in struct.iter_unpack('<12f',raw)for x in row)
            frames=meta.get('frame_count',1);stride=meta['vertex_count']*48
            assert len(raw)==frames*stride
            buffers=[g.buffer(raw[index*stride:(index+1)*stride])for index in range(frames)]
            models[name]=(meta,buffers)
            assets[str(path)]=sha(path);assets[str(binary)]=sha(binary)
        placements=[('conversing-male',[.25,.058,-2.15],math.atan2(1.2,-.9),0.),
                    ('conversing-female',[1.45,.058,-3.05],math.atan2(-1.2,.9),0.)]
        # Both cameras reuse the same world coordinates, meshes and actor phases.
        views={'front':([.0,1.9,5.6],[.65,1.4,-2.8]),
               'side':([9.,1.9,-2.6],[.65,1.4,-2.8])}
        query=C.c_uint();q.gl('glGenQueries',None,C.c_int,C.POINTER(C.c_uint))(1,C.byref(query))
        result_fn=q.gl('glGetQueryObjectui64v',None,C.c_uint,C.c_uint,C.POINTER(C.c_uint64))

        def draw(name,offset,yaw,seconds):
            meta,buffers=models[name];count=len(buffers);phase=(seconds/meta.get('duration_seconds',5.6)%1)*count
            base=int(phase);g.attributes(buffers[base],buffers[(base+1)%count])
            g.vec3('object_offset',offset);g.vec3('object_scale',[1,1,1]);g.one('object_yaw',yaw);g.one('pose_blend',phase-base)
            for material_draw in meta['draws']:
                if count>1:
                    png=q.ACTORS/material_draw['texture'];g.texture(png)
                    g.vec3('material_color',[1,1,1]);g.one('texture_mode',3,True);g.one('roughness',.75);g.one('emissive',0,True)
                else:
                    material=meta['materials'][material_draw['material']];kind=material['texture_kind']
                    png=q.ROOT/'city-remaster'/('wood-hd-v2.png'if kind==1 else'market-cotton-hd.png');g.texture(png)
                    g.vec3('material_color',material['color']);g.one('texture_mode',kind,True)
                    g.one('roughness',material['roughness']);g.one('emissive',material['emissive'],True)
                if str(png)not in textures:textures[str(png)]=sha(png)
                q.gl('glDrawArrays',None,C.c_uint,C.c_int,C.c_int)(4,material_draw['first'],material_draw['count'])

        def frame(seconds):
            q.clear();draw('corner-conversation',[0,0,0],0,seconds)
            for name,offset,yaw,phase in placements:draw(name,offset,yaw,seconds+phase)

        for view,(eye,target)in views.items():
            q.set_camera(g,eye,target);g.vec3('room_lamp',[.55,2.8,-1.7]);g.one('room_side_light',.24)
            assert g.location('room_lamp')>=0 and g.location('room_side_light')>=0
            pictures=[]
            for index,seconds in enumerate((0.,1.4)):
                frame(seconds);file=view+'-pose-'+str(index)+'.png'
                pictures.append(g.pixels(file));outputs.append({'view':view,'seconds':seconds,'path':str(OUT/file),'sha256':sha(OUT/file)})
            change=q.difference(*pictures)
            checks[view+'_animation_changes_pixels']=change['changed_pixels']>50
            checks[view+'_nonempty_render']=len(set(pictures[0].getdata()))>500
            values=[];cpu=[]
            for iteration in range(34):
                q.gl('glFinish',None)();start=time.perf_counter()
                q.gl('glBeginQuery',None,C.c_uint,C.c_uint)(0x88BF,query.value)
                frame(iteration*.037)
                q.gl('glEndQuery',None,C.c_uint)(0x88BF)
                duration=C.c_uint64();result_fn(query.value,0x8866,C.byref(duration))
                elapsed=(time.perf_counter()-start)*1000
                if iteration>=10:values.append(duration.value/1e6);cpu.append(elapsed)
            checks[view+'_timing_finite']=all(math.isfinite(x)and x>0 for x in values+cpu)
            cost.append({'view':view,'samples':24,'warmup':10,'gpu_elapsed_median_ms':statistics.median(values),
                         'gpu_elapsed_p95_ms':sorted(values)[22],'cpu_submit_and_wait_median_ms':statistics.median(cpu),
                         'motion':change})
        checks['actual_shaders_compile_link']=True
        checks['all_geometry_finite']=True
        checks['one_room_two_fixed_actor_instances']=len(models)==3 and len(placements)==2
        checks['gl_no_errors']=q.gl('glGetError',C.c_uint)()==0
        checks['sources_assets_textures_unchanged']=all(sha(path)==expected for path,expected in {**assets,**textures,**g.sources}.items())
        report={'status':'passed'if all(checks.values())else'failed','checks':checks,'driver':g.driver,
                'shader_sha256':g.sources,'asset_sha256':assets,'texture_sha256':textures,
                'script_sha256':sha(__file__),'harness_sha256':sha(ROOM/'qa_gpu.py'),
                'room_instances':1,'actor_instances':placements,'cameras':views,'renders':outputs,
                'timing':cost,'resolution':[1280,960],'native_game_validation':False,
                'limitations':['Synthetic local views: no exterior facade; native photographs must validate the real openings.',
                    'GL_TIME_ELAPSED includes Python submission gaps; CPU figure includes submission and blocking readback. These are harness costs, not native FPS.',
                    'GPU clocks and other desktop work are uncontrolled. One room plus two inhabitants; no world, water, shadows or gameplay.']}
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2));assert report['status']=='passed'
    finally:g.close()


if __name__=='__main__':main()
