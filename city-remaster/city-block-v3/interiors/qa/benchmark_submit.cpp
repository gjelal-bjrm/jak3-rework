// Standalone QA helper, no engine linkage or runtime dependencies.
// Native submission avoids Python gaps between GPU timer start/end commands.
typedef unsigned int U;
typedef int I;
typedef float F;
extern "C" int _fltused=0;
struct Api {
  void (*begin_query)(U,U);
  void (*end_query)(U);
  void (*bind_vertex_array)(U);
  void (*bind_texture)(U,U);
  void (*uniform1i)(I,I);
  void (*uniform1f)(I,F);
  void (*uniform3f)(I,F,F,F);
  void (*draw_arrays)(U,I,I);
};
struct Locations {I offset,color,mode,roughness,emissive;};
struct Draw {U vao,texture;I first,count,mode,emissive;F roughness,color[3],offset[3];};
extern "C" __declspec(dllexport) void submit(Api* api,Locations* loc,Draw* draws,I count,U query){
  api->begin_query(0x88BF,query); // GL_TIME_ELAPSED
  for(I n=0;n<count;++n){
    const Draw& d=draws[n];
    api->bind_vertex_array(d.vao);api->bind_texture(0x0DE1,d.texture);
    api->uniform3f(loc->offset,d.offset[0],d.offset[1],d.offset[2]);
    api->uniform3f(loc->color,d.color[0],d.color[1],d.color[2]);
    api->uniform1i(loc->mode,d.mode);api->uniform1i(loc->emissive,d.emissive);
    api->uniform1f(loc->roughness,d.roughness);
    api->draw_arrays(4,d.first,d.count);
  }
  api->end_query(0x88BF);
}
