# R4: restored corner window and four more houses

Base record: `architecture/revision-003/installed.json`, FR3 `ce3ed2028a71f80b292ff5df34cbe70f3839de4973c930860bd7f871bdd42604`.

## Geometry delivered

- House 1's lateral window, frame and balcony are restored exactly to R2 geometry, UVs and source palette entries. This permits the runtime to present the same room through both corner windows.
- Four new real openings are cut into distinct native houses in the east, west, northern and low polygonal residential areas. Each has a slightly different sill and lintel profile. Native building shapes and colours are retained.
- Nine anchors now cover six houses. This is an expansion of real windows, not a claim that all six houses have been completely remodeled.

The native house instances are 0, 4, 3 and the polygonal building assembled from instances 58/59/60/70. The rounded tower originally surveyed was rejected because its elevated position and surrounding objects made it unsuitable for this first inhabited-window batch.

Only 322 existing triangles are replaced: 266 reverse R3 and 56 cut the four new openings across four LODs. There are 14,634 added triangles: 6,250 restore the exact R2 side window and 8,384 form the new cut facades and closed beveled frames. The bounded cutter leaves source triangles outside the aperture rectangle unchanged.

## Files

- `candidate.json`: staged native FR3 and pinned proofs. No live installation performed by this author task.
- `window-anchors.json`: five historical R2 anchors, unchanged, followed by four new anchors. Coordinates use world meters with Y up. New room depth is 3.5 m.
- `new-window-specs.json`: new houses, outward normals, opening dimensions, terrain height and proposed street viewpoints.
- `native-camera-views.json`: four game-camera views for native review.
- `four-street-houses.blend`: editable four-house geometry. The exact restored house 1 model remains in the pinned historical `architecture/spargus-houses-v3.blend`.
- `street-east.png`, `street-west.png`, `street-low.png`, `street-north.png`: full native street geometry previews with readable albedo work lighting. They intentionally have no runtime rooms or inhabitants. Native surfaces visible through the holes lie beyond the audited 3.5 m room depth.

## Validation

- 163 native preservation checks pass: collision, textures, other trees, original palettes and visibility bounds remain unchanged.
- All added vertices remain in the original renderer bounds, with a minimum 10.69 m margin.
- 40 opening checks pass: nine apertures, four LODs, plus source integrity checks.
- 16 street-view checks pass: four houses, four LODs, nine rays per view. No occluders are excluded.
- Eight restoration checks pass, including equality of all 17,734 house 1 triangles against R2 positions, UVs and palette sources; house 2 is untouched.
- Float32 geometry has no degenerate triangles, invalid normals or invalid palette weights.

Staged FR3: `46b986d81aa7b3edf5d85e1f387a3b8efc789f9657d1e861495e51c2a251ea72`.

The root task owns the shared room and inhabitants, package integration, live deployment, and final in-game review.
