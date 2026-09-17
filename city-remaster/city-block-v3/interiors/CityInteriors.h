#pragma once
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <map>
#include <memory>
#include <stdexcept>
#include <vector>
#include "common/log/log.h"
#include "common/util/FileUtil.h"
#include "common/util/json_util.h"
#include "game/graphics/opengl_renderer/BucketRenderer.h"

// Rooms are actual world-space geometry behind cut facade openings. Opaque depth
// keeps their furniture/inhabitants behind walls and visible through water.
class CityInteriors {
 public:
  ~CityInteriors(){for(auto& m:m_meshes)if(m.second.buffer)glDeleteBuffers(1,&m.second.buffer);for(auto& t:m_textures)glDeleteTextures(1,&t.second);if(m_vao)glDeleteVertexArrays(1,&m_vao);}
  void render(SharedRenderState* state){
    if(!state->has_pc_data||state->version!=GameVersion::Jak3)return;
    bool loaded=false;for(auto* level:state->loader->get_in_use_levels())if(level->level->level_name=="wascitya")loaded=true;
    if(!loaded)return;
    Guard guard;
    if(!m_attempted){m_attempted=true;try{initialize(state);}catch(const std::exception& e){lg::error("City interiors unavailable: {}",e.what());return;}}
    if(!m_shader||!m_shader->okay()||m_rooms.empty())return;
    m_shader->activate();m_program=GLuint(m_shader->id());glBindVertexArray(m_vao);
    glEnable(GL_DEPTH_TEST);glDepthFunc(GL_GEQUAL);glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);glDisable(GL_CULL_FACE);glDisable(GL_SCISSOR_TEST);glDisable(GL_STENCIL_TEST);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
    const auto eye=state->camera_pos/4096.f;
    glUniformMatrix4fv(location("room_camera"),1,GL_FALSE,state->prototype_camera);
    glUniform3fv(location("room_eye"),1,eye.data());
    glUniform3f(location("room_fog"),state->fog_color[0]/255.f,state->fog_color[1]/255.f,state->fog_color[2]/255.f);
    glUniform1i(location("material_tex"),0);
    float seconds=std::chrono::duration<float>(std::chrono::steady_clock::now()-m_start).count();
    int visible=0;
    // A room is drawn once. Its apertures only decide visibility; neither the
    // camera nor the aperture selects or relocates occupants and furniture.
    for(const auto& room:m_rooms){
      float d2=1.e20f;bool exposed=false;
      for(size_t index:room.windows){const auto& w=m_windows[index];float distance=0,front=0;
        for(int c=0;c<3;++c){float d=eye[c]-w.center[c];distance+=d*d;front+=d*w.basis[6+c];}
        d2=std::min(d2,distance);exposed|=distance<110.f*110.f&&front>=-.4f;
      }
      if(!exposed)continue;
      const auto& anchor=m_windows[room.anchor];
      glUniformMatrix3fv(location("room_basis"),1,GL_FALSE,anchor.basis.data());
      glUniform3fv(location("room_origin"),1,room.origin.data());
      glUniform1f(location("room_occupancy"),room.actors.empty()?.2f:1.f);
      glUniform3fv(location("room_lamp"),1,room.lamp.data());
      glUniform1f(location("room_side_light"),room.windows.size()>1?.24f:0.f);
      draw(m_meshes.at(room.mesh),{0,0,0},room.scale,0,seconds);
      if(d2<75.f*75.f)for(const auto& actor:room.actors)
        draw(m_meshes.at(actor.mesh),actor.position,{1,1,1},actor.yaw,seconds+actor.phase);
      ++visible;
    }
    if(visible&&!m_logged){lg::info("City interiors live: {} visible rooms, actual Spargus inhabitants, animated poses",visible);m_logged=true;}
  }
 private:
  using Vec3=std::array<float,3>;
  struct Material{Vec3 color{1,1,1};float roughness=.9f;int texture_mode=0;bool emissive=false;GLuint texture=0;};
  struct Draw{GLint first=0;GLsizei count=0;Material material;};
  struct Mesh{GLuint buffer=0;size_t vertices=0,frames=1;float duration=5.6f;std::vector<Draw> draws;};
  struct Window{Vec3 center{},origin{};std::array<float,9>basis{};bool inhabited=false;float height_scale=1,depth_scale=1;};
  struct Actor{std::string mesh;Vec3 position{};float yaw=0,phase=0;};
  struct Room{std::string mesh;size_t anchor=0;std::vector<size_t>windows;Vec3 origin{},scale{1,1,1},lamp{0,2.94f,-1.65f};std::vector<Actor>actors;};
  GLint location(const char* name){return glGetUniformLocation(m_program,name);}
  static std::string path(const std::string& name){return file_util::get_file_path({"custom_assets","jak3","city-interiors",name});}
  static json read_json(const std::string& name){auto bytes=file_util::read_binary_file(path(name));return json::parse(bytes.begin(),bytes.end());}
  GLuint texture(const std::string& name){
    auto it=m_textures.find(name);if(it!=m_textures.end())return it->second;
    auto bytes=file_util::read_binary_file(path(name));if(bytes.size()<8)throw std::runtime_error("short texture");
    uint32_t wh[2];std::memcpy(wh,bytes.data(),8);
    if(!wh[0]||!wh[1]||wh[0]>8192||wh[1]>8192||bytes.size()!=8+size_t(wh[0])*wh[1]*4)throw std::runtime_error("invalid RGBA texture");
    GLuint id;glGenTextures(1,&id);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,id);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,wh[0],wh[1],0,GL_RGBA,GL_UNSIGNED_BYTE,bytes.data()+8);glGenerateMipmap(GL_TEXTURE_2D);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
    m_textures[name]=id;return id;
  }
  Mesh load_mesh(const std::string& name){
    auto j=read_json(name+".json");Mesh m;m.vertices=j.at("vertex_count").get<size_t>();m.frames=j.value("frame_count",size_t(1));m.duration=j.value("duration_seconds",5.6f);
    auto bytes=file_util::read_binary_file(path(j.at("binary").get<std::string>()));
    if(bytes.size()!=m.vertices*m.frames*48||!m.vertices||!m.frames||m.duration<=0)throw std::runtime_error("invalid mesh layout");
    glGenBuffers(1,&m.buffer);glBindBuffer(GL_ARRAY_BUFFER,m.buffer);glBufferData(GL_ARRAY_BUFFER,bytes.size(),bytes.data(),GL_STATIC_DRAW);
    for(const auto& d:j.at("draws")){Draw out;out.first=d.at("first").get<int>();out.count=d.at("count").get<int>();
      if(out.first<0||out.count<=0||size_t(out.first)+out.count>m.vertices)throw std::runtime_error("invalid draw range");
      if(m.frames>1){out.material.texture_mode=3;out.material.texture=texture(d.at("texture").get<std::string>());}
      else {const auto& a=j.at("materials").at(d.at("material").get<int>());out.material.color=a.at("color").get<Vec3>();out.material.roughness=a.at("roughness");out.material.emissive=a.at("emissive");out.material.texture_mode=a.at("texture_kind");if(out.material.texture_mode)out.material.texture=texture(out.material.texture_mode==1?"wood.rgba":"fabric.rgba");}
      m.draws.push_back(out);
    }return m;
  }
  void initialize(SharedRenderState* s){
    m_shader=std::make_unique<Shader>("city_interior",s->version);if(!m_shader->okay())return;
    glGenVertexArrays(1,&m_vao);glBindVertexArray(m_vao);
    for(const char* name:{"lounge","conversation","sitting-male","conversing-male","conversing-female"})m_meshes.emplace(name,load_mesh(name));
    const auto config=read_json("runtime.json");
    std::map<std::string,size_t>indices;
    for(const auto& a:config.at("windows")){Window w;w.center=a.at("center").get<Vec3>();auto n=a.at("normal").get<Vec3>(),r=a.at("right").get<Vec3>();
      for(int c=0;c<3;++c){w.basis[c]=r[c];w.basis[3+c]=c==1?1.f:0.f;w.basis[6+c]=n[c];w.origin[c]=w.center[c]-.54f*n[c];}
      float h=a.at("height");w.origin[1]-=h*.5f+.1f;w.height_scale=(h+.6f)/3.65f;w.depth_scale=std::min(1.f,a.value("room_depth",3.65f)/3.65f);w.inhabited=a.at("inhabited");
      if(!indices.emplace(a.at("id").get<std::string>(),m_windows.size()).second)throw std::runtime_error("duplicate window");
      m_windows.push_back(w);
    }
    std::vector<bool>assigned(m_windows.size(),false);
    for(const auto& a:config.at("rooms")){Room room;room.mesh=a.at("mesh").get<std::string>();room.anchor=indices.at(a.at("anchor").get<std::string>());
      room.origin=m_windows[room.anchor].origin;room.scale=a.at("scale").get<Vec3>();room.lamp=a.at("lamp").get<Vec3>();
      for(const auto& id:a.at("windows")){size_t index=indices.at(id.get<std::string>());if(assigned[index])throw std::runtime_error("window belongs to two rooms");assigned[index]=true;room.windows.push_back(index);}
      if(room.windows.empty()||std::find(room.windows.begin(),room.windows.end(),room.anchor)==room.windows.end())throw std::runtime_error("invalid room anchor");
      if(!m_meshes.count(room.mesh))m_meshes.emplace(room.mesh,load_mesh(room.mesh));
      for(const auto& actor:a.at("actors")){Actor out;out.mesh=actor.at("mesh").get<std::string>();out.position=actor.at("position").get<Vec3>();out.yaw=actor.value("yaw",0.f);out.phase=actor.value("phase",0.f);if(!m_meshes.count(out.mesh))throw std::runtime_error("unknown occupant mesh");room.actors.push_back(out);}
      m_rooms.push_back(room);
    }
    if(std::find(assigned.begin(),assigned.end(),false)!=assigned.end())throw std::runtime_error("window has no room");
    lg::info("City interiors: {} windows share {} physical rooms",m_windows.size(),m_rooms.size());
    m_start=std::chrono::steady_clock::now();
  }
  void draw(const Mesh& m,const Vec3& offset,const Vec3& scale,float yaw,float time){
    glBindBuffer(GL_ARRAY_BUFFER,m.buffer);float phase=std::fmod(time/m.duration,1.f)*float(m.frames);size_t frame=size_t(phase),next=(frame+1)%m.frames;
    const size_t a=frame*m.vertices*48,b=next*m.vertices*48;
    const size_t offsets[6]={a,a+12,a+24,a+32,b,b+12};const int sizes[6]={3,3,2,4,3,3};
    for(GLuint i=0;i<6;++i){glEnableVertexAttribArray(i);glVertexAttribPointer(i,sizes[i],GL_FLOAT,GL_FALSE,48,reinterpret_cast<void*>(offsets[i]));}
    glUniform1f(location("pose_blend"),phase-float(frame));glUniform1f(location("object_yaw"),yaw);glUniform3fv(location("object_offset"),1,offset.data());glUniform3fv(location("object_scale"),1,scale.data());
    for(const auto& d:m.draws){const auto& material=d.material;glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,material.texture);
      glUniform3fv(location("material_color"),1,material.color.data());glUniform1f(location("roughness"),material.roughness);glUniform1i(location("texture_mode"),material.texture_mode);glUniform1i(location("emissive"),material.emissive?1:0);glDrawArrays(GL_TRIANGLES,d.first,d.count);
    }
  }
  struct Guard{
    GLint program,vao,buffer,active,texture,depth;GLboolean write,test,blend,cull,scissor,stencil,color[4];
    Guard(){glGetIntegerv(GL_CURRENT_PROGRAM,&program);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&vao);glGetIntegerv(GL_ARRAY_BUFFER_BINDING,&buffer);glGetIntegerv(GL_ACTIVE_TEXTURE,&active);glActiveTexture(GL_TEXTURE0);glGetIntegerv(GL_TEXTURE_BINDING_2D,&texture);glGetIntegerv(GL_DEPTH_FUNC,&depth);glGetBooleanv(GL_DEPTH_WRITEMASK,&write);glGetBooleanv(GL_COLOR_WRITEMASK,color);test=glIsEnabled(GL_DEPTH_TEST);blend=glIsEnabled(GL_BLEND);cull=glIsEnabled(GL_CULL_FACE);scissor=glIsEnabled(GL_SCISSOR_TEST);stencil=glIsEnabled(GL_STENCIL_TEST);}
    static void restore(GLenum flag,GLboolean value){if(value)glEnable(flag);else glDisable(flag);}
    ~Guard(){glUseProgram(program);glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,buffer);glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,texture);glActiveTexture(active);glDepthFunc(depth);glDepthMask(write);glColorMask(color[0],color[1],color[2],color[3]);restore(GL_DEPTH_TEST,test);restore(GL_BLEND,blend);restore(GL_CULL_FACE,cull);restore(GL_SCISSOR_TEST,scissor);restore(GL_STENCIL_TEST,stencil);}
  };
  bool m_attempted=false,m_logged=false;GLuint m_vao=0,m_program=0;
  std::unique_ptr<Shader>m_shader;std::map<std::string,Mesh>m_meshes;std::map<std::string,GLuint>m_textures;std::vector<Window>m_windows;std::vector<Room>m_rooms;
  std::chrono::steady_clock::time_point m_start;
};
