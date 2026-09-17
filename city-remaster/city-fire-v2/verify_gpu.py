"""Render the actual city volume in a hidden WGL context; no game or UI manipulation."""
from pathlib import Path
import ctypes as C, hashlib,importlib.util,json,math
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('wgl_helpers',ROOT/'city-remaster/grass-contact/verify_gpu.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
u=C.c_uint;i=C.c_int;f=C.c_float;p=C.c_void_p
gl=w.gl

def main():
    window=w.user.CreateWindowExW(0,'STATIC','City fire shader validation',0,0,0,256,256,None,None,None,None)
    assert window;dc=w.user.GetDC(window);context=None
    try:
      pfd=w.PFD();pfd.size=C.sizeof(w.PFD);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.depth=24
      w.gdi.ChoosePixelFormat.argtypes=[w.W.HDC,C.POINTER(w.PFD)];w.gdi.SetPixelFormat.argtypes=[w.W.HDC,C.c_int,C.POINTER(w.PFD)]
      fmt=w.gdi.ChoosePixelFormat(dc,C.byref(pfd));assert fmt and w.gdi.SetPixelFormat(dc,fmt,C.byref(pfd))
      context=w.ogl.wglCreateContext(dc);assert context and w.ogl.wglMakeCurrent(dc,context)
      driver={n:gl('glGetString',C.c_char_p,u)(v).decode()for n,v in [('version',0x1F02),('vendor',0x1F00),('renderer',0x1F01)]}
      programs={};hashes={};checks={}
      for stem in ('city_fire','city_fire_lighting','city_fire_embers'):
        program=gl('glCreateProgram',u)()
        for ext,kind in [('vert',0x8B31),('frag',0x8B30)]:
          name=stem+'.'+ext;source=HERE/'shaders'/name;raw=source.read_bytes()
          assert all((ROOT/tree/'game/graphics/opengl_renderer/shaders'/name).read_bytes()==raw for tree in ('engine-src','data'))
          hashes[name]=hashlib.sha256(raw).hexdigest();shader=gl('glCreateShader',u,u)(kind);code=C.c_char_p(raw)
          gl('glShaderSource',None,u,i,C.POINTER(C.c_char_p),C.POINTER(i))(shader,1,C.byref(code),None)
          gl('glCompileShader',None,u)(shader);okay=i();gl('glGetShaderiv',None,u,u,C.POINTER(i))(shader,0x8B81,C.byref(okay))
          log=C.create_string_buffer(16384);gl('glGetShaderInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(shader,len(log),None,log)
          assert okay.value,(name,log.value.decode());gl('glAttachShader',None,u,u)(program,shader)
        gl('glLinkProgram',None,u)(program);okay=i();gl('glGetProgramiv',None,u,u,C.POINTER(i))(program,0x8B82,C.byref(okay))
        log=C.create_string_buffer(16384);gl('glGetProgramInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(program,len(log),None,log)
        assert okay.value,(stem,log.value.decode());programs[stem]=program;checks[stem+'_compile_link']=True
      program=programs['city_fire'];gl('glUseProgram',None,u)(program)
      location=lambda name:gl('glGetUniformLocation',i,u,C.c_char_p)(program,name.encode())
      uf=lambda name,value:gl('glUniform1f',None,i,f)(location(name),value)
      ui=lambda name,value:gl('glUniform1i',None,i,i)(location(name),value)
      u4=lambda name,values:gl('glUniform4fv',None,i,i,C.POINTER(f))(location(name),1,(f*4)(*values))
      ui('fire_count',1);u4('fire_sources',(0,0,0,.75));uf('fire_heights',4.0);uf('fire_footprints',.6);uf('fire_seeds',7.13)
      u4('cam_trans',(0,1.8*4096,8*4096,1));u4('fluid_viewport',(0,0,256,256))
      # Same world-unit and reversed camera conventions as the renderer.
      near=.1;far=100.;cot=1/math.tan(math.radians(25));m=[0.]*16
      m[0]=-cot/4096;m[5]=-cot/((512/416)*.5)/4096;m[10]=(far+near)/(far-near)/4096
      m[11]=1/4096;m[14]=2*far*near/(far-near)
      gl('glUniformMatrix4fv',None,i,i,C.c_ubyte,C.POINTER(f))(location('pc_camera'),1,0,(f*16)(*m))
      vao=u();gl('glGenVertexArrays',None,i,C.POINTER(u))(1,C.byref(vao));gl('glBindVertexArray',None,u)(vao)
      textures=(u*3)();gl('glGenTextures',None,i,C.POINTER(u))(3,textures)
      tex_image=gl('glTexImage2D',None,u,i,i,i,i,i,u,u,p)
      for index in range(3):
        gl('glActiveTexture',None,u)(0x84C0+index);gl('glBindTexture',None,u,u)(0x0DE1,textures[index])
        tex_image(0x0DE1,0,0x8814,256,256,0,0x1908,0x1406,None)
        gl('glTexParameteri',None,u,u,i)(0x0DE1,0x2801,0x2600);gl('glTexParameteri',None,u,u,i)(0x0DE1,0x2800,0x2600)
      ui('tex_T25',1);ui('tex_T26',2)
      framebuffer=u();gl('glGenFramebuffers',None,i,C.POINTER(u))(1,C.byref(framebuffer));gl('glBindFramebuffer',None,u,u)(0x8D40,framebuffer)
      gl('glFramebufferTexture2D',None,u,u,u,u,i)(0x8D40,0x8CE0,0x0DE1,textures[0],0)
      assert gl('glCheckFramebufferStatus',u,u)(0x8D40)==0x8CD5
      gl('glViewport',None,i,i,i,i)(0,0,256,256)
      for flag in (0x0BE2,0x0B71,0x0B44):gl('glDisable',None,u)(flag)
      def render(clock,wall=False):
        uf('fire_time',clock)
        depth=0.
        if wall:depth=((far+near)/(far-near)-2*far*near/((far-near)*4))*.5+.5
        pixels=(f*(256*256*4))(*([depth,depth,depth,depth]*(256*256)))
        gl('glActiveTexture',None,u)(0x84C2);gl('glBindTexture',None,u,u)(0x0DE1,textures[2]);tex_image(0x0DE1,0,0x8814,256,256,0,0x1908,0x1406,pixels)
        gl('glClearColor',None,f,f,f,f)(0,0,0,0);gl('glClear',None,u)(0x4000)
        gl('glDrawArraysInstanced',None,u,i,i,i)(4,0,6,1);gl('glFinish',None)()
        result=(f*(256*256*4))();gl('glReadPixels',None,i,i,i,i,u,u,p)(0,0,256,256,0x1908,0x1406,result)
        assert gl('glGetError',u)()==0
        return list(result)
      a=render(3.0);b=render(3.6);blocked=render(3.0,True)
      area=sum(a[k]>.01 for k in range(3,len(a),4));delta=sum(abs(x-y)for x,y in zip(a,b))/len(a)
      checks.update({'volume_has_visible_coverage':area>1000,'animation_changes_density':delta>.003,
                     'opaque_depth_completely_occludes':max(abs(x)for x in blocked)<1e-6,
                     'all_radiance_finite':all(math.isfinite(x)for x in a+b),
                     'opacity_bounded':all(0<=a[k]<=1 for k in range(3,len(a),4))})
      report={'status':'passed'if all(checks.values())else'failed','driver':driver,'checks':checks,
              'shader_sha256':hashes,'visible_pixels':area,'mean_animation_change':delta,
              'method':'Actual generated city shaders, hidden WGL framebuffer, 48-step volume at two times and opaque wall depth',
              'native_visual_validation':False}
      (HERE/'gpu-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert all(checks.values())
    finally:
      if context:w.ogl.wglMakeCurrent(dc,None);w.ogl.wglDeleteContext(context)
      w.user.ReleaseDC(window,dc);w.user.DestroyWindow(window)
if __name__=='__main__':main()
