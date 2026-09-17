const int max_city_fires=64;
uniform int fire_count;
uniform vec4 fire_sources[max_city_fires];
uniform float fire_heights[max_city_fires];
uniform float fire_footprints[max_city_fires];
uniform float fire_seeds[max_city_fires];
uniform int fire_light_count;
uniform int fire_light_indices[8];
float fireFuelSurface(int id,vec2 xz) { return 0.0; }
float fireFloor(int id) { return 0.0; }
