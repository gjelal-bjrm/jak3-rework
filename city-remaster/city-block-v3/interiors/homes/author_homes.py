"""Interieurs de maisons de Spargus vus depuis la rue : salon, chambre, cuisine.

Blender en arriere-plan :  blender.exe --background --python author_homes.py [--preview-only]

Principes (retour utilisateur du 17 septembre) : une fenetre doit donner sur l'interieur
d'une vraie maison, pas sur une vitrine.
- Le sol est 85 cm sous l'appui de fenetre : on voit les gens a partir de la taille, les
  meubles par-dessus l'appui, jamais un plancher de scene.
- La piece est bien plus large et plus profonde que l'ouverture (7,2 x 5,4 m) et continue
  hors du cadre ; une porte ouvre sur un couloir sombre, la maison ne s'arrete pas au mur.
- Plafond a 2,7 m avec poutres, murs epais autour de l'ouverture (parapet, tableaux, linteau).
- Une seule lampe chaude pres des meubles, le reste dans la penombre.
- Meubles bas et allonges, dans les materiaux de Spargus : enduit, pierre, bois sombre,
  toiles ocre et sarcelle, jarres d'argile, bronze.

Repere identique aux pieces precedentes : metres, x a droite vu de la rue, y vers le haut,
z negatif vers l'interieur ; l'origine est au centre de l'ouverture, 10 cm au-dessus de l'appui.
Le moteur place l'origine de la piece 54 cm derriere la facade.
"""
from pathlib import Path
import bpy, bmesh, math, json, struct, hashlib, sys
from mathutils import Vector

HERE = Path(__file__).resolve().parent
F = -.45            # sol : 45 cm sous l'appui, on voit les gens assis a partir de la poitrine
CEIL = 2.7          # plafond
W, D = 4.8, 3.4     # largeur, profondeur : doit tenir dans toutes les maisons (3,5 m libres audites)
OPEN_W, OPEN_TOP = 3.2, 2.5   # ouverture interieure (le trou exterieur fait 3,2 x 2,8, de 0,1 a 2,9)
MATERIALS = [
    ('sunbaked plaster', (.64, .47, .29), .93, 0),
    ('warm stone', (.36, .30, .23), .88, 0),
    ('carved wood', (.22, .12, .055), .70, 1),
    ('copper bindings', (.34, .18, .073), .43, 0),
    ('ochre canvas', (.59, .31, .105), .92, 2),
    ('deep teal canvas', (.12, .26, .22), .94, 2),
    ('clay vessels', (.56, .23, .10), .82, 0),
    ('dark rug', (.28, .13, .068), .98, 2),
    ('rug border', (.63, .40, .15), .95, 2),
    ('plant green', (.22, .29, .060), .62, 0),
    ('dark bronze', (.12, .095, .065), .52, 0),
    ('lamplight glass', (.94, .48, .12), .30, 0),
    ('shadow plaster', (.16, .12, .08), .97, 0),
    ('linen', (.78, .70, .56), .90, 2),
    ('hearth stone', (.20, .18, .16), .92, 0),
    ('fire glow', (1.0, .52, .14), .20, 0),
    ('sand floor', (.55, .44, .30), .96, 0),
]
EMISSIVE = {'lamplight glass', 'fire glow'}
MAT = {name: i for i, (name, *_rest) in enumerate(MATERIALS)}


def local(p): return (p[0], -p[2], p[1])
def material(index): return bpy.data.materials[MATERIALS[index][0]]


def finish(obj, name, mat, export=True):
    obj.name = name; obj.data.materials.append(material(mat)); obj['material_index'] = mat; obj['export'] = export
    return obj


def cube(name, p, size, mat, bevel=.025, rot=0, export=True):
    bpy.ops.mesh.primitive_cube_add(size=1, location=local(p))
    o = bpy.context.object; o.dimensions = (size[0], size[2], size[1]); o.rotation_euler.z = rot
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        m = o.modifiers.new('rounded edges', 'BEVEL'); m.width = bevel; m.segments = 2
        m = o.modifiers.new('weighted normals', 'WEIGHTED_NORMAL'); m.keep_sharp = True
    return finish(o, name, mat, export)


