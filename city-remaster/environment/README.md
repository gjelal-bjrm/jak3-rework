# City environment texture pipeline

Scope: exact named surface textures in `wascitya`, `wascityb` and `waswide`.
The bridge changes texture dimensions and RGBA bytes in the current FR3 files.
There is no level re-extraction, geometry replacement or runtime code change.

## Authoring inputs

`generated-materials.json` is the explicit allowlist and generation provenance.
It contains a list of `{name, generated, prompt}` entries. Each existing
`masters/<name>.png` is selected at staging time. Missing approved masters are
reported as pending; unlisted PNGs fail preparation.

Preparation uses Pillow only to read the image and convert its storage format.
RGB bytes are preserved exactly, and opaque native alpha is encoded as 128.
Native source aspect ratios must be preserved. Transparent native materials
require a separately reviewed alpha policy and are currently rejected.

Run from the prototype root in PowerShell:

```powershell
python city-remaster/environment/prepare.py
python city-remaster/environment/stage.py --stage city-environment-001
python city-remaster/environment/deploy.py --stage city-environment-001
```

`stage.py` creates an immutable new folder, snapshots the current installed
levels and the generation catalogue, prepares all current masters, patches the
copies and runs an independent audit. `deploy.py` is a read-only dry run unless
`--apply` is supplied. Always use a new stage name for a changed batch.

```powershell
python city-remaster/environment/deploy.py --stage city-environment-001 --apply
python city-remaster/environment/deploy.py --rollback
python city-remaster/environment/deploy.py --rollback --apply
```

## Provenance chain

Each level must match a recorded parent before staging. The records are read in
this order, with the most recent matching output selected:

1. `environment/baselines/waswide/baseline.json`
2. `city-remaster/installed.json` (market Merc models)
3. `city-remaster/static-installed.json` (static market models)
4. `environment/foliage/installed.json` (remaining city palms)
5. `environment/installed.json` (previous texture batch, if any)

WASWIDE's first baseline was independently compared against
`active/jak3/data/out/jak3/fr3/waswide.fr3`. They were byte-identical, SHA256
`76aa2abc630cd76dd6246354162f20ec5006d350d07e9599dc66d80c3186edff`.
`baseline_waswide.py` freezes copies and refuses to label a differing live file
as original. The baseline includes source hashes, two immutable snapshots and
original/V1/remaster variant copies. Their registry entries are added by the
first explicit ENV install, to avoid changing the shared registry during
another agent's deployment.

## Independent audit and installation proof

The existing bridge writes candidates; `audit.py` independently reads the
serialized levels using `compare_market.read_level` under Blender's Python,
which supplies `zstandard`. It compares:

- The complete static region, including geometry, collision and texture indices.
- The complete Merc tail, including the previously rebuilt market objects.
- Every serialized texture outside the exact allowlist.
- Name, page, combined ID and pool flag of each selected texture.
- Each selected texture's new dimensions and every RGBA pixel against the
  immutable stage files.
- At least one real pixel change in every candidate, to reject no-op passes.

`audit.json` binds its proof to `stage.json`, the auditor and parser hashes.
Before applying, deployment repeats all file hashes and verifies that the live
levels, remaster variants and parent records still match the frozen bases.
It also checks the current masters and generation catalogue have not changed
since staging. Original and V1 files are protected throughout.

The separate `environment/installed.json` records per-level `parent`, `before`,
`base_sha256`, `candidate`, `output_sha256`, patch and preservation hashes. It
does not overwrite the upstream Merc, static or foliage records. The immutable
stage contains its generation catalogue, encoded pixels, audit and installed
record. Future authoring masters may change without invalidating this stored
installation proof.

Copies use atomic replacement, breaking any hard links. Only this batch's
remaster registry entries and newly tracked baseline entries are updated.
Rollback verifies that the current levels still match the installed batch,
then restores its exact snapshots. If geometry advanced between texture
batches, rollback records that precise restored parent rather than resurrecting
an unrelated older texture manifest.

An audit proves data preservation, not visual quality or performance. Native
inspection after a level reload remains necessary; this pipeline never starts
the game or claims native visual validation.
