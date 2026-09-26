"""Apercu Blender des palmiers d'origine du desert (un exemplaire par prototype) : comprendre leur construction.
blender --background --python desert-remaster/palms/inspect_palms.py -- export.json
"""
import sys, json, math
from pathlib import Path
from collections import defaultdict
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'models-v1'))
from blender_common import NativeMesh, reset
HERE = Path(__file__).resolve().parent
src = sys.argv[sys.argv.index('--') + 1]
KEYS = sys.argv[sys.argv.index('--') + 2].split(',') if len(sys.argv) > sys.argv.index('--') + 2 else ['palm']
F = json.load(open(src))['faces']
by = defaultdict(lambda: defaultdict(list))
for f in F:
    if f.get('geom', 0) != 0: continue
    if not any(k in f['material'] for k in KEYS): continue
    by[f['proto']][f['instance']].append(f)
reset()
objs = []
x = 0.0
for proto in sorted(by):
    inst = sorted(by[proto])[0]
    fs = by[proto][inst]
    # tous les materiaux du prototype pour cet exemplaire
    allf = [f for f in F if f.get('geom', 0) == 0 and f['proto'] == proto and f['instance'] == inst and f['tree_type'] == fs[0]['tree_type'] and any(k in f['material'] for k in KEYS)]
    pts = [Vector(v['p']) for f in allf for v in f['vertices']]
    base = Vector((sum(p.x for p in pts) / len(pts), min(p.y for p in pts), sum(p.z for p in pts) / len(pts)))
    m = NativeMesh(f'proto{proto}', allf, origin=base - Vector((x, 0, 0)))
    size = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
    m.obj['size'] = size; objs.append(m.obj)
    print(proto, inst, sorted({f['material'] for f in allf}), len(allf), 'taille %.1f' % size)
    x += size * .9 + 4
scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 16
scene.render.resolution_x, scene.render.resolution_y = 2400, 900
world = scene.world or bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.6, .65, .75, 1)
sun = bpy.data.lights.new('s', 'SUN'); sun.energy = 4; so = bpy.data.objects.new('s', sun); scene.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(30))
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = x + 5
co = bpy.data.objects.new('c', cam); scene.collection.objects.link(co); scene.camera = co
co.location = (x / 2, -80, 18); co.rotation_euler = (math.radians(88), 0, 0)
scene.render.filepath = str(HERE / (Path(src).stem + '-' + KEYS[0] + '.png')); bpy.ops.render.render(write_still=True)
