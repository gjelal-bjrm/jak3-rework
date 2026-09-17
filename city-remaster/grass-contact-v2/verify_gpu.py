"""Actual revised shader + native exported blades, hidden WGL transform feedback."""
from pathlib import Path
import ctypes as C,importlib.util,json,struct,hashlib,math
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];QA=HERE/'qa'
spec=importlib.util.spec_from_file_location('grass_wgl',HERE.parent/'grass-contact/verify_gpu.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
W=api.W;user=api.user;gdi=api.gdi;ogl=api.ogl;gl=api.gl

def main():
 shader_path=ROOT/'engine-src/game/graphics/opengl_renderer/shaders/shrub.vert'
 text=shader_path.read_text().replace('#version 410 core\n','#version 410 core\n#define SCISSOR_ADJUST 1.0\n#define HEIGHT_SCALE 1.0\n',1)
 raw=(QA/'native-grass.bin').read_bytes();count=struct.unpack_from('<I',raw)[0]
 native=np.frombuffer(raw, dtype='<f4',offset=4).reshape(count,5).copy()
 roots=np.fromfile(QA/'native-roots.bin',dtype='<f4').reshape(count,4)
 vertices=np.concatenate([native,roots],axis=1).astype('f4')
 tips=np.where((native[:,4]==0)&(roots[:,3]>2.0))[0]
 tip=int(tips[np.argmax(roots[tips,3])]);root=roots[tip,:3].copy();contact=root.copy();contact[0]-=.11
 hwnd=user.CreateWindowExW(0,'STATIC','Grass roots GPU validation',0,0,0,16,16,None,None,None,None);assert hwnd
 dc=user.GetDC(hwnd);context=None
 try:
  pfd=api.PFD();pfd.size=C.sizeof(api.PFD);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.depth=24
  gdi.ChoosePixelFormat.argtypes=[W.HDC,C.POINTER(api.PFD)];gdi.SetPixelFormat.argtypes=[W.HDC,C.c_int,C.POINTER(api.PFD)]
  fmt=gdi.ChoosePixelFormat(dc,C.byref(pfd));assert fmt and gdi.SetPixelFormat(dc,fmt,C.byref(pfd))
  context=ogl.wglCreateContext(dc);assert context and ogl.wglMakeCurrent(dc,context)
  u=C.c_uint;i=C.c_int;p=C.c_void_p;f=C.c_float;size=C.c_ssize_t
  get_string=gl('glGetString',C.c_char_p,u);driver={k:get_string(v).decode()for k,v in [('version',0x1F02),('renderer',0x1F01)]}
  shader=gl('glCreateShader',u,u)(0x8B31);code=C.c_char_p(text.encode())
  gl('glShaderSource',None,u,i,C.POINTER(C.c_char_p),C.POINTER(i))(shader,1,C.byref(code),None);gl('glCompileShader',None,u)(shader)
  okay=i();gl('glGetShaderiv',None,u,u,C.POINTER(i))(shader,0x8B81,C.byref(okay))
  log=C.create_string_buffer(16384);gl('glGetShaderInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(shader,len(log),None,log);assert okay.value,log.value.decode()
  program=gl('glCreateProgram',u)();gl('glAttachShader',None,u,u)(program,shader)
  names=(C.c_char_p*1)(b'arena_world');gl('glTransformFeedbackVaryings',None,u,i,C.POINTER(C.c_char_p),u)(program,1,names,0x8C8C)
  gl('glLinkProgram',None,u)(program);gl('glGetProgramiv',None,u,u,C.POINTER(i))(program,0x8B82,C.byref(okay))
  gl('glGetProgramInfoLog',None,u,i,C.POINTER(i),C.c_char_p)(program,len(log),None,log);assert okay.value,log.value.decode()
  gl('glUseProgram',None,u)(program)
  vao=u();gl('glGenVertexArrays',None,i,C.POINTER(u))(1,C.byref(vao));gl('glBindVertexArray',None,u)(vao)
  gen=gl('glGenBuffers',None,i,C.POINTER(u));bind=gl('glBindBuffer',None,u,u);data=gl('glBufferData',None,u,size,p,u)
  vbo=u();gen(1,C.byref(vbo));bind(0x8892,vbo);data(0x8892,vertices.nbytes,vertices.ctypes.data_as(p),0x88E4)
  attrib=gl('glVertexAttribPointer',None,u,i,u,C.c_ubyte,i,p);enable=gl('glEnableVertexAttribArray',None,u)
  for loc,n,off in[(0,3,0),(1,2,12),(4,4,20)]:attrib(loc,n,0x1406,0,36,p(off));enable(loc)
  feedback=u();gen(1,C.byref(feedback));bind(0x8C8E,feedback);data(0x8C8E,count*12,None,0x88E1)
  gl('glBindBufferBase',None,u,u,u)(0x8C8E,0,feedback);gl('glEnable',None,u)(0x8C89)
  location=gl('glGetUniformLocation',i,u,C.c_char_p);ui=gl('glUniform1i',None,i,i);uf=gl('glUniform1f',None,i,f);u4=gl('glUniform4fv',None,i,i,C.POINTER(f))
  uf(location(program,b'palace_time'),13.37)
  begin=gl('glBeginTransformFeedback',None,u);end=gl('glEndTransformFeedback',None);draw=gl('glDrawArrays',None,u,i,i);get=gl('glGetBufferSubData',None,u,size,size,p)
  def run(age=0,n=1,mode=2,xyz=None):
   xyz=contact if xyz is None else xyz
   values=(f*64)(*(list(xyz)+[10.])*16);u4(location(program,b'grass_contacts'),16,values)
   ui(location(program,b'palace_foliage'),mode);ui(location(program,b'grass_contact_count'),n);uf(location(program,b'grass_contact_time'),10+age)
   begin(0);draw(0,0,count);end();gl('glFinish',None)()
   output=np.empty((count,3),dtype='f4');get(0x8C8E,0,output.nbytes,output.ctypes.data_as(p));assert gl('glGetError',u)()==0
   return output
  quiet=run(n=0);touch=run();delta=touch-quiet;dist=np.linalg.norm(delta,axis=1)
  rootmask=native[:,4]==4096;tipmask=native[:,4]==0
  sameplant=np.linalg.norm(roots[:,:3]-root,axis=1)<.28
  outer=sameplant&tipmask&(np.linalg.norm(native[:,[0,2]]/4096-contact[[0,2]],axis=1)>.9)
  far=np.linalg.norm(roots[:,[0,2]]-contact[[0,2]],axis=1)>1.31
  ages=[0,.1,.3,.6,.9,1.0,1.2];frames=[run(age=t)for t in ages]
  lengths=[float(np.linalg.norm(a[tip]-quiet[tip]))for a in frames]
  shifted=contact.copy();shifted[1]+=8
  checks={'full_vertex_shader_compile_and_link':True,
   'native_19530_vertices_finite':bool(np.isfinite(touch).all()),
   'all_native_roots_bit_identical':bool(np.array_equal(touch[rootmask],quiet[rootmask])),
   'tall_native_tip_visible_displacement':float(dist[tip])>.30,
   'outer_native_tips_follow_root_contact':bool(outer.any())and float(np.max(dist[outer]))>.20,
   'distant_blades_bit_identical':bool(far.any())and bool(np.array_equal(touch[far],quiet[far])),
   'other_floor_bit_identical':bool(np.array_equal(run(xyz=shifted),quiet)),
   'duplicates_do_not_amplify':float(np.max(np.abs(run(n=16)-touch)))<.001,
   'bounded_displacement':float(np.max(dist))<=.77,
   'smooth_monotonic_recovery':all(a>=b for a,b in zip(lengths,lengths[1:])),
   'one_second_exact_rest':bool(np.array_equal(frames[-2],quiet)and np.array_equal(frames[-1],quiet)),
   'non_grass_mode_unchanged':bool(np.array_equal(run(n=0,mode=0),run(n=16,mode=0))),
   'palace_foliage_unchanged':bool(np.array_equal(run(n=0,mode=1),run(n=16,mode=1)))}
  result={'status':'passed'if all(checks.values())else'failed','checks':checks,'driver':driver,
   'shader_sha256':hashlib.sha256(shader_path.read_bytes()).hexdigest(),'native_vertices':count,
   'native_export':str(QA/'native-grass.json'),'native_export_sha256':hashlib.sha256((QA/'native-grass.json').read_bytes()).hexdigest(),
   'contact_m':contact.tolist(),'tall_tip_position_m':(native[tip,:3]/4096).tolist(),'tall_blade_height_m':float(roots[tip,3]),
   'tall_tip_displacement_m':float(dist[tip]),'outer_tip_max_displacement_m':float(np.max(dist[outer])),
   'max_displacement_m':float(np.max(dist)),'recovery_age_s':ages,'recovery_displacement_m':lengths,'native_visual_validation':False}
  (QA/'gpu-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert all(checks.values())
 finally:
  if context:ogl.wglMakeCurrent(dc,None);ogl.wglDeleteContext(context)
  user.ReleaseDC(hwnd,dc);user.DestroyWindow(hwnd)
if __name__=='__main__':main()