def ellipsoid(name, p, size, mat, rotate=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=1, location=local(p))
    o = bpy.context.object; o.scale = (size[0], size[2], size[1]); o.rotation_euler.z = rotate
    for f in o.data.polygons: f.use_smooth = True
    return finish(o, name, mat)


def rod(name, a, b, r, mat, vertices=10):
    av, bv = Vector(local(a)), Vector(local(b)); d = bv - av
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=r, depth=d.length, location=(av + bv) * .5)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return finish(o, name, mat)


def vase(name, p, height, radius, mat):
    profile = [(0, .54), (.08, .7), (.20, .94), (.43, 1), (.65, .82), (.79, .58), (.87, .45), (.96, .45), (1, .54), (.985, .40), (.87, .34), (.73, .42), (.69, 0)]
    verts = []; faces = []; n = 18
    for y, r in profile:
        for i in range(n):
            a = i * math.tau / n; verts.append(local((p[0] + math.cos(a) * radius * r, p[1] + y * height, p[2] + math.sin(a) * radius * r)))
    for ring in range(len(profile) - 1):
        for i in range(n):
            j = (i + 1) % n; faces.append((ring * n + i, ring * n + j, (ring + 1) * n + j, (ring + 1) * n + i))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], faces); mesh.update()
    o = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(o)
    for f in mesh.polygons: f.use_smooth = True
    return finish(o, name, mat)


def cushion(name, p, size, mat, rotate=0):
    return cube(name, p, size, mat, min(size) * .30, rotate)


def cloth(name, p, size, mat):
    """Tissu pendu : panneau fin avec un leger ventre."""
    o = cube(name, p, size, mat, .01)
    bm = bmesh.new(); bm.from_mesh(o.data)
    for v in bm.verts:
        v.co.y -= .05 * math.sin((v.co.z - min(w.co.z for w in bm.verts)) / max(size[1], .01) * math.pi)
    bm.to_mesh(o.data); bm.free(); return o


def wall_with_door(z, door_x, door_w=1.1, door_h=2.2, thickness=.2):
    """Mur du fond en trois panneaux autour d'une porte ; retourne les objets."""
    left_w = (door_x - door_w / 2) - (-W / 2); right_w = W / 2 - (door_x + door_w / 2)
    out = [cube('back wall left', (-W / 2 + left_w / 2, (F + CEIL) / 2, z), (left_w, CEIL - F, thickness), MAT['sunbaked plaster'], .04),
           cube('back wall right', (W / 2 - right_w / 2, (F + CEIL) / 2, z), (right_w, CEIL - F, thickness), MAT['sunbaked plaster'], .04),
           cube('door lintel wall', (door_x, (F + door_h + CEIL) / 2, z), (door_w + .02, CEIL - (F + door_h), thickness), MAT['sunbaked plaster'], .04)]
    # encadrement de porte en bois et seuil
    for side in (-1, 1):
        out.append(cube('door jamb', (door_x + side * (door_w / 2 + .06), (F + door_h / 2), z), (.12, door_h + .1, thickness + .06), MAT['carved wood'], .02))
    out.append(cube('door head', (door_x, F + door_h + .08, z), (door_w + .3, .16, thickness + .06), MAT['carved wood'], .02))
    out.append(cube('door sill', (door_x, F + .02, z), (door_w + .1, .05, thickness + .08), MAT['warm stone'], .01))
    # couloir sombre derriere la porte, avec une lueur lointaine (court : il ne doit pas ressortir du batiment)
    depth = .7
    out.append(cube('corridor floor', (door_x, F - .05, z - thickness / 2 - depth / 2), (door_w + .6, .1, depth), MAT['shadow plaster'], 0))
    out.append(cube('corridor ceiling', (door_x, CEIL - .3, z - thickness / 2 - depth / 2), (door_w + .6, .1, depth), MAT['shadow plaster'], 0))
    for side in (-1, 1):
        out.append(cube('corridor wall', (door_x + side * (door_w / 2 + .3), (F + CEIL) / 2 - .15, z - thickness / 2 - depth / 2), (.1, CEIL - F, depth), MAT['shadow plaster'], 0))
    out.append(cube('corridor end wall', (door_x, (F + CEIL) / 2 - .15, z - thickness / 2 - depth), (door_w + .6, CEIL - F, .1), MAT['shadow plaster'], 0))
    out.append(ellipsoid('corridor lamp glass', (door_x + .25, F + 1.9, z - thickness / 2 - depth + .3), (.07, .10, .07), MAT['lamplight glass']))
    out.append(rod('corridor lamp chain', (door_x + .25, CEIL - .3, z - thickness / 2 - depth + .3), (door_x + .25, F + 2.0, z - thickness / 2 - depth + .3), .012, MAT['dark bronze']))
    return out


