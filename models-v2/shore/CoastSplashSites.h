#pragma once
// Genere par models-v2/shore/build_shore_tables.py : sites natifs d eclaboussure sur les rochers de Spargus.
// x, y, z (m) ; tangente du rocher (xz) ; direction vers le large (xz).
struct CoastSplashSite { float x, y, z, tx, tz, sx, sz; };
inline constexpr int COAST_SPLASH_SITE_COUNT = 15;
inline constexpr CoastSplashSite COAST_SPLASH_SITES[15] = {
  {1728.89f, 8.46f, -407.27f, -0.9972f, 0.0753f, 0.3388f, -0.9409f},  // waswide-part-175
  {1706.11f, 8.46f, -399.47f, -0.4245f, 0.9054f, -0.9054f, -0.4245f},  // waswide-part-176
  {1691.75f, 8.46f, -395.23f, -0.1121f, 0.9937f, -0.8697f, -0.4936f},  // waswide-part-177
  {1657.12f, 8.46f, -402.69f, -0.9245f, -0.3811f, -0.8219f, -0.5697f},  // waswide-part-178
  {1637.58f, 8.46f, -407.44f, -0.9036f, -0.4284f, -0.7784f, -0.6277f},  // waswide-part-179
  {1626.87f, 8.46f, -413.63f, -0.9364f, -0.3509f, 0.7684f, -0.6399f},  // waswide-part-180
  {1625.92f, 8.46f, -470.12f, 0.3354f, 0.9421f, -0.9421f, 0.3354f},  // waswide-part-183
  {1618.42f, 8.46f, -488.14f, -0.9988f, 0.0490f, 0.1872f, -0.9823f},  // waswide-part-184
  {1605.00f, 8.46f, -493.50f, -0.8654f, 0.5011f, -0.8864f, 0.4630f},  // waswide-part-185
  {1590.81f, 8.46f, -490.78f, -0.2820f, 0.9594f, -0.8291f, 0.5591f},  // waswide-part-186
  {1744.06f, 8.46f, -467.69f, 0.8549f, -0.5188f, 0.9995f, -0.0310f},  // waswide-part-187
  {1716.48f, 8.46f, -469.22f, -0.6377f, 0.7703f, -0.7703f, -0.6377f},  // waswide-part-188
  {1738.28f, 8.46f, -472.72f, 0.8549f, -0.5188f, 0.8877f, -0.4605f},  // waswide-part-189
  {1470.76f, 6.99f, -519.01f, -0.3731f, -0.9278f, 0.9864f, 0.1645f},  // waswide-part-197
  {1461.62f, 9.18f, -537.36f, -0.8312f, -0.5560f, 0.3684f, -0.9297f},  // waswide-part-198
};
