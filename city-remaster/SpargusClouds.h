#pragma once
#include <memory>
#include "game/graphics/opengl_renderer/BucketRenderer.h"
#include "game/graphics/opengl_renderer/background/LiquidSnapshot.h"
#include "game/graphics/opengl_renderer/loader/Loader.h"
#include "common/log/log.h"

// A private replacement for the procedural cloud mask on the Jak 3 sky bucket.
// The texture pool, GOAL sky geometry, sun sprites and original masks are untouched.
class SpargusClouds {
 public:
  ~SpargusClouds() {
    if (texture)glDeleteTextures(1,&texture);
    if (framebuffer)glDeleteFramebuffers(1,&framebuffer);
    if (vao)glDeleteVertexArrays(1,&vao);
    if (sampler)glDeleteSamplers(1,&sampler);
  }
  GLuint replacement(SharedRenderState* state,GLuint original,u32 tbp,bool sky_bucket) {
    if (!sky_bucket || state->version!=GameVersion::Jak3 || !state->has_pc_data)return original;
    if (region_frame!=state->frame_idx) {
      region_frame=state->frame_idx;
      const auto eye=state->camera_pos/4096.f;
      region=false;
      if(eye.x()>1400.f && eye.x()<2450.f && eye.y()>-60.f && eye.y()<220.f &&
         eye.z()>-1250.f && eye.z()<500.f) {
        for (const auto* level:state->loader->get_in_use_levels()) {
          const auto& name=level->level->level_name;
          if(name=="wascitya" || name=="wascityb" || name=="lwasbbv")region=true;
        }
      }
    }
    if(!region)return original;
    const auto name=state->texture_pool->get_debug_texture_name_from_tbp(tbp);
    if(name!="PC-ANIM/clouds" && name!="PC-ANIM/clouds-hires")return original;
    if(rendered_frame==state->frame_idx && source==original)return texture;

    GLint old_program,old_vao,old_draw,old_read,old_active,old_texture0,old_sampler0,viewport[4];
    GLboolean color_mask[4];
    glGetIntegerv(GL_CURRENT_PROGRAM,&old_program);glGetIntegerv(GL_VERTEX_ARRAY_BINDING,&old_vao);
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING,&old_draw);glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING,&old_read);
    glGetIntegerv(GL_ACTIVE_TEXTURE,&old_active);glGetIntegerv(GL_VIEWPORT,viewport);
    glGetBooleanv(GL_COLOR_WRITEMASK,color_mask);
    glActiveTexture(GL_TEXTURE0);glGetIntegerv(GL_TEXTURE_BINDING_2D,&old_texture0);
    glGetIntegeri_v(GL_SAMPLER_BINDING,0,&old_sampler0);
    const GLenum flags[]={GL_DEPTH_TEST,GL_BLEND,GL_CULL_FACE,GL_SCISSOR_TEST,GL_STENCIL_TEST,GL_FRAMEBUFFER_SRGB};
    GLboolean enabled[6];
    for(int i=0;i<6;i++){enabled[i]=glIsEnabled(flags[i]);glDisable(flags[i]);}
    if(!shader) {
      shader=std::make_unique<Shader>("spargus_clouds",state->version);
      glGenVertexArrays(1,&vao);glGenFramebuffers(1,&framebuffer);glGenTextures(1,&texture);
      glBindTexture(GL_TEXTURE_2D,texture);
      glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA16F,kSize,kSize,0,GL_RGBA,GL_FLOAT,nullptr);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
      glBindFramebuffer(GL_DRAW_FRAMEBUFFER,framebuffer);
      glFramebufferTexture2D(GL_DRAW_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
      ASSERT(glCheckFramebufferStatus(GL_DRAW_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE);
      glGenSamplers(1,&sampler);
      glSamplerParameteri(sampler,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);
      glSamplerParameteri(sampler,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
      glSamplerParameteri(sampler,GL_TEXTURE_WRAP_S,GL_REPEAT);
      glSamplerParameteri(sampler,GL_TEXTURE_WRAP_T,GL_REPEAT);
      lg::info("Spargus clouds: native {} -> private {}x{} density, native sky colours retained",name,kSize,kSize);
    }
    if(shader->okay()) {
      glBindFramebuffer(GL_DRAW_FRAMEBUFFER,framebuffer);glViewport(0,0,kSize,kSize);
      glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glBindVertexArray(vao);
      shader->activate();glBindTexture(GL_TEXTURE_2D,original);glBindSampler(0,sampler);
      glUniform1i(glGetUniformLocation(shader->id(),"native_clouds"),0);
      glUniform1f(glGetUniformLocation(shader->id(),"cloud_time"),LiquidSnapshot::seconds());
      glDrawArrays(GL_TRIANGLES,0,3);
      // Mips must be generated after detaching from the active draw framebuffer.
      glBindFramebuffer(GL_DRAW_FRAMEBUFFER,old_draw);glBindTexture(GL_TEXTURE_2D,texture);
      glGenerateMipmap(GL_TEXTURE_2D);
      rendered_frame=state->frame_idx;source=original;
    }
    glBindSampler(0,old_sampler0);glBindTexture(GL_TEXTURE_2D,old_texture0);glActiveTexture(old_active);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER,old_draw);glBindFramebuffer(GL_READ_FRAMEBUFFER,old_read);
    glViewport(viewport[0],viewport[1],viewport[2],viewport[3]);
    glUseProgram(old_program);glBindVertexArray(old_vao);
    glColorMask(color_mask[0],color_mask[1],color_mask[2],color_mask[3]);
    for(int i=0;i<6;i++){if(enabled[i])glEnable(flags[i]);else glDisable(flags[i]);}
    return shader->okay()?texture:original;
  }
 private:
  static constexpr int kSize=1024;
  std::unique_ptr<Shader> shader;
  GLuint texture=0,framebuffer=0,vao=0,sampler=0,source=0;
  u64 rendered_frame=UINT64_MAX,region_frame=UINT64_MAX;
  bool region=false;
};
