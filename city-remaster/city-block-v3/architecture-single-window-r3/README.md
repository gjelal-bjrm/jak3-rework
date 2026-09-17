# One inhabited window per floor: close house 1's lateral opening

Parent: `architecture/revision-002/installed.json`, FR3 SHA256 `5dc29623b1613a818d766a98bc0a4dfb247f68eaaf66e399065920f286257b74`.

This revision closes `wca-house1-east-room`, centered at `[2272.98,27.3,16.1]`, and removes its entire authored frame and balcony. The wall is reconstructed from the native pre-opening house source. The west window on the same floor and the upper window remain intact. House 2 is unchanged.

## Bounded authoring

The pinned historical Blender author is replayed exactly, verified against the original architecture patch, then replayed with only the east window omitted. Only the triangle difference is exported. It replaces 6,250 triangles with 266 native facade triangles in TIE tree 1, group 1, draw 9 and draw 12 (draw 11 at LOD 3). Unchanged house triangles are retained byte-identically; there is no whole-house overwrite.

Editable project: `house1-single-window.blend`. `window-anchors.json` contains the four remaining historical records verbatim; the original five-anchor file is never modified.

## Validation

- Historical author reproduces the existing house exactly in all four LODs.
- `closed-window-validation.json` proves the complete final house matches the author result without the lateral frame and balcony, and verifies 196 rays hit the original native wall surface within 5 mm.
- `opening-validation.json`: all four retained openings remain clear in all four LODs; 20 checks pass.
- `geometry-validation.json`: no degenerate float32 faces, invalid normals or palette weights.
- `bvh-coverage.json`: all replacement vertices fit the unchanged renderer bounds with at least 14.43 m margin.
- `staging/preservation.json`: all 163 native preservation checks pass.

Staged FR3 SHA256: `ce3ed2028a71f80b292ff5df34cbe70f3839de4973c930860bd7f871bdd42604`. Deployment, removal of the obsolete runtime interior/inhabitants, and native visual validation remain with the root task.
