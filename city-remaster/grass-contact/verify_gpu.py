"""Read-only execution of the real SHRUB vertex shader through WGL feedback.

Uses a hidden 16x16 context, no game process/window, third-party dependencies or
runtime edits. Only gpu-validation.json is written. Shader text is not reauthored:
the two normal renderer scale defines are inserted after its version directive.
"""
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib, json, math

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHADER='game/graphics/opengl_renderer/shaders/shrub.vert'
user=C.WinDLL('user32');gdi=C.WinDLL('gdi32');ogl=C.WinDLL('opengl32')
user.CreateWindowExW.restype=W.HWND
user.CreateWindowExW.argtypes=[W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p]
user.GetDC.restype=W.HDC;user.GetDC.argtypes=[W.HWND]
user.ReleaseDC.argtypes=[W.HWND,W.HDC]
user.DestroyWindow.argtypes=[W.HWND]
ogl.wglCreateContext.restype=C.c_void_p;ogl.wglCreateContext.argtypes=[W.HDC]
ogl.wglMakeCurrent.argtypes=[W.HDC,C.c_void_p]
ogl.wglDeleteContext.argtypes=[C.c_void_p]
ogl.wglGetProcAddress.restype=C.c_void_p;ogl.wglGetProcAddress.argtypes=[C.c_char_p]

class PFD(C.Structure):
    _fields_=[('size',W.WORD),('version',W.WORD),('flags',W.DWORD),('pixel',W.BYTE),
      ('color',W.BYTE),('r',W.BYTE),('rs',W.BYTE),('g',W.BYTE),('gs',W.BYTE),('b',W.BYTE),('bs',W.BYTE),
      ('a',W.BYTE),('as_',W.BYTE),('acc',W.BYTE),('ar',W.BYTE),('ag',W.BYTE),('ab',W.BYTE),('aa',W.BYTE),
      ('depth',W.BYTE),('stencil',W.BYTE),('aux',W.BYTE),('layer',W.BYTE),('reserved',W.BYTE),
      ('lm',W.DWORD),('vm',W.DWORD),('dm',W.DWORD)]

def gl(name,result,*args):
    address=ogl.wglGetProcAddress(name.encode())
    if address not in(None,1,2,3,C.c_void_p(-1).value):return C.WINFUNCTYPE(result,*args)(address)
    fn=getattr(ogl,name);fn.restype=result;fn.argtypes=list(args);return fn

