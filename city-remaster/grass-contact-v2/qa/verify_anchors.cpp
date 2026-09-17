#include "../GrassAnchors.h"
#include <cassert>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
struct Vertex { float x,y,z,s,t; };
struct Draw { int tree_tex_id; uint32_t first_index_index,num_indices; };
struct Texture { std::string debug_name; };
struct Tree {
  struct { std::vector<Vertex> vertices; } unpacked;
  std::vector<Draw> static_draws;
  std::vector<uint32_t> indices;
};
int main(int argc,char** argv) {
  assert(argc==4);
  Tree tree;
  std::ifstream in(argv[1],std::ios::binary);
  uint32_t count=0;in.read(reinterpret_cast<char*>(&count),4);assert(count>0&&count%3==0);
  tree.unpacked.vertices.resize(count);in.read(reinterpret_cast<char*>(tree.unpacked.vertices.data()),count*sizeof(Vertex));assert(in.good());
  for(uint32_t i=0;i<count;++i){tree.indices.push_back(i);if(i%3==2)tree.indices.push_back(UINT32_MAX);}
  tree.static_draws.push_back({0,0,uint32_t(tree.indices.size())});
  std::vector<Texture> textures={{"market-shrub-orange-v1"}};
  auto begin=std::chrono::steady_clock::now();
  auto result=GrassAnchors::build(tree,textures,"wascitya");
  const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
  assert(result.blades>0&&result.affected_vertices>0&&result.max_height>2.f);
  size_t root_count=0;bool finite=true;float max_root_error=0.f;
  for(size_t i=0;i<count;++i){
    const auto& v=tree.unpacked.vertices[i];const auto& root=result.vertices[i];
    for(float x:root)finite=finite&&std::isfinite(x);
    if(std::abs(v.t-4096.f)<.05f&&root[3]>0.f){
      ++root_count;
      max_root_error=std::max(max_root_error,std::abs(v.y/4096.f-root[1]));
    }
  }
  assert(finite&&root_count>0&&max_root_error<.02f);
  assert(GrassAnchors::build(tree,textures,"waspala").vertices.empty());
  textures[0].debug_name="city-cactus-green-v2";
  assert(GrassAnchors::build(tree,textures,"wascitya").vertices.empty());
  std::ofstream out(argv[2],std::ios::binary);
  out.write(reinterpret_cast<char*>(result.vertices.data()),result.vertices.size()*sizeof(GrassAnchors::Attribute));out.close();
  std::ofstream report(argv[3]);report<<std::setprecision(8);
  report<<"{\n  \"status\": \"passed\",\n  \"native_vertices\": "<<count
    <<",\n  \"blades\": "<<result.blades<<",\n  \"affected_vertices\": "<<result.affected_vertices
    <<",\n  \"unanchored_components\": "<<result.unanchored_components
    <<",\n  \"max_blade_height_m\": "<<result.max_height
    <<",\n  \"root_vertices\": "<<root_count<<",\n  \"max_root_y_error_m\": "<<max_root_error
    <<",\n  \"mesh_load_preparation_ms\": "<<ms
    <<",\n  \"palace_and_cactus_excluded\": true,\n  \"native_visual_validation\": false\n}\n";
  std::cout<<"Native anchor extraction PASS: "<<result.blades<<" blades; "<<result.affected_vertices<<" vertices; "<<ms<<" ms\n";
}