def shell(door_x):
    """Enveloppe commune : sol, plafond, murs, ouverture epaisse, poutres, porte et couloir."""
    cube('floor', (0, F - .1, -D / 2), (W, .2, D), MAT['sand floor'], .02)
    cube('ceiling', (0, CEIL + .17, -D / 2), (W, .34, D), MAT['sunbaked plaster'], .03)
    for side in (-1, 1):
        cube('side wall', (side * (W / 2 - .1), (F + CEIL) / 2, -D / 2), (.2, CEIL - F, D), MAT['sunbaked plaster'], .04)
        cube('wall foot course', (side * (W / 2 - .28), F + .14, -D / 2), (.16, .28, D), MAT['warm stone'], .03)
    # mur de facade interieur, epais, autour de l'ouverture
    t = .38
    cube('parapet', (0, (F + .1) / 2, -t / 2), (W, .1 - F, t), MAT['sunbaked plaster'], .03)
    cube('inner sill board', (0, .13, -t / 2), (OPEN_W + .3, .07, t + .12), MAT['carved wood'], .015)
    # le mur de facade interieur monte jusqu'a 4 m : certaines ouvertures exterieures font 3,8 m de haut
    TOP = 4.0
    cube('front lintel', (0, (OPEN_TOP + TOP) / 2, -t / 2), (W, TOP - OPEN_TOP, t), MAT['sunbaked plaster'], .03)
    for side in (-1, 1):
        cube('front wall side', (side * (OPEN_W / 2 + (W / 2 - OPEN_W / 2) / 2), (F + TOP) / 2, -t / 2), (W / 2 - OPEN_W / 2, TOP - F, t), MAT['sunbaked plaster'], .03)
    cube('back wall foot course', (0, F + .14, -D + .3), (W - .4, .28, .16), MAT['warm stone'], .03)
    for x in (-1.8, -.6, .6, 1.8):
        cube('ceiling beam', (x, CEIL - .09, -D / 2), (.16, .2, D), MAT['carved wood'], .02)
    wall_with_door(-D + .1, door_x, door_w=1.0)
    # niche haute dans le mur du fond, cote oppose a la porte
    nx = -door_x * .6
    cube('wall niche back', (nx, F + 1.85, -D + .19), (1.1, .6, .06), MAT['shadow plaster'], .01)
    cube('niche shelf', (nx, F + 1.57, -D + .24), (1.14, .06, .28), MAT['carved wood'], .012)
    for i in range(3):
        vase('niche jar', (nx - .36 + i * .36, F + 1.6, -D + .26), .24 + (i % 2) * .07, .09, MAT['clay vessels'])


