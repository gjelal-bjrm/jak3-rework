# WCB — complete palm coverage

This isolated candidate extends the reviewed complete market palms to the rest
of WCB. It changes **13 native palm instances**, representing **11 distinct
positions**, and retains the two already remastered market palms unchanged.
WCB therefore has all 15 native palm instances covered after this candidate is
installed. Native culling contains two pairs of spatially coincident palms;
their identities, groups and matrices remain separate, with identical detailed
silhouettes for each coincident pair.

## Candidate and evidence

- `candidate.json` records the complete parent/output/patch/audit hash chain.
- Immutable parent: `city-remaster/staging/market-static-003/wascityb.fr3`,
  SHA256 `de7ab0fd18e6f6400da5738c5a3b8446c7fb1b567baebde68e45132bb9faae1f`.
- Candidate: `wascityb.fr3`, SHA256
  `8883d7d7c8abdbac1225ce104ab41d023b5f2adc518e6e82874cd7caed45b2bf`.
- Patch: `patch.json`, SHA256
  `90a6d5ab65f35ca7bae095ad7e18adcd813d494bfbc2728457354822925ced56`.
- `validation.json`: **20 checks passed**, including complete selections, finite
  geometry, normalized normals, native palette interpolation, decreasing LODs,
  unchanged anchor/wind metadata and identical coincident silhouettes.
- `preservation.json`: **163 checks passed**, including **996,964 unselected
  native triangles preserved exactly**, unchanged collision, Merc data, TFRAG,
  existing texture pixels, BVH, native matrices and wind groups.
- `inner-city-palms.png` and `shore-palms.png` were visually inspected. They are
  Blender inspection renders, not game captures. Native wind, culling and frame
  time still need in-game inspection.

## Geometry and materials

The complete detailed meshes reuse `city-remaster/palms/author.py`, including
its corrected continuous cylindrical UVs on bark scars. The shared author SHA
is pinned by `author.py`. This is newly modeled geometry — curved individual
leaflets, rachises, dry strands, trunk collars/scars and roots — transformed by
each native instance's original matrix. No collision or gameplay is changed.

| LOD | Added triangles, all 13 palms |
| --- | ---: |
| 0 | 159,380 |
| 1 | 101,192 |
| 2 | 46,644 |
| 3 | 19,474 |

20,384 original triangles across all LODs are replaced by 326,690 triangles.
All 416 component/LOD groups are complete. LOD0 is roughly 12,260 triangles per
palm; performance and culling must be checked in the game.

The exact existing `market-palm-leaf-v1` and `market-palm-trunk-v1` textures are
reused. Their pixels are unchanged, and the bridge verifies identical existing
names before reuse. New dry fronds inherit the existing beard texture. No
shared atlas is replaced, and native wind provides the only foliage motion.

## Reproduction and integration

1. `python city-remaster/environment/foliage/prepare.py` reexports just the
   13 remaining complete palms from the immutable parent. Fresh draw IDs are
   essential: the market pass changed native draw ordering.
2. Run Blender in background with `author.py`; it writes this folder's patch,
   `.blend`, report and previews only.
3. `python city-remaster/environment/foliage/validate.py` validates the author.
4. `python city-remaster/environment/foliage/stage.py` builds a new candidate
   and runs the native preservation audit. It refuses to overwrite an existing
   candidate. It never modifies live data or variants.
5. Root owns installation and the `installed.json` record. Apply the wider ENV
   texture stage **after** this candidate, retaining its manifest as parent.

The saved `.blend` shows only LOD0; `finalize_blend.py` changes inspection
visibility only. No stage or author under the market folders was overwritten.

## WCA boundary

The current WCA texture inventory has no texture containing `palm`. Its static
draw inventory has no palm/leaf/beard/trunk material from this family. There is
therefore no WCA instance to which this specific author can be safely applied.
Other vegetation types would need their own targeted inventory and author.
