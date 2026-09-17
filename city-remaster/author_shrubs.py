"""Author the 69 complete WCB market shrubs, without changing runtime files.

Run with Blender --background --python city-remaster/author_shrubs.py.
The native instance matrix, foot and time-of-day colour indices are retained.
Each leaf is a closed curved volume; no native card geometry is retained.
"""
from pathlib import Path
import sys, json, math, random, hashlib, argparse
from collections import Counter
import bpy
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'models-v1'))
from blender_common import NativeMesh, reset, render_asset

TEXTURE = 'market-shrub-orange-v1'
PAGE = 'remaster-market-plants'


def bezier(points, t):
    s = 1-t
    return points[0]*s**3 + points[1]*3*s*s*t + points[2]*3*s*t*t + points[3]*t**3


class Tuft:
    def __init__(self, asset, matrix, rng):
        self.asset, self.matrix, self.rng = asset, matrix, rng
        self.vertices, self.faces, self.uvs, self.shades = [], [], [], []
        self.leaves = 0

    def leaf(self, root, angle, reach, height, drop, width, steps=12):
        rng = self.rng
        direction = Vector((math.cos(angle), 0, math.sin(angle)))
        sideways = Vector((-direction.z, 0, direction.x))
        # Start almost upright, bend into the prevailing direction, then let the
        # dry outer tip fall. Different tips do not share a radial sphere.
        bend = rng.uniform(-.19, .19)
        controls = [root,
                    root + direction*(reach*.04) + Vector((0, height*.67, 0)),
                    root + direction*(reach*.65) + sideways*bend + Vector((0, height*1.33, 0)),
                    root + direction*reach + sideways*(bend*.4) + Vector((0, height-drop, 0))]
        rows = []
        twist = rng.uniform(-.42, .42)
        u0 = rng.uniform(.03, .84)
        uwidth = rng.uniform(.06, .12)
        leafshade = rng.uniform(.92, 1.035)
        samples = [1-(1-j/steps)**1.55 for j in range(steps+1)]
        for j, t in enumerate(samples):
            centre = bezier(controls, t)
            if j == steps:
                # A single real point avoids sub-pixel diamond caps collapsing
                # after conversion to large native world-coordinate floats.
                rows.append([len(self.vertices)])
                self.vertices.append(self.asset.local(self.matrix @ centre))
                self.shades.append(leafshade)
                continue
            tangent = (bezier(controls, min(1, t+.001)) - bezier(controls, max(0, t-.001))).normalized()
            across = (sideways - tangent*sideways.dot(tangent)).normalized()
            ridge = tangent.cross(across).normalized()
            rotated = across*math.cos(twist*t) + ridge*math.sin(twist*t)
            ridge = tangent.cross(rotated).normalized()
            # Broadest near the lower quarter, then a long, fine point.
            w = width * max(.015, (.23 + .77*math.sin(math.pi*t)**.63)*(1-t)**.55)
            thickness = w*.105
            points = [centre-rotated*w,
                      centre+ridge*thickness,
                      centre+rotated*w,
                      centre-ridge*(thickness*.72)]
            row = []
            for k, point in enumerate(points):
                row.append(len(self.vertices))
                self.vertices.append(self.asset.local(self.matrix @ point))
                # Keep the source's lighting; add only weak ridge/base shading.
                self.shades.append(leafshade*(.84+.16*min(1, t*3))*[.93, 1.025, .93, .88][k])
            rows.append(row)
        for j in range(steps):
            for k in range(4):
                n = (k+1)%4
                # Counter-clockwise when viewed from outside the closed blade.
                if j == steps-1:
                    self.faces.append((rows[j][k], rows[j+1][0], rows[j][n]))
                    self.uvs.append([(u0+uwidth*k/4, samples[j]),
                                     (u0+uwidth*(k+.5)/4, 1),
                                     (u0+uwidth*(k+1)/4, samples[j])])
                    continue
                self.faces.append((rows[j][k], rows[j+1][k], rows[j+1][n], rows[j][n]))
                self.uvs.append([(u0+uwidth*k/4, samples[j]),
                                 (u0+uwidth*k/4, samples[j+1]),
                                 (u0+uwidth*(k+1)/4, samples[j+1]),
                                 (u0+uwidth*(k+1)/4, samples[j])])
        self.faces.append(tuple(rows[0]))
        self.uvs.append([(u0, 0), (u0+uwidth*.5, 0), (u0+uwidth, 0), (u0+uwidth*.5, 0)])
        self.leaves += 1

    def grow(self):
        rng = self.rng
        phase = rng.uniform(0, math.tau)
        # Three unequal crowns sharing the same native root zone. A few leaves
        # lean with their neighbours, avoiding an evenly spaced porcupine fan.
        clusters = [(0, 0), (.11, -.07), (-.075, .09)]
        counts = [rng.randint(9, 11), rng.randint(13, 15), rng.randint(8, 10)]
        for tier, count in enumerate(counts):
            for i in range(count):
                angle = phase + i*2.39996323 + tier*.47 + rng.uniform(-.20, .20)
                cx, cz = clusters[rng.randrange(len(clusters))]
                root = Vector((cx+rng.uniform(-.025, .025), -.071+rng.uniform(0, .012), cz+rng.uniform(-.025, .025)))
                if tier == 0:
                    height, reach, drop = rng.uniform(1.55, 2.04), rng.uniform(.24, .66), rng.uniform(0, .15)
                    width = rng.uniform(.028, .048)
                elif tier == 1:
                    height, reach, drop = rng.uniform(1.12, 1.65), rng.uniform(.75, 1.21), rng.uniform(.12, .43)
                    width = rng.uniform(.038, .064)
                else:
                    height, reach, drop = rng.uniform(.60, 1.03), rng.uniform(.81, 1.30), rng.uniform(.30, .58)
                    width = rng.uniform(.025, .051)
                self.leaf(root, angle, reach, height, drop, width)

    def finish(self, material):
        mesh = bpy.data.meshes.new(self.asset.obj.name+' curved closed blades')
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(material)
        uv = mesh.uv_layers.new(name='UVMap')
        colours = mesh.color_attributes.new(name='LeafShade', type='FLOAT_COLOR', domain='POINT')
        for i, shade in enumerate(self.shades):
            colours.data[i].color = (shade, shade, shade, 1)
        for polygon, coords in zip(mesh.polygons, self.uvs):
            polygon.use_smooth = True
            for loop, st in zip(polygon.loop_indices, coords):
                uv.data[loop].uv = st
        mesh.update()
        self.asset.obj.data = mesh
        # Verify actual closed topology; each disconnected leaf is intentional.
        incidence = Counter()
        for face in self.faces:
            for a, b in zip(face, face[1:]+face[:1]):
                incidence[tuple(sorted((a,b)))] += 1
        assert all(count == 2 for count in incidence.values()), 'An authored blade is open'
        return mesh