def pendant_lamp(p, chain_top=CEIL - .05):
    rod('lamp chain', (p[0], chain_top, p[2]), (p[0], p[1] + .12, p[2]), .012, MAT['dark bronze'])
    ellipsoid('lamp glass', p, (.13, .17, .13), MAT['lamplight glass'])
    for i in range(6):
        a = i * math.tau / 6
        rod('lamp cage', (p[0] + math.cos(a) * .16, p[1] - .16, p[2] + math.sin(a) * .16), (p[0] + math.cos(a) * .16, p[1] + .16, p[2] + math.sin(a) * .16), .01, MAT['dark bronze'], 6)
    cube('lamp cap', (p[0], p[1] + .19, p[2]), (.22, .05, .22), MAT['dark bronze'], .01)


def divan(x0, x1, z):
    """Banquette basse contre le mur du fond, face a la rue. Retourne le dessus des coussins."""
    length = x1 - x0; xc = (x0 + x1) / 2; seat_top = F + .5
    cube('divan frame', (xc, F + .28, z), (length, .44, .92), MAT['carved wood'], .04)
    for x in (x0 + .12, x1 - .12):
        for dz in (-.36, .36):
            rod('divan leg', (x, F, z + dz), (x, F + .1, z + dz), .06, MAT['carved wood'])
    n = max(2, int(length / .8))
    for i in range(n):
        x = x0 + (i + .5) * length / n
        cushion('divan seat', (x, seat_top + .13, z), (length / n - .04, .26, .86), MAT['ochre canvas' if i % 2 else 'deep teal canvas'])
        cushion('divan back', (x, seat_top + .55, z - .34), (length / n - .06, .62, .22), MAT['deep teal canvas' if i % 2 else 'ochre canvas'])
    for x in (x0 - .02, x1 + .02):
        cube('divan arm', (x, seat_top + .18, z), (.12, .36, .9), MAT['carved wood'], .02)
    cube('divan back timber', (xc, seat_top + .5, z - .48), (length + .1, .9, .1), MAT['carved wood'], .03)
    return seat_top + .26


def low_table(x, z, size=(1.3, .9)):
    cube('low table top', (x, F + .42, z), (size[0], .1, size[1]), MAT['carved wood'], .03)
    for dx in (-1, 1):
        for dz in (-1, 1):
            rod('table leg', (x + dx * size[0] * .42, F, z + dz * size[1] * .4), (x + dx * size[0] * .38, F + .4, z + dz * size[1] * .36), .04, MAT['carved wood'])
    vase('table pitcher', (x - .25, F + .47, z + .1), .3, .12, MAT['clay vessels'])
    vase('table cup', (x + .3, F + .47, z - .15), .16, .07, MAT['clay vessels'])


def rug(x, z, size):
    cube('rug', (x, F + .012, z), (size[0], .025, size[1]), MAT['dark rug'], .008)
    for dx in (-1, 1): cube('rug border', (x + dx * (size[0] / 2 - .07), F + .026, z), (.1, .01, size[1] - .1), MAT['rug border'], .003)
    for dz in (-1, 1): cube('rug border', (x, F + .026, z + dz * (size[1] / 2 - .07)), (size[0] - .1, .01, .1), MAT['rug border'], .003)


