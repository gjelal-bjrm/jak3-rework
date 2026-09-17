# Sand footsteps — native QA

Only `effect-control` changes in GAME.CGO. Root owns compiler port 7244 and
native tests. This folder's source patch never launches the compiler or game.

## Build / package

Compile `(m "effect-control")` after `apply.py --apply`. The output is
`data/out/jak3/obj/effect-control.o`. `register.py` (owned by the package agent)
stages and checks only that object against each separate route baseline; all
other CGO objects must be byte-identical. A full GAME rebuild is unnecessary.
Water/lighting/market changes in the other objects remain intact.

The final compilation passed. Object SHA256:
`be826db9d70e7c32b8271b53af979ba139c8f9de12c7f55df3556301f425cfcc`
(3,825,736 bytes). Hot loading was rejected by the listener packet-size limit;
that timeout was not a successful runtime test. `installed.json` records the
persistent installation into both separate GAME routes, preserving the other
489 of 490 objects byte-for-byte. The package validator subsequently passed
854 checks, with 48 files per variant and no errors.

**Work frozen at the user's request:** no further NPC dust debugging is part of
the current city art pass. Compilation, installation and static surface probes
are verified; natural NPC emission and the six live checks below remain
unverified. The earlier observation that Jak emitted dust but NPCs did not was
made before this new common implementation was loaded, so it establishes
neither success nor failure of the installed NPC hook.

## Static native-source evidence

- WCA sand at `(2240.2834, 7.0479, -40.7634)` is collision `dirt` (15), while
  its exact native TFRAG material is `wascity-ground-01`, with y=7.047568.
- `(2245, 7.919, -41)` is also ground-01, with native y=7.901719.
- Nearby stone at `(2239.8809408, 6.9510773, -41.5630061)` is
  `wascity-cement-road`. The exact triangle/height test rejects this point.
- `surface-validation.json` records these and other positive/negative probes,
  pinned native exports, and table hash. Texture RGB is never examined.
- Citizens propagate actual collision `best-other-tri.pat` into `ground-pat`
  (`citizen.gc` around 636 and 677). The effect requires on-ground, no in-air,
  no touch-water, sand/dirt PAT and an exact visible ground-01 hit.
- `wlander-male-ag.go` / `wlander-female-ag.go` use `was-fs-hard` / `wasf-fs`
  footstep tags, without `effect-joint`. `npc-hook.gc` observes these two tags
  and resolves Lball/Rball, selecting the nearest foot to the contact plane.
  The ordinary sound path remains present. Landing tags are not intercepted.

## Read-only REPL probes

Keep format argument counts small (the compiler limits call register arguments).

```lisp
(format #t "~%level=~A material=~D ground=~A wet=~A~%"
  (-> (level-get-target-inside *level*) name)
  (-> *target* control ground-pat material)
  (logtest? (-> *target* control status) (collide-status on-ground))
  (focus-test? *target* touch-water))

(format #t "~%sandA=~A sandB=~A stone=~A~%"
  (remaster-sand-visible-at? (new 'static 'vector :x (meters 2240.2834) :y (meters 7.0479) :z (meters -40.7634) :w 1.0))
  (remaster-sand-visible-at? (new 'static 'vector :x (meters 2245) :y (meters 7.919) :z (meters -41) :w 1.0))
  (remaster-sand-visible-at? (new 'static 'vector :x (meters 2239.88094) :y (meters 6.9510773) :z (meters -41.563006) :w 1.0)))

(format #t "~%events=~D eligible=~D emissions=~D npc=~D~%"
  *remaster-sand-step-events* *remaster-sand-step-eligible*
  *remaster-sand-step-emitted* *remaster-sand-step-npc-emitted*)

(format #t "~%surface-rejected=~D old-poofs-skipped=~D material=~D joint=~D~%"
  *remaster-sand-step-visual-rejected* *remaster-sand-step-suppressed-poofs*
  *remaster-sand-step-last-material* *remaster-sand-step-last-joint*)

(format #t "~%last-emission=~A level=~A~%"
  *remaster-sand-step-last-position* *remaster-sand-step-last-level*)
```

## Expected live checks

1. The exact surface probes return true / true / false.
2. Walk Jak over visible sand: emission count rises and two tiny short-lived
   particles appear at the actual foot. Standing idle produces no repeated
   dust. Old run poofs in this scope are skipped instead of added underneath.
3. Walk over neighbouring dalles: no new emission; the native material/mesh
   combination, not a broad rectangular zone, rejects the surface.
4. Keep Jak idle and observe naturally walking Spargus residents on sand:
   `npc-emitted` must rise and the small effect must be visible under their feet.
   This is required evidence; the shared code path alone is not validation.
5. Residents on stone and anyone airborne/in water produce no new sand effect.
6. Game remains muted. The patch does not alter sound settings or introduce any
   sound; preserving the native footstep call does not imply enabling audio.

## Scope / cost

WCA/WCB only. Ground-01 is the approved visible sand material; blended shore,
ditch and rock materials are conservatively rejected. Native collisions are
unchanged. The grid is only an index, followed by barycentric membership and
height checks (0.18 m tolerance); another material over the sand rejects it.
72,649 unique relevant triangles, 131,127 cell references, up to 644 candidates
in the busiest cell. Queries happen at footstep events, never each frame.

Each successful step requests two particles, about 0.11–0.155 m wide and
0.055–0.08 m high initially, at low alpha, fading over 0.24–0.30 s. Native
particle/group IDs are untouched; the launcher is private to this object.

**Pending, explicitly deferred:** the six live checks. Do not describe NPC dust
as working until natural NPC movement and actual emissions have been observed.
