"""Une piece physique par appartement, avec une variete stable et sans voisines identiques.

Regles demandees par l'utilisateur (17 septembre) :
- une fenetre doit donner sur l'interieur d'une vraie maison : pieces homes/ (salon, chambre,
  cuisine) de taille reelle, sol 45 cm sous l'appui, porte vers un couloir ;
- jamais deux scenes identiques a portee de vue l'une de l'autre ;
- si une scene revient, changer au moins l'agencement (piece en miroir, place sur la
  banquette) et le personnage ;
- le tirage ne depend que de l'identifiant de la fenetre et de ses voisines, jamais de la
  camera : il est stable pendant toute la session.

Les pieces homes/ ne sont pas mises a l'echelle de l'ouverture : seul le miroir (x -> -x) varie.
"""
import hashlib, json, math
from pathlib import Path

SHARED = ('wca-house1-west-room', 'wca-house1-east-room')
FIT_FILE = Path(__file__).resolve().parent / 'room-fit.json'   # echelles par fenetre mesurees par fit_rooms.py
NEIGHBOUR_RADIUS = 45.0        # m : deux fenetres plus proches que cela ne recoivent jamais la meme scene
HALF_PI = 1.5707963267948966
F = -.45                       # sol des pieces homes/ (author_homes.py)
CARPET = .058                  # semelles posees sur le tapis
D = 3.4                            # profondeur des pieces homes/
LOUNGE_SEATS = (-1.7, -1.0, -.3)   # x des trois places de la banquette du salon
LOUNGE_SEAT_TOP = F + .76          # dessus des coussins
SEAT_HEIGHT = {'sitting-male': .6624 * 1.15, 'sitting-female': .63 * 1.15}   # hauteur d'assise des acteurs installes
LAMPS = {'home-lounge': [-1.0, 2.0, -D + 1.85], 'home-bedroom': [.45, F + .74, -3.05], 'home-kitchen': [1.7, F + 1.0, -1.9]}
BED = {'x': 1.35, 'top': F + .64, 'z': -2.275}
HEARTH = {'x': .8, 'z': -1.9}      # position de la cuisiniere, de profil face a l'atre du mur droit


def h(*parts):
    return int.from_bytes(hashlib.sha256('|'.join(map(str, parts)).encode()).digest()[:4], 'big')


def actor(mesh, x, y, z, yaw):
    return {'mesh': mesh, 'position': [round(x, 3), round(y, 4), round(z, 3)], 'yaw': round(yaw, 4), 'phase': 0}


def variants(inhabited):
    """Scenes possibles pour une fenetre. `key` resume ce qui se voit : piece, personnages, miroir, place."""
    out = []
    for m in (1, -1):
        if not inhabited:
            for mesh in ('home-lounge', 'home-bedroom', 'home-kitchen'):
                out.append({'key': (mesh, 'vide', m, 0), 'mesh': mesh, 'mirror': m, 'actors': []})
            continue
        for who in ('sitting-male', 'sitting-female'):
            for seat, x in enumerate(LOUNGE_SEATS):
                out.append({'key': ('home-lounge', who, m, seat), 'mesh': 'home-lounge', 'mirror': m,
                            'actors': [actor(who, x * m, LOUNGE_SEAT_TOP - SEAT_HEIGHT[who], -D + .8, 0)]})
        out.append({'key': ('home-lounge', 'couple', m, 0), 'mesh': 'home-lounge', 'mirror': m,
                    'actors': [actor('conversing-male', .7 * m, F + CARPET, -2.3, .75 * m),
                               actor('conversing-female', 1.7 * m, F + CARPET, -1.95, -2.35 * m)]})
        for who in ('sleeping-male', 'sleeping-female'):
            out.append({'key': ('home-bedroom', who, m, 0), 'mesh': 'home-bedroom', 'mirror': m,
                        'actors': [actor(who, BED['x'] * m, BED['top'], BED['z'], 0)]})
        for who in ('cooking-female', 'cooking-male'):
            out.append({'key': ('home-kitchen', who, m, 0), 'mesh': 'home-kitchen', 'mirror': m,
                        'actors': [actor(who, HEARTH['x'] * m, F, HEARTH['z'], HALF_PI * m)]})
    return out


def similarity(a, b):
    """0 = rien en commun ; plus c'est haut, plus les deux scenes se ressemblent vues de la rue."""
    score = 0
    if a['key'] == b['key']: score += 10                                     # identiques
    if a['mesh'] == b['mesh']: score += 4                                    # meme piece
    if {x['mesh'] for x in a['actors']} & {x['mesh'] for x in b['actors']}: score += 3   # meme personnage
    if a['mirror'] == b['mirror']: score += 1                                # meme orientation
    return score


def rooms_for(windows):
    by_id = {w['id']: w for w in windows}
    assert len(by_id) == len(windows)
    rooms = []; assigned = set(); placed = []      # (centre, variante) des pieces deja attribuees
    fit = json.loads(FIT_FILE.read_text(encoding='utf-8')) if FIT_FILE.exists() else {}
    if all(name in by_id for name in SHARED):
        corner = {'id': 'wca-house1-corner-apartment', 'anchor': SHARED[0], 'windows': list(SHARED),
                  'mesh': 'corner-conversation', 'scale': [1, 1, 1], 'lamp': [.55, 2.8, -1.7], 'actors': [
                      {'mesh': 'conversing-male', 'position': [.25, .058, -2.15], 'yaw': 2.214297435588181, 'phase': 0},
                      {'mesh': 'conversing-female', 'position': [1.45, .058, -3.05], 'yaw': -0.9272952180016122, 'phase': 0}]}
        rooms.append(corner); assigned.update(SHARED)
        placed.append((by_id[SHARED[0]]['center'], {'key': ('corner', 'couple', 1, 0), 'mesh': 'corner-conversation', 'mirror': 1, 'actors': corner['actors']}))
    for w in sorted(windows, key=lambda w: w['id']):
        if w['id'] in assigned: continue
        choices = variants(w['inhabited'])
        neighbours = [v for centre, v in placed if math.dist(centre, w['center']) < NEIGHBOUR_RADIUS]
        # La scene la moins ressemblante a ses voisines gagne ; a egalite, tirage stable par identifiant.
        choices.sort(key=lambda v: (sum(similarity(v, n) for n in neighbours), h(w['id'], v['key'])))
        chosen = choices[0]
        phase = (h(w['id'], 'phase') % 800) / 100.0          # 0 a 7,99 s, commune aux deux interlocuteurs
        # echelle mesuree : la piece ne doit pas ressortir du batiment (fit_rooms.py) ; les acteurs suivent
        sx, _, sz = fit.get(w['id'], {}).get('scale', [1, 1, 1])
        actors = []
        for a in chosen['actors']:
            p = a['position']
            actors.append(dict(a, position=[round(p[0] * sx, 3), p[1], round(p[2] * sz, 3)], phase=round(phase, 2)))
        lamp = list(LAMPS[chosen['mesh']]); lamp[0] *= chosen['mirror'] * sx; lamp[2] *= sz
        rooms.append({'id': w['id'] + '-apartment', 'anchor': w['id'], 'windows': [w['id']], 'mesh': chosen['mesh'],
                      'scale': [round(chosen['mirror'] * sx, 3), 1, round(sz, 3)], 'lamp': lamp, 'actors': actors,
                      'variant': '/'.join(map(str, chosen['key']))})
        assigned.add(w['id']); placed.append((w['center'], chosen))
    assert assigned == set(by_id)
    return rooms
