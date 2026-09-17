#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <mutex>
#include "common/log/log.h"
#include "game/graphics/opengl_renderer/background/LiquidSnapshot.h"

// A bounded snapshot copied at Jak's normal post-physics hook. No camera proxy,
// GOAL heap offsets, particle hooks or render-thread reads of mutable game data.
namespace GrassContacts {
constexpr size_t kCount = 16;
inline std::array<std::array<float, 4>, kCount> samples{};
inline std::array<float, 3> latest{};
inline std::mutex mutex;
inline size_t count = 0;
inline size_t next = 0;
inline int region = 0;
inline float last_seen = -1000.f;
inline float last_sample = -1000.f;

inline void push(const float* packet, int level) {
  if (level != 1 && level != 2) return;
  const float x = packet[0] / 4096.f, y = packet[1] / 4096.f,
              z = packet[2] / 4096.f, now = LiquidSnapshot::seconds();
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)) return;
  std::lock_guard<std::mutex> lock(mutex);
  const float dx = x - latest[0], dy = y - latest[1], dz = z - latest[2];
  // A scene change, pause or teleport must not leave a trail across the city.
  if (region != level || now - last_seen > .25f || dx*dx + dy*dy + dz*dz > 25.f) {
    count = next = 0;
    last_sample = -1000.f;
  }
  region = level;
  latest = {x, y, z};
  last_seen = now;
  if (now - last_sample >= .0625f || count == 0) {
    samples[next] = {x, y, z, now};
    next = (next + 1) % kCount;
    count = std::min(count + 1, kCount);
    last_sample = now;
  }
}

inline void bind(GLuint program, int material_region) {
  const GLint count_location = glGetUniformLocation(program, "grass_contact_count");
  if (count_location < 0) return;  // The same material binder serves other trees.
  std::array<std::array<float, 4>, kCount> snapshot{};
  size_t active = 0;
  const float now = LiquidSnapshot::seconds();
  {
    std::lock_guard<std::mutex> lock(mutex);
    if (material_region != 0 && region == material_region) {
      for (size_t i = 0; i < count; ++i) {
        const float age = now - samples[i][3];
        if (age >= 0.f && age < 1.f) snapshot[active++] = samples[i];
      }
    }
  }
  glUniform1i(count_location, static_cast<GLint>(active));
  glUniform1f(glGetUniformLocation(program, "grass_contact_time"), now);
  if (active) {
    glUniform4fv(glGetUniformLocation(program, "grass_contacts"),
                 static_cast<GLsizei>(active), snapshot[0].data());
    static bool reported = false;
    if (!reported) {
      lg::info("Remaster grass contact: Jak position {:.3f}, {:.3f}, {:.3f}; region {}; {} shader samples",
               snapshot[0][0], snapshot[0][1], snapshot[0][2], material_region, active);
      reported = true;
    }
  }
}
}  // namespace GrassContacts
