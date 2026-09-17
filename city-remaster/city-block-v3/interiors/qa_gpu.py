"""Read-only WGL render of the real city interior shaders and exported meshes.

No visible window, game launch, runtime mutation or keyboard/controller input.
Only interiors/qa contains outputs. Use the bundled Python with Pillow.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json,math,struct,hashlib,importlib.util
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ACTORS=HERE.parent/'inhabitants'
OUT=HERE/'qa'
spec=importlib.util.spec_from_file_location('wgl_common',ROOT/'city-remaster/grass-contact/verify_gpu.py')
wgl=importlib.util.module_from_spec(spec);spec.loader.exec_module(wgl)
gl=wgl.gl
u=C.c_uint;i=C.c_int;p=C.c_void_p;f=C.c_float;size=C.c_ssize_t
def sha(raw):return hashlib.sha256(raw).hexdigest()
def norm(a):
    d=math.sqrt(sum(x*x for x in a));return[x/d for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def mul(a,b):return[[sum(a[r][k]*b[k][c]for k in range(4))for c in range(4)]for r in range(4)]
def camera(eye,target,aspect):
    forward=norm([a-b for a,b in zip(target,eye)]);right=norm(cross(forward,[0,1,0]));up=cross(right,forward)
    view=[right+[-dot(right,eye)],up+[-dot(up,eye)],[-x for x in forward]+[dot(forward,eye)],[0,0,0,1]]
    q=1/math.tan(math.radians(43)/2);near=.1;far=100
    proj=[[q/aspect,0,0,0],[0,q,0,0],[0,0,(far+near)/(near-far),2*far*near/(near-far)],[0,0,-1,0]]
    return mul(proj,view)
def packed_matrix(a):return(f*16)(*[a[r][c]for c in range(4)for r in range(4)])

class Renderer:
    def __init__(self,width=1000,height=1000):
        self.width=width;self.height=height;self.cache={};self.sources={}
        self.hwnd=wgl.user.CreateWindowExW(0,'STATIC','Interior shader offscreen QA',0,0,0,16,16,None,None,None,None)
        assert self.hwnd;self.dc=wgl.user.GetDC(self.hwnd)
        pfd=wgl.PFD();pfd.size=C.sizeof(pfd);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.depth=24
        wgl.gdi.ChoosePixelFormat.argtypes=[W.HDC,C.POINTER(wgl.PFD)];wgl.gdi.SetPixelFormat.argtypes=[W.HDC,C.c_int,C.POINTER(wgl.PFD)]
        fmt=wgl.gdi.ChoosePixelFormat(self.dc,C.byref(pfd));assert fmt and wgl.gdi.SetPixelFormat(self.dc,fmt,C.byref(pfd))
        self.ctx=wgl.ogl.wglCreateContext(self.dc);assert self.ctx and wgl.ogl.wglMakeCurrent(self.dc,self.ctx)
        self.driver={n:gl('glGetString',C.c_char_p,u)(v).decode()for n,v in [('version',0x1F02),('renderer',0x1F01)]}
        self.program=gl('glCreateProgram',u)()
        for extension,kind in [('vert',0x8B31),('frag',0x8B30)]:
            path=HERE/('city_interior.'+extension);raw=path.read_bytes();self.sources[str(path)]=sha(raw)
            shader=gl('glCreateShader',u,u)(kind);text=C.c_char_p(raw)
            gl('glShaderSource',None,u,i,C.POINTER(C.c_char_p),C.POINTER(i))(shader,1,C.byref(text),None)
            gl('glCompileShader',None,u)(shader);okay=i();gl('glGetShaderiv',None,u,u,C.POINTER(i))(shader,0x8B81,C.byref(okay))
            buf=C.create_string_buffer(16384);gl('glGetShaderInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(shader,len(buf),None,buf)
            assert okay.value,path.name+': '+buf.value.decode()
            gl('glAttachShader',None,u,u)(self.program,shader)
        gl('glLinkProgram',None,u)(self.program);okay=i();gl('glGetProgramiv',None,u,u,C.POINTER(i))(self.program,0x8B82,C.byref(okay))
        buf=C.create_string_buffer(16384);gl('glGetProgramInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(self.program,len(buf),None,buf)
        assert okay.value,buf.value.decode();gl('glUseProgram',None,u)(self.program)
        vao=u();gl('glGenVertexArrays',None,i,C.POINTER(u))(1,C.byref(vao));gl('glBindVertexArray',None,u)(vao)
        fbo=u();gl('glGenFramebuffers',None,i,C.POINTER(u))(1,C.byref(fbo));gl('glBindFramebuffer',None,u,u)(0x8D40,fbo)
        tex=u();gl('glGenTextures',None,i,C.POINTER(u))(1,C.byref(tex));gl('glBindTexture',None,u,u)(0x0DE1,tex)
        gl('glTexImage2D',None,u,i,i,i,i,i,u,u,p)(0x0DE1,0,0x8058,width,height,0,0x1908,0x1401,None)
        gl('glTexParameteri',None,u,u,i)(0x0DE1,0x2801,0x2601)
        gl('glFramebufferTexture2D',None,u,u,u,u,i)(0x8D40,0x8CE0,0x0DE1,tex,0)
        depth=u();gl('glGenRenderbuffers',None,i,C.POINTER(u))(1,C.byref(depth));gl('glBindRenderbuffer',None,u,u)(0x8D41,depth)
        gl('glRenderbufferStorage',None,u,u,i,i)(0x8D41,0x81A6,width,height)
        gl('glFramebufferRenderbuffer',None,u,u,u,u)(0x8D40,0x8D00,0x8D41,depth)
        assert gl('glCheckFramebufferStatus',u,u)(0x8D40)==0x8CD5
        gl('glViewport',None,i,i,i,i)(0,0,width,height)
        gl('glEnable',None,u)(0x0B71);gl('glDepthFunc',None,u)(0x0203)
        gl('glDisable',None,u)(0x0B44);gl('glDisable',None,u)(0x0BE2)
    def location(self,name):return gl('glGetUniformLocation',i,u,C.c_char_p)(self.program,name.encode())
    def one(self,name,value,integer=False):
        loc=self.location(name)
        if loc>=0:
            gl('glUniform1i',None,i,i)(loc,int(value))if integer else gl('glUniform1f',None,i,f)(loc,value)
    def vec3(self,name,value):
        loc=self.location(name)
        if loc>=0:gl('glUniform3f',None,i,f,f,f)(loc,*value)
    def mat4(self,name,value):
        loc=self.location(name)
        if loc>=0:gl('glUniformMatrix4fv',None,i,i,C.c_ubyte,C.POINTER(f))(loc,1,0,packed_matrix(value))
    def mat3(self,name,value):
        loc=self.location(name)
        if loc>=0:gl('glUniformMatrix3fv',None,i,i,C.c_ubyte,C.POINTER(f))(loc,1,0,(f*9)(*[value[r][c]for c in range(3)for r in range(3)]))
    def buffer(self,raw):
        vbo=u();gl('glGenBuffers',None,i,C.POINTER(u))(1,C.byref(vbo));gl('glBindBuffer',None,u,u)(0x8892,vbo)
        arr=C.create_string_buffer(raw);gl('glBufferData',None,u,size,p,u)(0x8892,len(raw),arr,0x88E4);return vbo
    def attributes(self,base,next_frame):
        attrib=gl('glVertexAttribPointer',None,u,i,u,C.c_ubyte,i,p);enable=gl('glEnableVertexAttribArray',None,u)
        gl('glBindBuffer',None,u,u)(0x8892,base)
        for loc,count,offset in [(0,3,0),(1,3,12),(2,2,24),(3,4,32)]:attrib(loc,count,0x1406,0,48,p(offset));enable(loc)
        gl('glBindBuffer',None,u,u)(0x8892,next_frame)
        for loc,offset in [(4,0),(5,12)]:attrib(loc,3,0x1406,0,48,p(offset));enable(loc)
    def texture(self,path):
        key=str(path)
        if key not in self.cache:
            im=Image.open(path).convert('RGBA');raw=im.tobytes();arr=C.create_string_buffer(raw)
            tex=u();gl('glGenTextures',None,i,C.POINTER(u))(1,C.byref(tex));gl('glBindTexture',None,u,u)(0x0DE1,tex)
            gl('glTexImage2D',None,u,i,i,i,i,i,u,u,p)(0x0DE1,0,0x8058,im.width,im.height,0,0x1908,0x1401,arr)
            gl('glTexParameteri',None,u,u,i)(0x0DE1,0x2801,0x2703);gl('glTexParameteri',None,u,u,i)(0x0DE1,0x2800,0x2601)
            gl('glGenerateMipmap',None,u)(0x0DE1);self.cache[key]=tex
        gl('glActiveTexture',None,u)(0x84C0);gl('glBindTexture',None,u,u)(0x0DE1,self.cache[key])
    def pixels(self,name):
        gl('glFinish',None)();arr=(C.c_ubyte*(self.width*self.height*4))()
        gl('glReadPixels',None,i,i,i,i,u,u,p)(0,0,self.width,self.height,0x1908,0x1401,arr)
        error=gl('glGetError',u)();assert not error,hex(error)
        image=Image.frombytes('RGBA',(self.width,self.height),bytes(arr),'raw','RGBA',0,-1)
        image.save(OUT/name);return image
    def close(self):
        wgl.ogl.wglMakeCurrent(self.dc,None);wgl.ogl.wglDeleteContext(self.ctx)
        wgl.user.ReleaseDC(self.hwnd,self.dc);wgl.user.DestroyWindow(self.hwnd)

def set_camera(g,eye,target):
    # Invert only the native unit/sign/viewport conventions, keeping the real
    # shader byte-identical. This is an ordinary perspective QA camera.
    matrix=camera([0,0,0],[a-b for a,b in zip(target,eye)],g.width/g.height)
    matrix=[[-value/(4096 if c<3 else 1)/(512/416*.5 if r==1 else 1)
             for c,value in enumerate(row)]for r,row in enumerate(matrix)]
    g.mat4('room_camera',matrix);g.mat3('room_basis',[[1,0,0],[0,1,0],[0,0,1]])
    g.vec3('room_origin',[0,0,0]);g.vec3('room_eye',eye);g.vec3('room_fog',[.28,.31,.33])
    g.one('material_tex',0,True);g.one('room_occupancy',1)

def mesh_object(g,meta,base,frames,offset=(0,0,0),yaw=0,blend=0,actor=False):
    g.attributes(frames[0],frames[1]);g.vec3('object_offset',offset);g.vec3('object_scale',[1,1,1])
    g.one('object_yaw',yaw);g.one('pose_blend',blend)
    for draw in meta['draws']:
        if actor:
            g.texture(base/draw['texture']);g.vec3('material_color',[1,1,1]);g.one('texture_mode',3,True)
            g.one('roughness',.75);g.one('emissive',0,True)
        else:
            mat=meta['materials'][draw['material']];kind=mat['texture_kind']
            texture=ROOT/'city-remaster'/('support-wood-hd.png'if kind==1 else'market-cotton-hd.png')
            g.texture(texture);g.vec3('material_color',mat['color']);g.one('texture_mode',kind,True)
            g.one('roughness',mat['roughness']);g.one('emissive',mat['emissive'],True)
        gl('glDrawArrays',None,u,i,i)(4,draw['first'],draw['count'])

def difference(a,b):
    av=a.convert('RGB').tobytes();bv=b.convert('RGB').tobytes()
    values=[abs(x-y)for x,y in zip(av,bv)]
    return {'changed_pixels':sum(sum(values[k:k+3])>=9 for k in range(0,len(values),3)),
            'mean_absolute_channel_change':sum(values)/len(values)}

def clear():
    gl('glClearColor',None,f,f,f,f)(.075,.085,.095,1);gl('glClear',None,u)(0x4100)

def main():
    OUT.mkdir(exist_ok=True);g=Renderer();checks={};assets={};renders=[]
    try:
        rooms={};actors={}
        for layout in ('lounge','conversation'):
            path=HERE/(layout+'.json');meta=json.loads(path.read_text());raw=(HERE/meta['binary']).read_bytes()
            assert sha(raw)==meta['sha256'];assets[str(path)]=sha(path.read_bytes());assets[str(HERE/meta['binary'])]=sha(raw)
            buffer=g.buffer(raw);rooms[layout]=(meta,(buffer,buffer))
        for name in ('sitting-male','conversing-male','conversing-female'):
            path=ACTORS/(name+'.json');meta=json.loads(path.read_text());raw=(ACTORS/meta['binary']).read_bytes()
            assert sha(raw)==meta['binary_sha256'];assets[str(path)]=sha(path.read_bytes());assets[str(ACTORS/meta['binary'])]=sha(raw)
            stride=meta['frame_stride_bytes'];buffers=[g.buffer(raw[i*stride:(i+1)*stride])for i in range(4)]
            actors[name]=(meta,buffers)
        set_camera(g,[0,1.9,5.4],[0,1.35,-1.8])
        for layout in ('lounge','conversation'):
            output=[]
            for pose in (0.,1.):
                clear();meta,buffers=rooms[layout];mesh_object(g,meta,HERE,buffers)
                placements=[('sitting-male',(0,.09,-2.5),0)]if layout=='lounge'else[
                    ('conversing-male',(-.58,0,-1.6),math.radians(60)),
                    ('conversing-female',(.58,0,-1.6),math.radians(-60))]
                for name,offset,yaw in placements:
                    meta,buffers=actors[name];mesh_object(g,meta,ACTORS,buffers[:2],offset,yaw,pose,True)
                file=layout+'-pose-'+str(int(pose))+'.png';output.append(g.pixels(file));renders.append(file)
            change=difference(*output);checks[layout+'_animation_changes_pixels']=change['changed_pixels']>50
            checks[layout+'_nonempty_render']=len(set(output[0].getdata()))>300
            (OUT/(layout+'-motion.json')).write_text(json.dumps(change,indent=2)+'\n')
        # Alpha uses the exact texture path and fragment shader. A 128-alpha
        # native texel multiplied by vertex alpha=2 must render as fully solid.
        set_camera(g,[0,1,4],[0,1,0]);g.vec3('object_offset',[0,0,0]);g.vec3('object_scale',[1,1,1]);g.one('object_yaw',0);g.one('pose_blend',0)
        g.vec3('material_color',[1,1,1]);g.one('texture_mode',3,True);g.one('emissive',1,True)
        verts=[]
        for x,y,uv in [(-.6,.4,(0,0)),(.6,.4,(1,0)),(.6,1.6,(1,1)),(-.6,.4,(0,0)),(.6,1.6,(1,1)),(-.6,1.6,(0,1))]:
            verts.extend([x,y,0,0,0,1,*uv,1,1,1,2])
        quad=g.buffer(struct.pack('<'+str(len(verts))+'f',*verts));g.attributes(quad,quad)
        images={}
        for alpha in (0,16,32,128,255):
            path=OUT/('alpha-tex-'+str(alpha)+'.png');Image.new('RGBA',(1,1),(130,90,50,alpha)).save(path)
            clear();g.texture(path);gl('glDrawArrays',None,u,i,i)(4,0,6);images[alpha]=g.pixels('alpha-'+str(alpha)+'.png')
        checks['native_128_alpha_same_as_255']=difference(images[128],images[255])['changed_pixels']==0
        checks['transparent_alpha_is_discarded']=difference(images[0],images[16])['changed_pixels']==0
        checks['alpha_threshold_uses_vertex_factor']=difference(images[0],images[32])['changed_pixels']>1000
        checks['native_128_alpha_is_visible']=difference(images[0],images[128])['changed_pixels']>1000
        checks['actual_shaders_compile_link']=True
        checks['source_and_asset_bytes_unchanged']=all(sha(Path(p).read_bytes())==h for p,h in {**assets,**g.sources}.items())
        report={'status':'passed'if all(checks.values())else'failed','driver':g.driver,'checks':checks,'shader_sha256':g.sources,
          'asset_sha256':assets,'renders':renders,'camera':'synthetic street view; native shader PS2 clip/unit conventions inverted through uniforms only',
          'method':'Actual shaders compile/link/draw in hidden WGL; actual 12f room and actor binaries; exact native PNG textures; GPU frame readback',
          'native_game_validation':False}
        (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='passed'
    finally:g.close()
if __name__=='__main__':main()
