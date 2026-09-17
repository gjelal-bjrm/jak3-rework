#pragma once
#include "common/custom_data/Tfrag3Data.h"
#include "common/log/log.h"
#include "game/graphics/opengl_renderer/BucketRenderer.h"
#include "PalaceMaterialAudit.h"
#include "LiquidSnapshot.h"

// Cache static scenery classifications at level load. Animated liquids,
// characters and other levels sharing the shader programs keep their own path.
class PalaceMaterials {
 public:
  void load(const tfrag3::Level& level) {
    m_kinds.clear();
    m_names.clear();
    m_high_res.clear();
    const bool market = level.level_name == "wascityb";
    if (level.level_name != "waspala" && !market) return;
    int count=0, high_res=0;
    for (const auto& texture : level.textures) {
      // Only newly authored, dedicated market materials opt in. Native city
      // atlases also cover untouched scenery and must retain their own path.
      const int kind=market ? classify_market(texture.debug_name) : classify(texture.debug_name);
      m_kinds.push_back(kind);
      m_names.push_back(texture.debug_name);
      m_high_res.push_back(std::max(texture.w,texture.h)>=512);
      if (kind) { ++count; if (std::max(texture.w,texture.h)>=512) ++high_res; }
    }
    static bool reported_palace=false, reported_market=false;
    bool& reported=market ? reported_market : reported_palace;
    if (!reported && count) {
      lg::info("Remaster material response [{}]: {} static materials, {} textures at 512px or above",level.level_name,count,high_res);
      reported=true;
    }
  }
  void bind(GLuint program, int texture, const SharedRenderState* state) const {
    const int kind=state->version==GameVersion::Jak3 && texture>=0 &&
        size_t(texture)<m_kinds.size() ? m_kinds[texture] : 0;
    glUniform1i(glGetUniformLocation(program,"palace_material"),kind);
    const bool palm=kind && (m_names[texture]=="waspala-palmplant-leaf-02" || m_names[texture]=="waspala-shrub-plant" || m_names[texture]=="for-shrub-moss");
    const bool market_shrub=kind && m_names[texture]=="market-shrub-orange-v1";
    const bool market_wind=kind && m_names[texture]=="market-palm-leaf-v1";
    glUniform1i(glGetUniformLocation(program,"market_wind_material"),market_wind);
    glUniform1i(glGetUniformLocation(program,"palace_foliage"),market_shrub?2:(palm?1:0));
    if(palm || market_shrub)glUniform1f(glGetUniformLocation(program,"palace_time"),LiquidSnapshot::seconds());
    PalaceMaterialAudit::bind(program,kind ? m_names[texture] : std::string(),kind);
    // Some PS2 scenery draws explicitly select nearest filtering. Retaining it
    // makes HD albedo and derivative normals pixelate and shimmer at close range.
    if(kind && m_high_res[texture]) {
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR_MIPMAP_LINEAR);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    }
    // These private remaster textures use authored, repeating UVs. Native
    // atlases and the leaf/shrub alpha textures keep their original wrap.
    if (kind && (m_names[texture]=="market-palm-trunk-v1" ||
                 m_names[texture]=="market-support-wood-v1" ||
                 m_names[texture]=="market-support-metal-v1")) {
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);
      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);
    }
    if (kind) glUniform3f(glGetUniformLocation(program,"palace_eye"),
        state->camera_pos[0]/4096.f,state->camera_pos[1]/4096.f,state->camera_pos[2]/4096.f);
  }
 private:
  static int classify_market(const std::string& name) {
    if (name=="market-support-wood-v1" || name=="market-palm-trunk-v1") return 2;
    if (name=="market-support-metal-v1") return 3;
    if (name=="market-palm-leaf-v1" || name=="market-shrub-orange-v1") return 5;
    return 0;
  }
  static int classify(const std::string& name) {
    if (name=="waspala-fire-coal") return 0;
    if (name=="waspala-fire-holder01" || name=="waspala-fire-holder03") return 3;
    if (name.rfind("waspala-cliff-rock",0)==0 || name=="waspala-small-rocks" ||
        name=="wascity-outerwall-rock") return 7;
    if (name=="for-shrub-moss" || name=="waspala-shrub-plant" ||
        name=="waspala-palmplant-leaf-02" || name=="waspala-palmtree-beard") return 5;
    if (name=="waspala-glass-03") return 4;
    if (name=="waspala-throne-cushion") return 6;
    if (name=="waspala-throne-back-03" || name=="waspala-throne-cap") return 3;
    if (name=="waspala-throne-base" || name=="waspala-throne-back-02") return 2;
    if (name=="waspala-palmtree-trunk-01" || name=="waspala-branch-01" ||
        name=="waspala-wheel-paddle") return 2;
    if (name.rfind("waspala-",0)!=0 && name.rfind("common_sandstone_",0)!=0 &&
        name!="wascity-outerwall-rock") return 0;
    if (name.find("water")!=std::string::npos || name.find("dust")!=std::string::npos) return 0;
    if (name.find("metal")!=std::string::npos || name.find("bolt")!=std::string::npos ||
        name.find("chain")!=std::string::npos || name.find("elevator")!=std::string::npos ||
        name.find("wheel")!=std::string::npos || name=="waspala-column-plate" ||
        name=="waspala-column-piece") return 3;
    return 1;
  }
  std::vector<int> m_kinds;
  std::vector<std::string> m_names;
  std::vector<bool> m_high_res;
};
