"""Lames sculptees qui tiennent les braseros de l'arene (TIE prototype 13, 42 exemplaires, 4 niveaux de detail).

Lancement : blender.exe --background --python arena-remaster/objects/remodel_spikes.py
Meme forme, memes UV et couleurs d'origine ; aretes arrondies (chanfrein a 3 segments) et faces subdivisees
en douceur, comme une piece sculptee et polie plutot qu'un solide a facettes. Sortie : spikes-patch.json.
"""
import sys, json, math
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'models-v1'))
from blender_common import *
OUT = Path(__file__).resolve().parent

faces = json.loads((OUT / 'braziers-native.json').read_text())['faces']
patch = {'description': 'Arene : lames des braseros aux aretes arrondies', 'remove': [], 'add': []}
reports = []


def soften(asset, width, segments):
    bm = bmesh.new(); bm.from_mesh(asset.obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(20)]
    bmesh.ops.bevel(bm, geom=edges, offset=width, segments=segments, profile=.55, affect='EDGES', clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces)); bm.normal_update(); bm.to_mesh(asset.obj.data); bm.free()
    for p in asset.obj.data.polygons: p.use_smooth = True
    asset.assign_uv()


instances = sorted({f.get('instance') for f in faces if f['proto'] == 13 and f['geom'] == 0})
for instance in instances:
    targets = defaultdict(list)
    for f in faces:
        if f['proto'] == 13 and f.get('instance') == instance:
            targets[f['geom']].append(f)
    reset()
    high = NativeMesh(f'Lame_{instance}', targets[0]); soften(high, .05, 3)
    low = NativeMesh(f'Lame_loin_{instance}', targets[3]); soften(low, .05, 1)
    info = {'instance': instance, 'original_triangles': {}, 'new_triangles': {}}
    for lod, tfaces in sorted(targets.items()):
        asset = low if lod == 3 else high
        remove, add, dist = asset.records(tfaces)
        patch['remove'].extend(remove); patch['add'].extend(add)
        info['original_triangles'][lod] = len(tfaces); info['new_triangles'][lod] = len(add)
    reports.append(info)
    if instance == instances[0]:
        render_asset(high.obj, OUT / 'spikes-preview.png', view=(4, -7, 2))
print('lames :', len(instances), reports[0]['original_triangles'], '->', reports[0]['new_triangles'], flush=True)
(OUT / 'spikes-patch.json').write_text(json.dumps(patch, separators=(',', ':')))
(OUT / 'spikes-report.json').write_text(json.dumps(reports, indent=2))
print('Enregistre :', len(patch['remove']), 'retires ->', len(patch['add']), 'ajoutes', flush=True)
