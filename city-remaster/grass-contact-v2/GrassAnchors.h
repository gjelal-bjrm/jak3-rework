#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <vector>

// Derive each closed blade's root from the geometry actually loaded. The bridge
// stores triangle corners independently, so weld only identical positions for
// this auxiliary attribute. Neither native vertices nor topology are changed.
namespace GrassAnchors {
using Attribute = std::array<float, 4>;  // root XYZ in metres, blade height
struct Key {
  std::array<uint32_t, 3> words;
  bool operator==(const Key& other) const { return words == other.words; }
};
struct Hash {
  size_t operator()(const Key& key) const {
    size_t h = 0;
    for (const auto word : key.words) h ^= size_t(word) + 0x9e3779b9u + (h << 6) + (h >> 2);
    return h;
  }
};
template <typename Vertex>
Key key_for(const Vertex& v) {
  Key result{};
  const float p[3] = {v.x == 0.f ? 0.f : v.x, v.y == 0.f ? 0.f : v.y,
                      v.z == 0.f ? 0.f : v.z};
  std::memcpy(result.words.data(), p, sizeof(p));
  return result;
}
struct Node {
  uint32_t parent;
  std::array<float, 3> p;
  bool is_root;
};
inline uint32_t find(std::vector<Node>& nodes, uint32_t index) {
  while (nodes[index].parent != index) {
    nodes[index].parent = nodes[nodes[index].parent].parent;
    index = nodes[index].parent;
  }
  return index;
}
inline void join(std::vector<Node>& nodes, uint32_t a, uint32_t b) {
  a = find(nodes, a); b = find(nodes, b);
  if (a != b) nodes[std::max(a, b)].parent = std::min(a, b);
}
struct Result {
  std::vector<Attribute> vertices;
  size_t blades = 0;
  size_t affected_vertices = 0;
  size_t unanchored_components = 0;
  float max_height = 0.f;
};

template <typename Tree, typename Textures>
Result build(const Tree& tree, const Textures& textures, const std::string& level) {
  Result result;
  if (level != "wascitya" && level != "wascityb") return result;
  std::vector<const typename std::decay_t<decltype(tree.static_draws)>::value_type*> draws;
  for (const auto& draw : tree.static_draws) {
    if (draw.tree_tex_id >= 0 && size_t(draw.tree_tex_id) < textures.size() &&
        textures[draw.tree_tex_id].debug_name == "market-shrub-orange-v1") draws.push_back(&draw);
  }
  if (draws.empty()) return result;
  const auto& vertices = tree.unpacked.vertices;
  result.vertices.resize(vertices.size(), {0.f, 0.f, 0.f, 0.f});
  std::unordered_map<Key, uint32_t, Hash> welded;
  std::vector<Node> nodes;
  auto vertex_node = [&](uint32_t index) {
    const auto& v = vertices.at(index);
    const auto key = key_for(v);
    const auto found = welded.find(key);
    const bool is_root = std::abs(v.t - 4096.f) < .05f;
    if (found != welded.end()) {
      nodes[found->second].is_root = nodes[found->second].is_root || is_root;
      return found->second;
    }
    const uint32_t id = uint32_t(nodes.size());
    welded.emplace(key, id);
    nodes.push_back({id, {v.x / 4096.f, v.y / 4096.f, v.z / 4096.f}, is_root});
    return id;
  };
  for (const auto* draw : draws) {
    uint32_t previous[2]{};
    size_t run = 0;
    for (size_t i = draw->first_index_index; i < size_t(draw->first_index_index) + draw->num_indices; ++i) {
      const uint32_t index = tree.indices.at(i);
      if (index == UINT32_MAX) { run = 0; continue; }
      const uint32_t node = vertex_node(index);
      if (run >= 2) { join(nodes, previous[0], node); join(nodes, previous[1], node); }
      previous[0] = previous[1]; previous[1] = node; ++run;
    }
  }
  struct Bounds {
    std::array<double, 3> root_sum{};
    size_t roots = 0;
    float max_y = -std::numeric_limits<float>::infinity();
  };
  std::vector<Bounds> bounds(nodes.size());
  for (uint32_t i = 0; i < nodes.size(); ++i) {
    auto& b = bounds[find(nodes, i)];
    b.max_y = std::max(b.max_y, nodes[i].p[1]);
    if (nodes[i].is_root) {
      ++b.roots;
      for (int axis = 0; axis < 3; ++axis) b.root_sum[axis] += nodes[i].p[axis];
    }
  }
  std::vector<Attribute> roots(nodes.size(), {0.f, 0.f, 0.f, 0.f});
  for (size_t i = 0; i < bounds.size(); ++i) {
    if (nodes[i].parent != i) continue;
    if (!bounds[i].roots) { ++result.unanchored_components; continue; }
    auto& root = roots[i];
    for (int axis = 0; axis < 3; ++axis) root[axis] = float(bounds[i].root_sum[axis] / bounds[i].roots);
    root[3] = std::max(.05f, bounds[i].max_y - root[1]);
    result.max_height = std::max(result.max_height, root[3]);
    ++result.blades;
  }
  for (const auto* draw : draws) {
    for (size_t i = draw->first_index_index; i < size_t(draw->first_index_index) + draw->num_indices; ++i) {
      const uint32_t index = tree.indices[i];
      if (index == UINT32_MAX) continue;
      const auto node = welded.at(key_for(vertices[index]));
      const auto& root = roots[find(nodes, node)];
      if (root[3] > 0.f && result.vertices[index][3] == 0.f) ++result.affected_vertices;
      result.vertices[index] = root;
    }
  }
  return result;
}
}  // namespace GrassAnchors
