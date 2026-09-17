# House 2: street-side ornament correction

Parent: `architecture/revision-001/installed.json`, FR3 SHA256 `fd442a3c6d80c55d89189c8cc6fa09f21a41491ff83f12df9ac230e4dffa25c9`.

The native wall is double-sided and some of its triangle normals point away from the street. Revision 1 used those normals to place four shields and consequently put them behind their supporting wall. This revision orients each support normal toward the actual street camera before projecting the outline onto the wall.

Only TIE tree 0 draw 40 groups 5, 6 and 7 change (draw 38 at LOD 3). There are four closed shield components per LOD: one in group 5, two in group 6, one in group 7. Exactly 2,064 triangles are removed and replaced. Already correct groups 4 and 9, all buildings, windows, collisions, original textures and BVH spheres remain unchanged.

## Evidence

- `visibility-validation.json`: 84 checks across four LODs, full native block, three street viewpoints. Every local ray hits the shield before its supporting wall. No faces are excluded. A separate facade about 11 m ahead naturally hides the left edge of group 7 from one angle; this is recorded, not discarded. Every shield is fully visible from at least one adjacent viewpoint.
- `fullblock-native.png` and `fullblock-open-angle.png`: readable geometry previews with emissive albedo, all source geometry retained. These are diagnostic Blender renders, not claims of in-game lighting validation. Editable scene: `house2-native-camera-fullblock.blend`.
- `ornament-validation.json`: four closed positive-volume components at each LOD.
- `geometry-validation.json`: finite, nondegenerate float32 geometry, consistent normals and normalized palette weights.
- `opening-validation.json`: all five existing window openings remain clear at every LOD.
- `bvh-coverage.json`: all 6,192 added vertex records remain inside original renderer visibility spheres, with at least 1.215 m margin.
- `staging/preservation.json`: all 163 native preservation checks pass.

Native camera: position `[2321,31,-16]`, target `[2342,27,-21]`, meters. Adjacent views offset the camera by two meters along its horizontal right vector.

`candidate.json` points to the staged FR3 with SHA256 `5dc29623b1613a818d766a98bc0a4dfb247f68eaaf66e399065920f286257b74`. Native deployment and final in-game visual validation belong to the root task.
