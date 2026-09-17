"""Bounded room-only GPU comparison, with identical draw counts/materials."""
from pathlib import Path
import ctypes as C,json,statistics,importlib.util,hashlib
HERE=Path(__file__).resolve().parent;ROOM=HERE.parent
spec=importlib.util.spec_from_file_location('interior_qa',ROOM/'qa_gpu.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class Api(C.Structure):
    _fields_=[(n,C.c_void_p)for n in ('begin_query','end_query','bind_vertex_array','bind_texture','uniform1i','uniform1f','uniform3f','draw_arrays')]
class Locations(C.Structure):
    _fields_=[(n,C.c_int)for n in ('offset','color','mode','roughness','emissive')]
class Draw(C.Structure):
    _fields_=[('vao',C.c_uint),('texture',C.c_uint),('first',C.c_int),('count',C.c_int),('mode',C.c_int),('emissive',C.c_int),
              ('roughness',C.c_float),('color',C.c_float*3),('offset',C.c_float*3)]
def distribution(values):
    s=sorted(values)
    return {'median_ms':statistics.median(s),'p95_ms':s[int(.95*(len(s)-1))],'min_ms':min(s),'max_ms':max(s)}
def main():
    g=q.Renderer(1920,1080)
    try:
        names=('glBeginQuery','glEndQuery','glBindVertexArray','glBindTexture','glUniform1i','glUniform1f','glUniform3f','glDrawArrays')
        api=Api(*[C.cast(q.gl(n,None),C.c_void_p).value for n in names])
        loc=Locations(*[g.location(n)for n in ('object_offset','material_color','texture_mode','roughness','emissive')])
        lib=C.CDLL(str(HERE/'benchmark_submit.dll'));submit=lib.submit
        submit.argtypes=[C.POINTER(Api),C.POINTER(Locations),C.POINTER(Draw),C.c_int,C.c_uint]
        models={};assets={}
        for version,folder in [('before',ROOM/'no-ao'),('ao',ROOM)]:
            for layout in ('lounge','conversation'):
                meta=json.loads((folder/(layout+'.json')).read_text());raw=(folder/meta['binary']).read_bytes();assert q.sha(raw)==meta['sha256']
                assets[str(folder/meta['binary'])]=q.sha(raw)
                vao=C.c_uint();q.gl('glGenVertexArrays',None,C.c_int,C.POINTER(C.c_uint))(1,C.byref(vao));q.gl('glBindVertexArray',None,C.c_uint)(vao)
                vbo=g.buffer(raw);g.attributes(vbo,vbo);models[(version,layout)]=(meta,vao.value)
        textures={}
        for kind in (0,1,2):
            path=q.ROOT/'city-remaster'/('support-wood-hd.png'if kind==1 else'market-cotton-hd.png')
            g.texture(path);textures[kind]=g.cache[str(path)].value
        query=C.c_uint();q.gl('glGenQueries',None,C.c_int,C.POINTER(C.c_uint))(1,C.byref(query))
        result_fn=q.gl('glGetQueryObjectui64v',None,C.c_uint,C.c_uint,C.POINTER(C.c_uint64))
        g.vec3('object_scale',[1,1,1]);g.one('object_yaw',0);g.one('pose_blend',0)
        output=[]
        for room_count in (2,5):
            q.set_camera(g,[0,2.1,10 if room_count==2 else 23],[0,1.5,-1.8])
            commands={};counts={}
            for version in ('before','ao'):
                rows=[];vertices=0
                for index in range(room_count):
                    layout='lounge'if index%2==0 else'conversation';meta,vao=models[(version,layout)]
                    vertices+=meta['vertex_count'];offset=((index-(room_count-1)/2)*4.65,0,0)
                    for draw in meta['draws']:
                        material=meta['materials'][draw['material']];kind=material['texture_kind']
                        rows.append(Draw(vao,textures[kind],draw['first'],draw['count'],kind,material['emissive'],
                                         material['roughness'],(C.c_float*3)(*material['color']),(C.c_float*3)(*offset)))
                commands[version]=(Draw*len(rows))(*rows);counts[version]={'vertices':vertices,'draws':len(rows)}
            samples={'before':[],'ao':[]}
            for frame in range(100):
                # Alternate ordering as well as versions to limit clock/order bias.
                for version in (('before','ao')if frame%2==0 else('ao','before')):
                    q.clear();draws=commands[version];submit(C.byref(api),C.byref(loc),draws,len(draws),query.value)
                    duration=C.c_uint64();result_fn(query.value,0x8866,C.byref(duration))
                    if frame>=40:samples[version].append(duration.value/1e6)
            row={'rooms_visible':room_count,'warmup_frames_per_variant':40,'timed_frames_per_variant':60,
                 'before':dict(distribution(samples['before']),**counts['before']),
                 'ao':dict(distribution(samples['ao']),**counts['ao'])}
            row['median_added_ms']=row['ao']['median_ms']-row['before']['median_ms'];output.append(row)
        error=q.gl('glGetError',C.c_uint)();assert not error,hex(error)
        report={'status':'measured','driver':g.driver,'resolution':[1920,1080],'msaa_samples':1,'timer':'GL_TIME_ELAPSED uint64 nanoseconds',
                'submission':'Native C++ loop, identical material/state/draw count per version; Python outside timed region',
                'scope':'Rooms only, actual city interior shaders and original/AO room binaries. No actors, exterior geometry, water or game simulation.',
                'results':output,'asset_sha256':assets,'shader_sha256':g.sources,
                'limitations':['Offscreen synthetic camera; rooms arranged side by side, fully visible.','Not a whole-game frame-time or FPS benchmark.','No GPU scheduling/clock lock; median and p95 reported, versions interleaved.','Texture upload, level loading and CPU submission costs excluded; MSAA disabled.']}
        (HERE/'gpu-cost.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:g.close()
if __name__=='__main__':main()
