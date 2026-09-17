#include "CityFireSources.h"
#include <cassert>
#include <iostream>
#include <limits>

int main() {
  using namespace CityFireSources;
  const float origin[]{0, 0, 0, 1};
  const float identity[]{0, 0, 0, 1};
  const float up[]{-.70710678118f, 0, 0, .70710678118f};
  const auto fit = attachments[0];
  reset();
  assert(snapshot(6, origin).empty());
  assert(publish(fit.region, fit.aid, origin, identity, 1) == 0); // Native fallback until shader ready.
  assert(snapshot(6, origin).size() == 1);
  ready();
  assert(publish(fit.region, fit.aid, origin, up, 1) == 1);
  const auto moved = snapshot(6, origin).front();
  const auto expected = rotate(up, fit.offset);
  for (int k = 0; k < 3; ++k) assert(std::abs(moved.position[k] - expected[k]) < .00001f);
  assert(snapshot(1u << (3 - fit.region), origin).empty());
  auto bad = std::array<float, 4>{0, 0, std::numeric_limits<float>::quiet_NaN(), 1};
  assert(publish(fit.region, fit.aid, bad.data(), up, 1) == 0);
  assert(snapshot(6, origin).empty());
  assert(publish(0, fit.aid, origin, up, 1) == 0);
  assert(publish(fit.region, 1234567, origin, up, 1) == 0);
  // Unselected maps/actors cannot dereference absent transforms at map changes.
  assert(publish(0, fit.aid, nullptr, nullptr, 1) == 0);
  assert(publish(fit.region, 1234567, nullptr, nullptr, 1) == 0);
  for (const auto& a : attachments) assert(publish(a.region, a.aid, origin, up, 1) == 1);
  assert(snapshot(6, origin).size() == 61);
  assert(snapshot(2, origin).size() == 35);
  assert(snapshot(4, origin).size() == 26);
  for (int i = 0; i < 10; ++i) publish(fit.region, fit.aid, origin, up, 1);
  assert(snapshot(6, origin).size() == 61); // Same actor is updated, never duplicated.
  // Deactivation happens after a root may have been released.
  assert(publish(fit.region, fit.aid, nullptr, nullptr, 0) == 1);
  assert(snapshot(6, origin).size() == 60); // Stop/deactivate takes effect synchronously.
  const float distant_eye[]{400 * 4096.f, 0, 0, 1};
  assert(snapshot(6, distant_eye).empty());
  reset();
  assert(snapshot(6, origin).empty());
  std::cout << "PASS: actual C++ registry, 61 identities, 35/26 region split, activation, stop,\n"
               "native fallback, rejected transforms, quaternion anchors, reset and 300 m limit\n";
}