def lounge():
    shell(door_x=1.5)
    # banquette contre le mur du fond, a gauche, face a la rue
    seat = divan(-2.1, .1, -D + .75)
    low_table(-1.0, -D + 1.9, (1.2, .7))
    rug(-1.0, -D + 1.85, (2.5, 2.1))
    pendant_lamp((-1.0, 2.0, -D + 1.85))
    # coffre, jarres cote droit ; tenture cote gauche
    cube('tall chest', (2.05, F + .55, -1.4), (.5, 1.1, .85), MAT['carved wood'], .03)
    for y in (F + .28, F + .85): cube('chest strap', (2.05, y, -1.4), (.54, .07, .89), MAT['copper bindings'], .005)
    vase('water jar', (1.0, F, -D + .55), .85, .3, MAT['clay vessels'])
    vase('small jar', (.55, F, -D + .5), .45, .18, MAT['clay vessels'])
    cloth('wall hanging', (-2.35, F + 1.9, -1.7), (.04, 1.1, 1.3), MAT['ochre canvas'])
    for y in (F + 1.4, F + 2.45): cube('hanging rod', (-2.33, y, -1.7), (.05, .05, 1.45), MAT['carved wood'], .01)
    # plante en pot pres de la fenetre, cote droit
    vase('plant pot', (1.95, F, -.75), .45, .22, MAT['clay vessels'])
    for i in range(5):
        a = i * math.tau / 5
        ellipsoid('plant leaves', (1.95 + math.cos(a) * .2, F + .7 + (i % 2) * .12, -.75 + math.sin(a) * .2), (.15, .28, .08), MAT['plant green'], a)
    seats = [-1.7, -1.0, -.3]
    return {'seat_top': seat, 'lamp': [-1.0, 2.0, -D + 1.85],
            'sitting': {'position': [seats[1], round(seat - .7618, 3), -D + .8], 'yaw': 0, 'seats_x': seats},
            'couple': [{'position': [.7, F, -2.3], 'yaw': .75}, {'position': [1.7, F, -1.95], 'yaw': -2.35}]}


def bedroom():
    shell(door_x=-1.5)
    # lit le long du mur droit, tete contre le mur du fond
    bx, z0, z1 = 1.35, -1.15, -3.2; zc = (z0 + z1) / 2; top = F + .42
    cube('bed frame', (bx, F + .24, zc), (1.5, .36, z1 - z0), MAT['carved wood'], .04)
    for z in (z0 + .1, z1 - .1):
        for dx in (-.6, .6): rod('bed leg', (bx + dx, F, z), (bx + dx, F + .08, z), .06, MAT['carved wood'])
    cube('bed head board', (bx, F + 1.0, z1 + .02), (1.56, .8, .1), MAT['carved wood'], .03)
    cushion('mattress', (bx, top + .11, zc), (1.4, .22, z1 - z0 - .12), MAT['linen'])
    cushion('pillow', (bx, top + .3, z1 + .4), (1.0, .18, .5), MAT['linen'])
    cushion('blanket', (bx, top + .27, zc + .35), (1.44, .12, (z1 - z0) * .62), MAT['deep teal canvas'])
    cube('blanket fold', (bx, top + .34, z0 + .55), (1.44, .06, .5), MAT['ochre canvas'], .01)
    # coffre au pied du lit, table de chevet avec lampe a huile
    cube('foot chest', (bx, F + .28, z0 + .45), (1.0, .56, .5), MAT['carved wood'], .03)
    cube('chest strap', (bx, F + .28, z0 + .45), (1.04, .07, .54), MAT['copper bindings'], .005)
    cube('bedside table', (.3, F + .55, -2.95), (.5, .08, .5), MAT['carved wood'], .02)
    for dx in (-.18, .18):
        for dz in (-.18, .18): rod('bedside leg', (.3 + dx, F, -2.95 + dz), (.3 + dx, F + .52, -2.95 + dz), .03, MAT['carved wood'])
    vase('bedside jar', (.15, F + .6, -2.85), .22, .09, MAT['clay vessels'])
    cube('oil lamp base', (.45, F + .63, -3.05), (.14, .06, .14), MAT['dark bronze'], .01)
    ellipsoid('oil lamp flame', (.45, F + .74, -3.05), (.05, .09, .05), MAT['lamplight glass'])
    rug(-.2, -2.1, (1.3, 1.9))
    # vetements pendus et tabouret cote gauche
    cube('peg rail', (-2.32, F + 2.05, -2.2), (.06, .08, 1.3), MAT['carved wood'], .01)
    cloth('hung tunic', (-2.28, F + 1.5, -1.9), (.06, 1.0, .5), MAT['ochre canvas'])
    cloth('hung wrap', (-2.28, F + 1.45, -2.55), (.06, 1.1, .6), MAT['deep teal canvas'])
    cube('stool', (-1.7, F + .42, -1.0), (.45, .07, .45), MAT['carved wood'], .015)
    for a in range(3):
        ang = a * math.tau / 3
        rod('stool leg', (-1.7 + math.cos(ang) * .16, F, -1.0 + math.sin(ang) * .16), (-1.7 + math.cos(ang) * .12, F + .4, -1.0 + math.sin(ang) * .12), .025, MAT['carved wood'])
    vase('floor jar', (-2.0, F, -2.85), .65, .26, MAT['clay vessels'])
    return {'lamp': [.45, F + .74, -3.05], 'mattress_top': top + .22,
            'sleeping': {'position': [bx, round(top + .22, 3), zc - .1], 'yaw': 0}}


