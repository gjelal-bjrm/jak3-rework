"""Offscreen GLSL compilation/temporal checks in a hidden WGL context.

The fixture is synthetic procedural coverage, not a captured in-game sky.
Run with Blender's Python for numpy/Pillow. No game or renderer process touched.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import json,time
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
user=C.WinDLL('user32');gdi=C.WinDLL('gdi32');ogl=C.WinDLL('opengl32')
user.CreateWindowExW.restype=W.HWND
user.CreateWindowExW.argtypes=[W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p]
user.GetDC.restype=W.HDC;user.GetDC.argtypes=[W.HWND]
ogl.wglCreateContext.restype=C.c_void_p;ogl.wglCreateContext.argtypes=[W.HDC]
ogl.wglMakeCurrent.argtypes=[W.HDC,C.c_void_p]
ogl.wglGetProcAddress.restype=C.c_void_p;ogl.wglGetProcAddress.argtypes=[C.c_char_p]


class PFD(C.Structure):
    _fields_=[('size',W.WORD),('version',W.WORD),('flags',W.DWORD),('pixel',W.BYTE),
              ('color',W.BYTE),('r',W.BYTE),('rs',W.BYTE),('g',W.BYTE),('gs',W.BYTE),('b',W.BYTE),('bs',W.BYTE),
              ('a',W.BYTE),('as_',W.BYTE),('acc',W.BYTE),('ar',W.BYTE),('ag',W.BYTE),('ab',W.BYTE),('aa',W.BYTE),
              ('depth',W.BYTE),('stencil',W.BYTE),('aux',W.BYTE),('layer',W.BYTE),('reserved',W.BYTE),
              ('lm',W.DWORD),('vm',W.DWORD),('dm',W.DWORD)]


def gl(name,rest,*args):
    address=ogl.wglGetProcAddress(name.encode())
    if address not in (None,1,2,3,C.c_void_p(-1).value):return C.WINFUNCTYPE(rest,*args)(address)
    fn=getattr(ogl,name);fn.restype=rest;fn.argtypes=list(args);return fn


def main():
    # No WS_VISIBLE and no ShowWindow: this context cannot open a visible window.
    hwnd=user.CreateWindowExW(0,'STATIC','Spargus shader validation',0,0,0,16,16,None,None,None,None)
    dc=user.GetDC(hwnd);pfd=PFD();pfd.size=C.sizeof(PFD);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.depth=24
    gdi.ChoosePixelFormat.argtypes=[W.HDC,C.POINTER(PFD)];gdi.SetPixelFormat.argtypes=[W.HDC,C.c_int,C.POINTER(PFD)]
    fmt=gdi.ChoosePixelFormat(dc,C.byref(pfd));assert fmt and gdi.SetPixelFormat(dc,fmt,C.byref(pfd))
    context=ogl.wglCreateContext(dc);assert context and ogl.wglMakeCurrent(dc,context)
    uint=C.c_uint;integer=C.c_int;ptr=C.c_void_p;float_=C.c_float
    create=gl('glCreateShader',uint,uint);source=gl('glShaderSource',None,uint,integer,C.POINTER(C.c_char_p),C.POINTER(integer))
    compile_=gl('glCompileShader',None,uint);shaderiv=gl('glGetShaderiv',None,uint,uint,C.POINTER(integer))
    log=gl('glGetShaderInfoLog',None,uint,integer,C.POINTER(integer),C.c_char_p)
    program=gl('glCreateProgram',uint)();attach=gl('glAttachShader',None,uint,uint)
    for name,kind in [('spargus_clouds.vert',0x8B31),('spargus_clouds.frag',0x8B30)]:
        s=create(kind);text=(HERE/name).read_bytes();st=C.c_char_p(text);source(s,1,C.byref(st),None);compile_(s)
        okay=integer();shaderiv(s,0x8B81,C.byref(okay));buf=C.create_string_buffer(8192);log(s,8192,None,buf)
        assert okay.value,(name,buf.value.decode());attach(program,s)
    gl('glLinkProgram',None,uint)(program);okay=integer();gl('glGetProgramiv',None,uint,uint,C.POINTER(integer))(program,0x8B82,C.byref(okay));assert okay.value
    use=gl('glUseProgram',None,uint);use(program)
    location=gl('glGetUniformLocation',integer,uint,C.c_char_p);uniform=gl('glUniform1f',None,integer,float_)
    gl('glUniform1i',None,integer,integer)(location(program,b'native_clouds'),0)
    vao=uint();gl('glGenVertexArrays',None,integer,C.POINTER(uint))(1,C.byref(vao));gl('glBindVertexArray',None,uint)(vao)
    gen=gl('glGenTextures',None,integer,C.POINTER(uint));bind=gl('glBindTexture',None,uint,uint)
    teximage=gl('glTexImage2D',None,uint,integer,integer,integer,integer,integer,uint,uint,ptr)
    param=gl('glTexParameteri',None,uint,uint,integer);mips=gl('glGenerateMipmap',None,uint)
    native=uint();gen(1,C.byref(native));bind(0x0DE1,native)
    # Smooth multiscale periodic banks, spanning fully clear and opaque areas.
    size=1024;rng=np.random.default_rng(37);field=np.zeros((size,size),np.float32)
    for grid,weight in [(8,.53),(16,.28),(32,.14),(64,.05)]:
        random=rng.random((grid,grid));x=np.arange(size)*grid/size;i=np.floor(x).astype(int);f=x-i;w=f*f*(3-2*f)
        a=random[i[:,None]%grid,i[None,:]%grid];b=random[i[:,None]%grid,(i[None,:]+1)%grid]
        c=random[(i[:,None]+1)%grid,i[None,:]%grid];d=random[(i[:,None]+1)%grid,(i[None,:]+1)%grid]
        field+=weight*((a*(1-w)+b*w)*(1-w[:,None])+(c*(1-w)+d*w)*w[:,None])
    coverage=np.sin(np.clip((field-.34)/.31,0,1)*np.pi/2)**2
    pixels=np.full((size,size,4),.5,np.float32);pixels[:,:,3]=coverage*.5
    teximage(0x0DE1,0,0x881A,size,size,0,0x1908,0x1406,pixels.ctypes.data)
    param(0x0DE1,0x2801,0x2703);param(0x0DE1,0x2800,0x2601);mips(0x0DE1)
    output=uint();gen(1,C.byref(output));bind(0x0DE1,output)
    teximage(0x0DE1,0,0x881A,size,size,0,0x1908,0x1406,None)
    param(0x0DE1,0x2801,0x2601);param(0x0DE1,0x2800,0x2601)
    fbo=uint();gl('glGenFramebuffers',None,integer,C.POINTER(uint))(1,C.byref(fbo))
    gl('glBindFramebuffer',None,uint,uint)(0x8D40,fbo)
    gl('glFramebufferTexture2D',None,uint,uint,uint,uint,integer)(0x8D40,0x8CE0,0x0DE1,output,0)
    assert gl('glCheckFramebufferStatus',uint,uint)(0x8D40)==0x8CD5
    gl('glViewport',None,integer,integer,integer,integer)(0,0,size,size);bind(0x0DE1,native)
    draw=gl('glDrawArrays',None,uint,integer,integer);finish=gl('glFinish',None)
    read=gl('glReadPixels',None,integer,integer,integer,integer,uint,uint,ptr)
    frames=[];timings=[]
    for moment in (0.,1/60,8.,32.):
        uniform(location(program,b'cloud_time'),moment);t=time.perf_counter();draw(4,0,3);finish();timings.append((time.perf_counter()-t)*1000)
        result=np.empty_like(pixels);read(0,0,size,size,0x1908,0x1406,result.ctypes.data);frames.append(result)
    # A fully white native bank exposed the original flat-cutout regression:
    # detail and self-shadow must survive even when the source coverage saturates.
    full=pixels.copy();full[:,:,3]=.5
    teximage(0x0DE1,0,0x881A,size,size,0,0x1908,0x1406,full.ctypes.data);mips(0x0DE1)
    uniform(location(program,b'cloud_time'),0.);draw(4,0,3);finish()
    dense=np.empty_like(pixels);read(0,0,size,size,0x1908,0x1406,dense.ctypes.data)
    full[:,:,3]=0.
    teximage(0x0DE1,0,0x881A,size,size,0,0x1908,0x1406,full.ctypes.data);mips(0x0DE1)
    draw(4,0,3);finish();clear=np.empty_like(pixels);read(0,0,size,size,0x1908,0x1406,clear.ctypes.data)
    # Compare visible premultiplied contribution; RGB at zero alpha has no effect.
    visible=[np.concatenate((f[:,:,:3]*f[:,:,3:4],f[:,:,3:4]),axis=2)for f in frames]
    checks={'glsl_compile_and_link':True,'finite_rgba':all(np.isfinite(f).all()for f in frames),
            'native_half_alpha_contract':all(float(f[:,:,3].min())>=0 and float(f[:,:,3].max())<=.5 for f in frames),
            'neutral_rgb_preserves_palette':all(np.array_equal(f[:,:,0],f[:,:,1])and np.array_equal(f[:,:,0],f[:,:,2])for f in frames),
            'visible_temporal_evolution':float(np.abs(frames[3]-frames[0]).mean())>.0003,
            'smooth_frame_step':float(np.abs(visible[1]-visible[0]).max())<.003,
            'saturated_native_banks_keep_internal_relief':float(dense[:,:,0].std())>.02,
            'clear_native_weather_stays_clear':float(clear[:,:,3].max())==0.}
    out=HERE/'sky-preview';out.mkdir(exist_ok=True)
    # A colour fixture only: actual hue and sun lighting still come from GOAL.
    sky=np.array([.38,.45,.60]);tint=np.array([.79,.76,.61])
    for name,f in [('native-fixture',pixels),('new-fixture-t0',frames[0]),('new-fixture-t32',frames[3]),('dense-bank-fixture',dense)]:
        a=np.clip(f[:,:,3:4]*2,0,1);rgb=sky*(1-a)+tint*(f[:,:,:3]*2)*a
        Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(out/(name+'.png'))
    report={'status':'passed'if all(checks.values())else'failed','checks':{k:bool(v)for k,v in checks.items()},
            'fixture':'Synthetic native-style coverage; not an in-game screenshot',
            'render_ms':timings,'max_frame_step':float(np.abs(visible[1]-visible[0]).max()),
            'mean_32s_change':float(np.abs(frames[3]-frames[0]).mean()),
            'saturated_bank_shading_stddev':float(dense[:,:,0].std()),'native_visual_validation':False}
    (HERE/'spargus-clouds-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    assert all(checks.values())
    ogl.wglMakeCurrent(dc,None);ogl.wglDeleteContext.argtypes=[C.c_void_p];ogl.wglDeleteContext(context)
    user.DestroyWindow.argtypes=[W.HWND];user.DestroyWindow(hwnd)


if __name__=='__main__':main()