def main():
    paths=[ROOT/tree/SHADER for tree in('engine-src','data')]
    raw=paths[0].read_bytes();assert raw==paths[1].read_bytes()
    packed=ROOT/'variants/remaster'/SHADER
    assert packed.read_bytes()==raw,'Test must match the currently packaged shader'
    text=raw.decode().replace('\r\n','\n')
    assert text.count('#version 410 core\n')==1
    text=text.replace('#version 410 core\n','#version 410 core\n#define SCISSOR_ADJUST 1.0\n#define HEIGHT_SCALE 1.0\n',1)
    # No WS_VISIBLE, ShowWindow or event-loop focus; cannot interrupt native play.
    hwnd=user.CreateWindowExW(0,'STATIC','Grass shader read-only validation',0,0,0,16,16,None,None,None,None)
    assert hwnd
    dc=user.GetDC(hwnd);context=None
    try:
        pfd=PFD();pfd.size=C.sizeof(PFD);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.depth=24
        gdi.ChoosePixelFormat.argtypes=[W.HDC,C.POINTER(PFD)];gdi.SetPixelFormat.argtypes=[W.HDC,C.c_int,C.POINTER(PFD)]
        fmt=gdi.ChoosePixelFormat(dc,C.byref(pfd));assert fmt and gdi.SetPixelFormat(dc,fmt,C.byref(pfd))
        context=ogl.wglCreateContext(dc);assert context and ogl.wglMakeCurrent(dc,context)
        u=C.c_uint;i=C.c_int;p=C.c_void_p;f=C.c_float;size=C.c_ssize_t
        get_string=gl('glGetString',C.c_char_p,u)
        driver={name:get_string(value).decode()for name,value in [('version',0x1F02),('vendor',0x1F00),('renderer',0x1F01)]}
        shader=gl('glCreateShader',u,u)(0x8B31);code=C.c_char_p(text.encode())
        gl('glShaderSource',None,u,i,C.POINTER(C.c_char_p),C.POINTER(i))(shader,1,C.byref(code),None)
        gl('glCompileShader',None,u)(shader);okay=i()
        gl('glGetShaderiv',None,u,u,C.POINTER(i))(shader,0x8B81,C.byref(okay))
        log=C.create_string_buffer(16384);gl('glGetShaderInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(shader,len(log),None,log)
        assert okay.value,log.value.decode()
        program=gl('glCreateProgram',u)();gl('glAttachShader',None,u,u)(program,shader)
        names=(C.c_char_p*1)(b'arena_world')
        gl('glTransformFeedbackVaryings',None,u,i,C.POINTER(C.c_char_p),u)(program,1,names,0x8C8C)
        gl('glLinkProgram',None,u)(program);gl('glGetProgramiv',None,u,u,C.POINTER(i))(program,0x8B82,C.byref(okay))
        gl('glGetProgramInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(program,len(log),None,log)
        assert okay.value,log.value.decode()
        gl('glUseProgram',None,u)(program)
        vao=u();gl('glGenVertexArrays',None,i,C.POINTER(u))(1,C.byref(vao));gl('glBindVertexArray',None,u)(vao)
        gen=gl('glGenBuffers',None,i,C.POINTER(u));bind=gl('glBindBuffer',None,u,u)
        data=gl('glBufferData',None,u,size,p,u)
        # Metres span the actual city coordinates to include float precision loss.
        fixtures=[('root',(1767.1,7.03,-330.),4096.),('near_tip',(1767.2,7.6,-330.),0.),
          ('far_tip',(1769.,7.6,-330.),0.),('other_floor',(1767.1,10.6,-330.),0.),
          ('center_tip',(1767.,7.6,-330.),0.),('half_blade',(1767.2,7.35,-330.),2048.)]
        values=[]
        for _,pos,v in fixtures:values.extend([a*4096 for a in pos]+[1234.,v,1.])
        vertices=(f*len(values))(*values);vbo=u();gen(1,C.byref(vbo));bind(0x8892,vbo);data(0x8892,C.sizeof(vertices),vertices,0x88E4)
        attrib=gl('glVertexAttribPointer',None,u,i,u,C.c_ubyte,i,p)
        enable=gl('glEnableVertexAttribArray',None,u)
        for location,offset in [(0,0),(1,12)]:attrib(location,3,0x1406,0,24,C.c_void_p(offset));enable(location)
        feedback=u();gen(1,C.byref(feedback));bind(0x8C8E,feedback);data(0x8C8E,len(fixtures)*12,None,0x88E1)
        gl('glBindBufferBase',None,u,u,u)(0x8C8E,0,feedback)
        gl('glEnable',None,u)(0x8C89) # GL_RASTERIZER_DISCARD
        location=gl('glGetUniformLocation',i,u,C.c_char_p)
        uniform_i=gl('glUniform1i',None,i,i);uniform_f=gl('glUniform1f',None,i,f)
        uniform4=gl('glUniform4fv',None,i,i,C.POINTER(f))
        contacts=(f*64)(*([1767.,7.,-330.,10.]*16))
        uniform4(location(program,b'grass_contacts'),16,contacts)
        uniform_f(location(program,b'palace_time'),13.37)
        begin=gl('glBeginTransformFeedback',None,u);end=gl('glEndTransformFeedback',None)
        draw=gl('glDrawArrays',None,u,i,i);get=gl('glGetBufferSubData',None,u,size,size,p)
        def run(mode,count,age):
            uniform_i(location(program,b'palace_foliage'),mode)
            uniform_i(location(program,b'grass_contact_count'),count)
            uniform_f(location(program,b'grass_contact_time'),10.+age)
            begin(0);draw(0,0,len(fixtures));end();gl('glFinish',None)()
            output=(f*(len(fixtures)*3))();get(0x8C8E,0,C.sizeof(output),output)
            assert gl('glGetError',u)()==0
            return [tuple(output[n*3+k]for k in range(3))for n in range(len(fixtures))]
        quiet=run(2,0,0);touch=run(2,1,0);duplicates=run(2,16,0)
        ages=(0,.1,.3,.6,.9,1.,1.2)
        frames=[run(2,1,t)for t in ages]
        delta=lambda a,b:tuple(x-y for x,y in zip(a,b))
        length=lambda d:math.sqrt(sum(x*x for x in d))
        peak=length(delta(touch[4],quiet[4]))
        recovery=[length(delta(frame[1],quiet[1]))for frame in frames]
        checks={'actual_packaged_vertex_shader_compile_link':True,
          'root_output_bit_identical':touch[0]==quiet[0],
          'near_tip_moves_outward_and_down':touch[1][0]>quiet[1][0]+.1 and touch[1][1]<quiet[1][1]-.02,
          'centerline_is_finite_and_bounded':all(math.isfinite(x)for x in touch[4]) and .28<peak<.293,
          'far_tip_output_bit_identical':touch[2]==quiet[2],
          'other_floor_output_bit_identical':touch[3]==quiet[3],
          'duplicate_contacts_bit_identical':touch==duplicates,
          'zero_count_is_exact_wind_only':run(2,0,.6)==quiet,
          'half_blade_bends_less_than_tip':length(delta(touch[5],quiet[5]))<length(delta(touch[1],quiet[1])),
          'recovery_monotonic':all(a>=b for a,b in zip(recovery,recovery[1:])),
          'one_second_restores_wind_bit_identical':frames[-2]==quiet and frames[-1]==quiet,
          'mode_zero_ignores_contacts':run(0,0,0)==run(0,16,0),
          'palace_mode_one_ignores_contacts':run(1,0,0)==run(1,16,0),
          'native_shader_files_unchanged':all(path.read_bytes()==raw for path in paths) and packed.read_bytes()==raw}
        report={'status':'passed'if all(checks.values())else'failed','shader_sha256':hashlib.sha256(raw).hexdigest(),
          'driver':driver,'method':'Actual full packaged vertex shader; arena_world transform feedback; hidden WGL context',
          'checks':checks,'fixtures':[{'name':name,'position_m':pos,'native_v':v,'contact_delta_m':delta(a,b)}
              for(name,pos,v),a,b in zip(fixtures,touch,quiet)],
          'recovery_age_s':ages,'near_tip_contact_displacement_m':recovery,
          'centerline_contact_displacement_m':peak,'native_visual_validation':False}
        (HERE/'gpu-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
        assert all(checks.values()),[k for k,v in checks.items()if not v]
    finally:
        if context:ogl.wglMakeCurrent(dc,None);ogl.wglDeleteContext(context)
        user.ReleaseDC(hwnd,dc);user.DestroyWindow(hwnd)

if __name__=='__main__':main()