def kitchen():
    shell(door_x=-2.2)
    # atre sur le mur droit, avec hotte, marmite et braises
    # atre adosse au mur du fond, a droite, pour que la cuisiniere soit vue de la rue
    hx, hz = 2.3, -D + .75
    cube('hearth base', (hx, F + .42, hz), (1.7, .84, 1.0), MAT['hearth stone'], .03)
    cube('hearth top slab', (hx, F + .87, hz), (1.76, .08, 1.06), MAT['warm stone'], .02)
    cube('hearth back', (hx, F + 1.4, -D + .35), (1.7, 1.1, .3), MAT['hearth stone'], .03)
    cube('fire bed', (hx, F + .94, hz + .1), (.8, .1, .6), MAT['fire glow'], .01)
    for i in range(4):
        rod('log', (hx - .3, F + 1.0, hz - .2 + i * .15), (hx + .3, F + 1.04, hz - .15 + i * .15), .05, MAT['carved wood'])
    cube('hood', (hx, F + 2.25, hz - .1), (1.8, .7, 1.1), MAT['sunbaked plaster'], .05)
    cube('hood chimney', (hx, CEIL - .2, hz - .2), (.9, .5, .7), MAT['sunbaked plaster'], .04)
    for dx in (-.5, .5): rod('pot bar', (hx + dx, F + 1.75, hz - .4), (hx + dx, F + 1.75, hz + .4), .02, MAT['dark bronze'])
    rod('pot hook', (hx, F + 1.75, hz + .1), (hx, F + 1.5, hz + .1), .015, MAT['dark bronze'])
    ellipsoid('cooking pot', (hx, F + 1.32, hz + .1), (.36, .28, .36), MAT['dark bronze'])
    cube('pot rim', (hx, F + 1.56, hz + .1), (.6, .05, .6), MAT['dark bronze'], .01)
    # plan de travail le long du mur du fond, jarres et etageres
    cz = -D + .5
    cube('counter body', (-1.5, F + .42, cz), (3.2, .84, .7), MAT['warm stone'], .03)
    cube('counter top', (-1.5, F + .88, cz), (3.3, .08, .78), MAT['carved wood'], .02)
    for i, x in enumerate((-2.8, -2.1, -1.2, -.3)):
        vase('counter jar', (x, F + .92, cz - .05 + (i % 2) * .15), .3 + (i % 3) * .08, .1 + (i % 2) * .03, MAT['clay vessels'])
    cube('cutting board', (-1.7, F + .94, cz + .2), (.5, .04, .35), MAT['carved wood'], .008)
    cube('bread basket', (-.6, F + .96, cz + .15), (.5, .16, .36), MAT['rug border'], .03)
    cube('kitchen shelf', (-1.5, F + 1.6, -D + .28), (3.0, .06, .32), MAT['carved wood'], .012)
    for i in range(4):
        vase('shelf jar', (-2.6 + i * .75, F + 1.63, -D + .3), .22 + (i % 2) * .1, .08, MAT['clay vessels'])
    cube('shelf basket', (-.6, F + 1.7, -D + .3), (.45, .2, .3), MAT['rug border'], .03)
    cube('kitchen shelf', (-1.5, F + 2.15, -D + .28), (3.0, .06, .32), MAT['carved wood'], .012)
    for i in range(3):
        cube('folded cloth', (-2.5 + i * .9, F + 2.2, -D + .3), (.5, .1, .28), MAT['ochre canvas' if i % 2 else 'deep teal canvas'], .02)
    # herbes suspendues a une poutre, table et tabourets pres de la fenetre
    for i, x in enumerate((-2.6, -2.3, -2.0, -1.7)):
        rod('herb string', (x, CEIL - .2, -1.9), (x, CEIL - .55, -1.9), .006, MAT['rug border'])
        ellipsoid('herb bundle', (x, CEIL - .75, -1.9), (.09, .22, .09), MAT['plant green'])
    cube('kitchen table top', (-1.7, F + .8, -1.9), (1.3, .08, .9), MAT['carved wood'], .02)
    for dx in (-.55, .55):
        for dz in (-.36, .36): rod('kitchen table leg', (-1.7 + dx, F, -1.9 + dz), (-1.7 + dx, F + .76, -1.9 + dz), .04, MAT['carved wood'])
    vase('table bowl', (-1.5, F + .84, -1.8), .14, .18, MAT['clay vessels'])
    for sx in (-2.5, -.9):
        cube('stool', (sx, F + .45, -1.9), (.42, .07, .42), MAT['carved wood'], .015)
        for a in range(4):
            ang = a * math.tau / 4 + .4
            rod('stool leg', (sx + math.cos(ang) * .16, F, -1.9 + math.sin(ang) * .16), (sx + math.cos(ang) * .13, F + .42, -1.9 + math.sin(ang) * .13), .025, MAT['carved wood'])
    vase('floor amphora', (-3.0, F, -3.6), .9, .3, MAT['clay vessels'])
    cube('firewood stack', (3.05, F + .2, -2.2), (.7, .4, .9), MAT['carved wood'], .03)
    return {'lamp': [hx, F + 1.0, hz + .3],
            'cooking': {'position': [hx, F, hz + .95], 'yaw': math.pi}}


