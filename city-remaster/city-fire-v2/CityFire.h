#pragma once
#include "game/graphics/opengl_renderer/background/LiquidSnapshot.h"
#include "game/graphics/opengl_renderer/CityFireSources.h"

// The accepted palace recipe, supplied by active city part-spawners. Kept in a
// separate pass so the 24 palace volumes and fitted coal surfaces stay untouched.
class CityFire {
 public:
  ~CityFire() {
    if (m_vao) glDeleteVertexArrays(1, &m_vao);
    if (m_timer[0]) glDeleteQueries(2, m_timer);
  }
  void render(SharedRenderState* state) {
    if (!state->has_pc_data || state->version != GameVersion::Jak3 ||
        m_render_frame == state->frame_idx) return;
    unsigned regions = 0;
    for (auto* level : state->loader->get_in_use_levels()) {
      if (level->level->level_name == "wascitya") regions |= 1u << 1;
      if (level->level->level_name == "wascityb") regions |= 1u << 2;
    }
    if (!regions) return;
    auto sources = CityFireSources::snapshot(regions, state->camera_pos.data());
    if (sources.empty()) return;
    ASSERT(sources.size() <= 64);
    m_render_frame = state->frame_idx;
    GLint program, vao, depth_func, active, src_rgb, dst_rgb, src_alpha, dst_alpha, eq_rgb, eq_alpha;
    GLboolean depth_write, color_mask[4];
    glGetIntegerv(GL_CURRENT_PROGRAM, &program); glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
    glGetIntegerv(GL_DEPTH_FUNC, &depth_func); glGetIntegerv(GL_ACTIVE_TEXTURE, &active);
    glGetIntegerv(GL_BLEND_SRC_RGB, &src_rgb); glGetIntegerv(GL_BLEND_DST_RGB, &dst_rgb);
    glGetIntegerv(GL_BLEND_SRC_ALPHA, &src_alpha); glGetIntegerv(GL_BLEND_DST_ALPHA, &dst_alpha);
    glGetIntegerv(GL_BLEND_EQUATION_RGB, &eq_rgb); glGetIntegerv(GL_BLEND_EQUATION_ALPHA, &eq_alpha);
    glGetBooleanv(GL_DEPTH_WRITEMASK, &depth_write); glGetBooleanv(GL_COLOR_WRITEMASK, color_mask);
    const GLenum flags[] = {GL_DEPTH_TEST, GL_BLEND, GL_CULL_FACE, GL_SCISSOR_TEST,
                           GL_STENCIL_TEST, GL_PROGRAM_POINT_SIZE};
    GLboolean enabled[6];
    for (int i = 0; i < 6; i++) { enabled[i] = glIsEnabled(flags[i]); glDisable(flags[i]); }
    if (!m_volume) {
      m_volume = std::make_unique<Shader>("city_fire", state->version);
      m_light = std::make_unique<Shader>("city_fire_lighting", state->version);
      m_embers = std::make_unique<Shader>("city_fire_embers", state->version);
      glGenVertexArrays(1, &m_vao); glGenQueries(2, m_timer);
      CityFireSources::ready();
      lg::info("City fire: accepted palace recipe, 61 fitted active attachments, 8 local lights; before water");
    }
    if (m_logged_sources != int(sources.size())) {
      lg::info("City fire live: {} active volumes in loaded city regions; nearest AID {} at {:.3f}, {:.3f}, {:.3f}",
        sources.size(), sources.back().aid, sources.back().position[0], sources.back().position[1], sources.back().position[2]);
      m_logged_sources = int(sources.size());
    }
    std::array<std::array<float, 4>, 64> positions{};
    std::array<float, 64> heights{}, footprints{}, seeds{};
    std::array<GLint, 8> lights{};
    int light_count = 0;
    for (size_t i = 0; i < sources.size(); ++i) {
      positions[i] = sources[i].position;
      heights[i] = sources[i].height; footprints[i] = sources[i].footprint; seeds[i] = sources[i].seed;
    }
    for (int i = int(sources.size()) - 1; i >= 0 && light_count < 8; --i) {
      float d2 = 0;
      for (int k = 0; k < 3; ++k) {
        const float d = positions[i][k] - state->camera_pos[k] / 4096.f;
        d2 += d * d;
      }
      if (d2 < 48.f * 48.f) lights[light_count++] = i;
    }
    glBindVertexArray(m_vao); glDepthMask(GL_FALSE); glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    const float seconds = LiquidSnapshot::seconds();
    if (m_timer_pending) {
      GLint ready = 0; glGetQueryObjectiv(m_timer[1], GL_QUERY_RESULT_AVAILABLE, &ready);
      if (ready) {
        GLuint64 start = 0, end = 0;
        glGetQueryObjectui64v(m_timer[0], GL_QUERY_RESULT, &start);
        glGetQueryObjectui64v(m_timer[1], GL_QUERY_RESULT, &end);
        const double ms = double(end - start) / 1000000.0;
        m_time_sum += ms; m_time_max = std::max(m_time_max, ms); ++m_time_count; m_timer_pending = false;
        if (m_time_count == 12) lg::info("City fire GPU: {} samples, mean {:.2f} ms, max {:.2f} ms at {}x{}",
          m_time_count, m_time_sum / m_time_count, m_time_max, state->render_fb_w, state->render_fb_h);
      }
    }
    const bool measure = !m_timer_pending && m_time_count < 12 && state->frame_idx % 30 == 0;
    if (measure) glQueryCounter(m_timer[0], GL_TIMESTAMP);
    auto bind = [&](Shader& shader) {
      shader.activate(); const auto id = shader.id();
      glUniformMatrix4fv(glGetUniformLocation(id, "pc_camera"), 1, GL_FALSE, state->prototype_camera);
      glUniform4fv(glGetUniformLocation(id, "cam_trans"), 1, state->camera_pos.data());
      glUniform1f(glGetUniformLocation(id, "fire_time"), seconds);
      glUniform1i(glGetUniformLocation(id, "fire_count"), int(sources.size()));
      glUniform4fv(glGetUniformLocation(id, "fire_sources"), int(sources.size()), positions[0].data());
      glUniform1fv(glGetUniformLocation(id, "fire_heights"), int(sources.size()), heights.data());
      glUniform1fv(glGetUniformLocation(id, "fire_footprints"), int(sources.size()), footprints.data());
      glUniform1fv(glGetUniformLocation(id, "fire_seeds"), int(sources.size()), seeds.data());
      glUniform1i(glGetUniformLocation(id, "fire_light_count"), light_count);
      glUniform1iv(glGetUniformLocation(id, "fire_light_indices"), 8, lights.data());
      m_scene.bind(state, id);
    };
    bind(*m_light); glDrawArrays(GL_TRIANGLES, 0, 3);
    bind(*m_volume);
    glEnable(GL_BLEND); glBlendEquation(GL_FUNC_ADD); glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
    glDrawArraysInstanced(GL_TRIANGLES, 0, 6, int(sources.size()));
    bind(*m_embers);
    glUniform1f(glGetUniformLocation(m_embers->id(), "viewport_height"), float(state->render_fb_h));
    glEnable(GL_DEPTH_TEST); glDepthFunc(GL_GEQUAL); glEnable(GL_PROGRAM_POINT_SIZE);
    glDrawArrays(GL_POINTS, 0, int(sources.size()) * 7);
    if (measure) { glQueryCounter(m_timer[1], GL_TIMESTAMP); m_timer_pending = true; }
    glUseProgram(program); glBindVertexArray(vao); glDepthFunc(depth_func); glDepthMask(depth_write);
    glBlendFuncSeparate(src_rgb, dst_rgb, src_alpha, dst_alpha); glBlendEquationSeparate(eq_rgb, eq_alpha);
    glColorMask(color_mask[0], color_mask[1], color_mask[2], color_mask[3]); glActiveTexture(active);
    for (int i = 0; i < 6; i++) { if (enabled[i]) glEnable(flags[i]); else glDisable(flags[i]); }
  }
 private:
  std::unique_ptr<Shader> m_volume, m_light, m_embers;
  LiquidSnapshot m_scene;
  GLuint m_vao = 0;
  u64 m_render_frame = UINT64_MAX;
  GLuint m_timer[2] = {};
  bool m_timer_pending = false;
  int m_time_count = 0, m_logged_sources = -1;
  double m_time_sum = 0, m_time_max = 0;
};