def make_material():
    material = bpy.data.materials.new('Market dry ochre leaf tissue')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .76
    shader.inputs['Specular IOR Level'].default_value = .23
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(HERE/'market-shrub-orange-hd.png'))
    texture.image.pack()
    colour = nodes.new('ShaderNodeVertexColor'); colour.layer_name = 'LeafShade'
    mix = nodes.new('ShaderNodeMixRGB'); mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1
    links.new(texture.outputs['Color'], mix.inputs[1]); links.new(colour.outputs['Color'], mix.inputs[2])
    links.new(mix.outputs['Color'], shader.inputs['Base Color'])
    return material


def bounds(points):
    return [[min(p[a] for p in points) for a in range(3)], [max(p[a] for p in points) for a in range(3)]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    native = json.loads((HERE/'market-plants-native.json').read_text())
    mapping = json.loads((HERE/'market-plants-map.json').read_text())
    instances = {i['instance']: i for i in native['instance_inventory'] if i['tree_type']=='shrub' and i['tree']==0}
    selected = {item['source']['instance'] for item in mapping['shrubs']}
    targets = {i: [] for i in selected}
    for face in native['faces']:
        if face['tree_type']=='shrub' and face['tree']==0 and face['instance'] in selected:
            assert face['proto']==9 and face['geom']==0
            targets[face['instance']].append(face)
    assert len(targets)==69 and all(len(faces)==38 for faces in targets.values())
    reset(); material = make_material()
    patch = {'description':'69 complete WCB market shrubs: individually curved, closed desert blades, native feet/palette and isolated HD tissue texture',
             'level':native['level'], 'source_fr3':native['source_fr3'],
             'new_textures':[{'name':TEXTURE,'page':PAGE,'width':1254,'height':1254,
                              'rgba_file':str((HERE/'market-shrub-orange-hd.rgba').resolve())}],
             'remove':[], 'add':[]}
    report = {'source_fr3':native['source_fr3'], 'texture':TEXTURE, 'uv_units':'native 0..4096',
              'collision_modified':False, 'instance_matrices_preserved':True,
              'runtime_modified':False, 'closed_blades':True, 'instances':[]}
    assets = []
    preview_ids = [2467, 2491, 2596]
    scene_origin = Vector((1780, 30, -310))
    for number, instance in enumerate(sorted(targets)):
        faces, inst = targets[instance], instances[instance]
        origin, cols = inst['origin_m'], inst['matrix_columns']
        matrix = Matrix([[cols[c][r] for c in range(3)]+[origin[r]] for r in range(3)]+[[0,0,0,1]])
        asset = NativeMesh('Market shrub '+str(instance), faces, origin)
        # Source thumbnail uses native UV divided by 4096 only for preview.
        if instance == preview_ids[0] and not args.no_render:
            for loop in asset.obj.data.uv_layers.active.data:
                loop.uv = (loop.uv.x/4096, 1-(1-loop.uv.y)/4096)
            render_asset(asset.obj, HERE/'market-shrubs-source-preview.png', view=(4,-7,2.6), resolution=900)
        tuft = Tuft(asset, matrix, random.Random(instance*787+9143)); tuft.grow()
        mesh = tuft.finish(material)
        remove, add, distance = asset.records(faces)
        mesh.calc_loop_triangles()
        assert len(add)==len(mesh.loop_triangles)
        for record, tri in zip(add, mesh.loop_triangles):
            record['texture'] = TEXTURE
            for vertex, vi in zip(record['vertices'], tri.vertices):
                vertex['uv'] = [round(value*4096, 5) for value in vertex['uv']]
                vertex['rgba'] = [max(0,min(255,round(value*tuft.shades[vi]))) for value in vertex['rgba']]
                vertex['p'] = [round(value,6) for value in vertex['p']]
        patch['remove'].extend(remove); patch['add'].extend(add)
        points = [asset.world(vertex.co) for vertex in mesh.vertices]
        lo, hi = bounds(points)
        oldlo, oldhi = bounds([v['p'] for f in faces for v in f['vertices']])
        source_radius = max(math.hypot(v['p'][0]-origin[0],v['p'][2]-origin[2]) for f in faces for v in f['vertices'])
        new_radius = max(math.hypot(p[0]-origin[0],p[2]-origin[2]) for p in points)
        asset.obj['native_instance'] = instance
        asset.obj['native_matrix_columns'] = json.dumps(cols)
        asset.obj['source_triangles'] = len(faces)
        asset.obj['authored_leaves'] = tuft.leaves
        delta = Vector(origin)-scene_origin
        asset.obj.location = (delta.x,-delta.z,delta.y)
        report['instances'].append({'instance':instance, 'origin_m':origin, 'leaves':tuft.leaves,
            'source_triangles':len(faces),'authored_triangles':len(add),'source_bounds':[oldlo,oldhi],
            'authored_bounds':[lo,hi], 'radius_ratio':new_radius/source_radius,
            'source_projection_max_m':distance, 'minimum_y_change_m':lo[1]-oldlo[1]})
        if instance in preview_ids and not args.no_render:
            bpy.context.view_layer.update()
            render_asset(asset.obj, HERE/f'market-shrub-{instance}-preview.png', view=(4,-7,2.6), resolution=1000)
        assets.append(asset)
        print(f'SHRUB {number+1}/69 instance={instance} leaves={tuft.leaves} triangles={len(add)} radius={new_radius/source_radius:.3f}', flush=True)
    report['removed_triangles'] = len(patch['remove']); report['added_triangles'] = len(patch['add'])
    report['authored_leaves'] = sum(i['leaves'] for i in report['instances'])
    report['max_radius_ratio'] = max(i['radius_ratio'] for i in report['instances'])
    report['min_radius_ratio'] = min(i['radius_ratio'] for i in report['instances'])
    assert len(patch['remove'])==2622
    # All instances stay in their original scene positions. Cameras are only
    # author previews; these assets have not been validated in the live game.
    for asset in assets:
        asset.obj.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'market-shrubs.blend'))
    (HERE/'market-shrubs-patch.json').write_text(json.dumps(patch,separators=(',',':')))
    (HERE/'market-shrubs-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='instances'},indent=2),flush=True)


if __name__=='__main__':
    main()