LAYOUTS = {'home-lounge': lounge, 'home-bedroom': bedroom, 'home-kitchen': kitchen}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, rgb, rough, tex in MATERIALS:
        m = bpy.data.materials.new(name); m.use_nodes = True
        bsdf = m.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value = (*rgb, 1)
        bsdf.inputs['Roughness'].default_value = rough
        if name in EMISSIVE:
            bsdf.inputs['Emission Color'].default_value = (*rgb, 1); bsdf.inputs['Emission Strength'].default_value = 6.0


def export(layout):
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.get('export')]
    verts = []; draws = []; deps = bpy.context.evaluated_depsgraph_get()
    for o in sorted(objects, key=lambda x: (x['material_index'], x.name)):
        e = o.evaluated_get(deps); m = e.to_mesh(); m.calc_loop_triangles(); start = len(verts)
        for tri in m.loop_triangles:
            for vi, li in zip(tri.vertices, tri.loops):
                p = e.matrix_world @ m.vertices[vi].co
                n = e.matrix_world.to_3x3().inverted().transposed() @ m.corner_normals[li].vector; n.normalize()
                q = (p.x, p.z, -p.y); normal = (n.x, n.z, -n.y)
                uv = (q[0] * .7 + q[2] * .23, q[1] * .7 + q[2] * .6)
                verts.append((*q, *normal, *uv, 1., 1., 1., 1.))
        count = len(verts) - start; mi = o['material_index']
        if draws and draws[-1]['material'] == mi: draws[-1]['count'] += count
        else: draws.append({'first': start, 'count': count, 'material': mi})
        e.to_mesh_clear()
    binary = HERE / (layout + '.bin')
    with binary.open('wb') as f:
        for row in verts: f.write(struct.pack('<12f', *row))
    meta = {'schema': 'city-room-mesh-v1', 'units': 'metres', 'floor_y': F, 'dimensions': [W, CEIL - F, D],
            'binary': binary.name, 'stride_floats': 12, 'vertex_count': len(verts), 'draws': draws,
            'materials': [{'name': n, 'color': list(c), 'roughness': r, 'texture_kind': t, 'emissive': n in EMISSIVE} for n, c, r, t in MATERIALS],
            'sha256': hashlib.sha256(binary.read_bytes()).hexdigest()}
    (HERE / (layout + '.json')).write_text(json.dumps(meta, indent=2) + '\n')
    return len(verts)


