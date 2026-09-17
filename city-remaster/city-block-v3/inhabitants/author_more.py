"""Nouveaux habitants pour varier les scenes : femme assise, dormeurs, cuisiniers.

Blender en arriere-plan :  blender.exe --background --python author_more.py

Reprend l'auteur v1 (author.py : import du corps natif, textures, export JSON+BIN 48 octets
par sommet, quatre poses en boucle). Ajoute deux poses :
- sleeping : allonge sur le dos, mains sur le ventre, respiration lente ; le corps est couche
  le long de +Z (tete vers -Z, c'est-a-dire vers le fond de la piece), dos a Y=0.
- cooking : debout, buste penche vers l'avant, main droite qui remue au-dessus d'une marmite,
  main gauche posee sur la hanche, regard baisse.
"""
from pathlib import Path
import importlib.util, bpy, math, json, struct, hashlib
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('author_v1', HERE / 'author.py')
v1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)
aim, turn, update, evaluated, textures, digest, scene_setup = v1.aim, v1.turn, v1.update, v1.evaluated, v1.textures, v1.digest, v1.scene_setup

ACTORS = [('female', 'sitting'), ('male', 'sleeping'), ('female', 'sleeping'), ('female', 'cooking'), ('male', 'cooking')]
DURATION = {'sitting': 5.6, 'sleeping': 6.4, 'cooking': 3.2}


def pose(arm, sex, kind, phase):
    if kind == 'sitting':
        v1.pose(arm, sex, 'sitting', phase); return
    arm.animation_data_clear()
    for b in arm.pose.bones: b.matrix_basis.identity()
    update()
    wave = math.sin(phase); slow = math.cos(phase)
    if kind == 'sleeping':
        # bras le long du corps puis mains ramenees sur le ventre ; tete legerement tournee
        for side, sign in [('L', 1), ('R', -1)]:
            aim(arm, side + 'shoulder', (sign * .10, .05, -1))
            aim(arm, side + 'elbow', (-sign * .60, -.50, -.30))       # avant-bras vers le ventre (devant = -Y)
            turn(arm, side + 'hand', 'X', math.radians(-15))
        turn(arm, 'chest', 'X', math.radians(2.0 + 1.6 * wave))       # respiration
        turn(arm, 'neck', 'Z', math.radians(18 + 1.5 * slow))
        turn(arm, 'neck', 'X', math.radians(6))
        for side, sign in [('L', 1), ('R', -1)]:
            aim(arm, side + 'thigh', (sign * .09, .06, -1))
            aim(arm, side + 'knee', (0, .10, -1))
        # puis tout le corps est couche : rotation de l'os racine 'main' (les rotations
        # d'objet n'ont aucun effet sur le maillage deforme par l'armature)
        main = arm.pose.bones['main']; main.matrix_basis = Matrix.Rotation(math.radians(-90), 4, 'X') @ main.matrix_basis; update()
    elif kind == 'cooking':
        turn(arm, 'chest', 'X', math.radians(11 + 1.0 * slow))         # buste penche vers la marmite
        turn(arm, 'neck', 'X', math.radians(14))
        turn(arm, 'neck', 'Z', math.radians(-4 + 2.0 * wave))
        # bras droit : avant-bras qui decrit un petit cercle au-dessus de la marmite
        aim(arm, 'Rshoulder', (-.15, -.55, -.85))
        aim(arm, 'Relbow', (.25 + .18 * wave, -1, .45 + .18 * slow))
        turn(arm, 'Rhand', 'X', math.radians(-30))
        # bras gauche : main sur la hanche
        aim(arm, 'Lshoulder', (.32, .10, -.95))
        aim(arm, 'Lelbow', (-.85, -.35, -.20))
        turn(arm, 'chest', 'Z', math.radians(1.2 * wave))
    update()


def frame_vertices(obj, scale, offset):
    """Comme v1.frame_vertices, mais avec un decalage vertical mesure en coordonnees monde."""
    ev, mesh = evaluated(obj); records = []; ranges = []
    colors = mesh.color_attributes.get('Color') or mesh.color_attributes.active_color
    uv = mesh.uv_layers.active.data
    for material in range(len(obj.data.materials)):
        start = len(records)
        for triangle in mesh.loop_triangles:
            if triangle.material_index != material: continue
            for vi, li in zip(triangle.vertices, triangle.loops):
                point = ev.matrix_world @ mesh.vertices[vi].co
                normal = (ev.matrix_world.to_3x3() @ mesh.corner_normals[li].vector).normalized()
                tex = uv[li].uv
                col = tuple(2 * x for x in colors.data[li if colors.domain == 'CORNER' else vi].color) if colors else (1, 1, 1, 2)
                records.append((point.x * scale, (point.z + offset) * scale, -point.y * scale,
                                normal.x, normal.z, -normal.y, tex.x, 1 - tex.y, *col))
        if len(records) > start: ranges.append({'material_index': material, 'first': start, 'count': len(records) - start})
    ev.to_mesh_clear(); return records, ranges


def world_min_z(obj):
    ev, mesh = evaluated(obj); z = min((ev.matrix_world @ v.co).z for v in mesh.vertices); ev.to_mesh_clear(); return z


