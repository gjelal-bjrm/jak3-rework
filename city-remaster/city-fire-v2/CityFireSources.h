#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <mutex>
#include <vector>

// Live part-spawners publish only authorised city attachments. No static always-on
// lights are inferred merely because a city's FR3 happens to be resident.
namespace CityFireSources {
struct Attachment {
  int region;
  unsigned aid;
  std::array<float, 3> offset;
  float radius, height, footprint;
};
#include "CityFireAttachments.inc"
struct Source {
  std::array<float, 4> position{};
  float height = 0, footprint = 0, seed = 0;
  int region = 0;
  unsigned aid = 0;
  bool active = false;
};
inline std::array<Source, attachments.size()> sources{};
inline std::mutex mutex;
inline bool renderer_ready = false;

inline std::array<float, 3> rotate(const float* q, const std::array<float, 3>& v) {
  const float tx = 2.f * (q[1] * v[2] - q[2] * v[1]);
  const float ty = 2.f * (q[2] * v[0] - q[0] * v[2]);
  const float tz = 2.f * (q[0] * v[1] - q[1] * v[0]);
  return {v[0] + q[3] * tx + q[1] * tz - q[2] * ty,
          v[1] + q[3] * ty + q[2] * tx - q[0] * tz,
          v[2] + q[3] * tz + q[0] * ty - q[1] * tx};
}

inline int publish(int region, unsigned aid, const float* position, const float* quaternion,
                   int active) {
  std::lock_guard<std::mutex> guard(mutex);
  for (size_t i = 0; i < attachments.size(); ++i) {
    const auto& fit = attachments[i];
    if (fit.region != region || fit.aid != aid) continue;
    auto& source = sources[i];
    if (!active) { source.active = false; return renderer_ready ? 1 : 0; }
    for (int k = 0; k < 4; ++k) {
      if (!std::isfinite(position[k]) || !std::isfinite(quaternion[k])) {
        source.active = false;
        return 0; // Keep the native effect if the live transform cannot be represented.
      }
    }
    const auto offset = rotate(quaternion, fit.offset);
    source.position = {position[0] / 4096.f + offset[0],
                       position[1] / 4096.f + offset[1],
                       position[2] / 4096.f + offset[2], fit.radius};
    source.height = fit.height;
    source.footprint = fit.footprint;
    // Stable actor identity: sorting/culling cannot change a flame's phase.
    source.seed = float(aid % 997) * .07913f;
    source.region = region;
    source.aid = aid;
    source.active = true;
    return renderer_ready ? 1 : 0;
  }
  return 0; // Unselected maps, actors and groups remain entirely native.
}

inline void ready() {
  std::lock_guard<std::mutex> guard(mutex);
  renderer_ready = true;
}
inline void reset() {
  std::lock_guard<std::mutex> guard(mutex);
  for (auto& source : sources) source.active = false;
}
inline std::vector<Source> snapshot(unsigned visible_regions, const float* eye) {
  std::lock_guard<std::mutex> guard(mutex);
  std::vector<Source> result;
  for (const auto& source : sources) {
    if (!source.active || !(visible_regions & (1u << source.region))) continue;
    float d2 = 0;
    for (int k = 0; k < 3; ++k) {
      const float d = source.position[k] - eye[k] / 4096.f;
      d2 += d * d;
    }
    // The original group fades from 200 to 300 m. Match its far limit.
    if (d2 <= 300.f * 300.f) result.push_back(source);
  }
  // Back-to-front volumes; actor seed stays attached during sorting.
  std::sort(result.begin(), result.end(), [&](const Source& a, const Source& b) {
    float da = 0, db = 0;
    for (int k = 0; k < 3; ++k) {
      da += std::pow(a.position[k] - eye[k] / 4096.f, 2.f);
      db += std::pow(b.position[k] - eye[k] / 4096.f, 2.f);
    }
    return da > db;
  });
  return result;
}
} // namespace CityFireSources