def preview(layout, placements):
    """Rendu depuis la rue a travers un masque de facade, oeil a hauteur de Jak."""
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 48
    scene.world = bpy.data.worlds.new('street'); scene.world.color = (.05, .05, .06)
    scene.render.resolution_x = 1100; scene.render.resolution_y = 800; scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    # masque : la facade autour du trou exterieur (3,2 x 2,8 de y=0,1 a 2,9)
    big = 30
    cube('mask top', (0, 2.9 + big / 2, .2), (big, big, .3), MAT['shadow plaster'], 0, export=False)
    cube('mask bottom', (0, .1 - big / 2, .2), (big, big, .3), MAT['shadow plaster'], 0, export=False)
    for side in (-1, 1): cube('mask side', (side * (1.6 + big / 2), 1.5, .2), (big, big, .3), MAT['shadow plaster'], 0, export=False)
    # silhouettes des occupants (boites a la taille des acteurs) pour juger l'echelle
    for name, p in placements.items():
        if name not in ('sitting', 'sleeping', 'cooking', 'couple'): continue
        pos = p['position'] if isinstance(p, dict) else None
        if name == 'sitting': cube('occupant ' + name, (pos[0], pos[1] + .95, pos[2]), (.8, 1.86, .9), MAT['dark bronze'], .05, export=False)
        elif name == 'sleeping': cube('occupant ' + name, (pos[0], pos[1] + .2, pos[2]), (.8, .4, 2.2), MAT['dark bronze'], .05, export=False)
        elif name == 'cooking': cube('occupant ' + name, (pos[0], pos[1] + 1.15, pos[2]), (.7, 2.3, .5), MAT['dark bronze'], .05, export=False)
        elif name == 'couple':
            for q in p: cube('occupant couple', (q['position'][0], q['position'][1] + 1.15, q['position'][2]), (.7, 2.3, .5), MAT['dark bronze'], .05, export=False)
    for name, p, color, power, size in [('daylight', (0, 1.4, 1.2), (1., .86, .66), 420, 3),
                                        ('room lamp', tuple(placements['lamp']), (1., .6, .25), 180, .8)]:
        d = bpy.data.lights.new(name, 'AREA' if name == 'daylight' else 'POINT'); d.energy = power; d.color = color
        if name == 'daylight': d.shape = 'DISK'; d.size = size
        o = bpy.data.objects.new(name, d); scene.collection.objects.link(o); o.location = local(p)
        if name == 'daylight': o.rotation_euler = (Vector(local((0, .6, -2.5))) - o.location).to_track_quat('-Z', 'Y').to_euler()
    camdata = bpy.data.cameras.new('street'); cam = bpy.data.objects.new('street', camdata); scene.collection.objects.link(cam)
    scene.camera = cam; camdata.lens = 30
    # deux points de vue : Jak dans la rue (oeil vers l'appui) et Jak grimpe sur l'appui
    for suffix, eye, target in (('street', (.5, .35, 4.2), (-.1, 1.0, -2.6)), ('sill', (.3, 1.6, 1.0), (-.1, .7, -3.2))):
        cam.location = local(eye); cam.rotation_euler = (Vector(local(target)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(HERE / f'{layout}-preview-{suffix}.png'); bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / (layout + '.blend')))


def main():
    preview_only = '--preview-only' in sys.argv
    summary = {}
    for layout, build in LAYOUTS.items():
        reset()
        placements = build()
        count = 0 if preview_only else export(layout)
        preview(layout, placements)
        summary[layout] = {'vertices': count, 'placements': {k: v for k, v in placements.items()}}
        print(layout, 'sommets', count, flush=True)
    (HERE / 'placements.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__': main()