def main():
    results = []
    for sex, kind in ACTORS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(HERE / (sex + '-selected.glb')))
        arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        obj = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.startswith('wlander-'))
        for o in list(bpy.data.objects):
            if o not in (arm, obj): bpy.data.objects.remove(o, do_unlink=True)
        arm.animation_data_clear()
        for b in arm.pose.bones: b.matrix_basis.identity()
        update()
        ev, mesh = evaluated(obj); standing_height = max(v.co.z for v in mesh.vertices) - min(v.co.z for v in mesh.vertices); ev.to_mesh_clear()
        # meme taille que les habitants deja installes (scale_actors.py : x1,15 assis, x1,2 debout)
        scale = (2.0 if sex == 'male' else 1.9) / standing_height * (1.15 if kind == 'sitting' else 1.2)
        for p in obj.data.polygons: p.use_smooth = True
        mats = textures(obj)
        name = kind + '-' + sex; frames = []; bounds = []; joints = []; rig_frames = []; offset = None; draws = None
        for i in range(4):
            pose(arm, sex, kind, i * math.tau / 4)
            rig_frames.append({b.name: b.matrix_basis.copy() for b in arm.pose.bones})
            if offset is None: offset = -world_min_z(obj)
            records, ranges = frame_vertices(obj, scale, offset)
            if draws is None: draws = ranges
            assert draws == ranges
            if frames: assert all(a[6:] == b[6:] for a, b in zip(frames[0], records))
            frames.append(records)
            bounds.append([[min(v[a] for v in records) for a in range(3)], [max(v[a] for v in records) for a in range(3)]])
            joints.append({n: [(arm.matrix_world @ b.head).x * scale, ((arm.matrix_world @ b.head).z + offset) * scale, -(arm.matrix_world @ b.head).y * scale]
                           for n in ('hips', 'Lknee', 'Rknee', 'Lhand', 'Rhand', 'Lankle', 'Rankle', 'neck') if (b := arm.pose.bones.get(n))})
        data = b''.join(struct.pack('<12f', *r) for frame in frames for r in frame)
        (HERE / (name + '.bin')).write_bytes(data)
        for draw in draws: draw.update(mats[draw.pop('material_index')])
        report = {'name': name, 'version': 1, 'binary': name + '.bin', 'binary_sha256': digest(data),
                  'source_manifest': 'source-manifest.json', 'source_sex': sex, 'kind': kind,
                  'coordinate_system': 'right-handed X right, Y up, Z forward; metres; lowest point at Y=0' + (' (lying on the back along -Z, head toward -Z)' if kind == 'sleeping' else ''),
                  'stride_bytes': 48, 'attributes': {'position': [0, 3], 'normal': [12, 3], 'uv': [24, 2], 'color': [32, 4]},
                  'vertex_color_contract': 'linear vertex COLOR_0 multiplied by native GLB baseColorFactor=2; RGB normally 0..1, alpha=2 compensates native texture alpha 128/255; multiply albedo * vertex RGBA directly, then lighting',
                  'primitive': 'triangles', 'vertex_count': len(frames[0]), 'frame_count': 4, 'frame_stride_bytes': len(frames[0]) * 48,
                  'duration_seconds': DURATION[kind], 'sample_times': [0, .25, .5, .75], 'loop': True,
                  'interpolation': 'cyclic linear positions; normalize blended normals; UV/color constant',
                  'standing_height_m': 2.0 if sex == 'male' else 1.9, 'source_height_m': standing_height, 'source_to_metres_scale': scale,
                  'bounds_by_frame': bounds, 'draws': draws, 'joint_positions_by_frame': joints, 'native_game_validation': False}
        if kind == 'sitting':
            hp = joints[0]['hips']; report['seat'] = {'center_m': [hp[0], hp[1] - .06, hp[2]], 'recommended_cushion_top_m': hp[1] - .06, 'forward': '+Z'}
        (HERE / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')
        arm.animation_data_clear()
        for i in range(5):
            for b in arm.pose.bones:
                b.matrix_basis = rig_frames[i % 4][b.name]
                for path in ('location', 'rotation_quaternion', 'scale'): b.keyframe_insert(data_path=path, frame=1 + i * 24)
        sc = scene_setup(); sc.frame_end = 97; sc.frame_set(1)
        if kind == 'sleeping':   # camera plus haute pour un corps couche
            cam = sc.camera; cam.location = (3.5, -6, 4.5); cam.rotation_euler = (Vector((0, -.2, .3)) - Vector(cam.location)).to_track_quat('-Z', 'Y').to_euler(); cam.data.ortho_scale = 4.4
        sc.render.filepath = str(HERE / (name + '-preview.png')); bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (name + '.blend')))
        results.append({k: report[k] for k in ('name', 'binary', 'vertex_count', 'frame_count', 'binary_sha256', 'bounds_by_frame')})
        print(name, 'sommets', len(frames[0]), 'bornes', [round(x, 2) for x in bounds[0][0]], [round(x, 2) for x in bounds[0][1]], flush=True)
    (HERE / 'actors-more.json').write_text(json.dumps({'actors': results}, indent=2) + '\n')


if __name__ == '__main__': main()
