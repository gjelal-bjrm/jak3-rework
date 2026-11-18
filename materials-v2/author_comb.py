"""Catacombes precurseurs : matieres v2 (metal precurseur, tuyaux, dalles alveolees, grilles...).

Lancement (Python de Blender : numpy + PIL) :
  "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" materials-v2/author_comb.py

Chaque texture d'origine (128 px, ombres et reflets peints) est RECREEE : on reprend son dessin exact (rainures,
nervures, alveoles, mesures sur l'original) et on le reconstruit en relief reel, avec une couleur propre sans ombre
peinte, une rugosite et des creux. Le rendu (materials_v2.glsl) eclaire ce relief avec les lampes du lieu.
Le grain fin du metal (martelage, piqures, rayures) et ses grandes variations (patine, zones polies) sont deux jeux
de cartes plaques selon le monde : meme finesse partout, quel que soit l'etirement de la texture d'origine.
Sorties : materials-v2/out/*.rgba (+ .png) et comb/materials.json (lu par remaster-build/build.py : couleurs
remplacees, cartes de relief / matiere et jeux du monde ajoutes a chaque niveau qui contient ces textures).
"""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from mv2lib import *

SRC = ROOT / 'data/decompiler_out/jak3/textures'
OUT = HERE / 'out'
FAMILY, GRAIN_TILE, MACRO_TILE = 'comb', 1.6, 9.0
LEVELS = ('comb', 'rail')          # prefixes des niveaux ou la famille s'applique
albedo_list, map_list, world_list = [], [], []


def original(name, page='comba-tfrag'):
    return np.asarray(Image.open(SRC / page / f'{name}.png').convert('RGBA'), float)


def mean_rgb(name, page='comba-tfrag'):
    return original(name, page)[..., :3].reshape(-1, 3).mean(0)


def alpha_of(name, w, h, page='comba-tfrag'):
    a = Image.fromarray(original(name, page)[..., 3].astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(a, np.uint8)


def emit(name, albedo, alpha, normal, hm, grain, rough, metal, emis, cav):
    """Ecrit les trois cartes d'une texture."""
    hn = (hm - hm.min()) / max(hm.max() - hm.min(), 1e-9) if np.ptp(hm) > 0 else np.full(hm.shape, .5)
    if albedo is not None:
        albedo_list.append(save(OUT, name, np.dstack([to8(albedo), alpha])))
    map_list.append(dict(save(OUT, name + '.n', pack_normal(normal, hn, grain)), base=name))
    map_list.append(dict(save(OUT, name + '.m', pack_matter(rough, metal, emis, cav)), base=name))


def bronze(name, w, h, tile, hm, base=None, rough0=.42, grain=1., gain=1.6, seed=1, page='comba-tfrag',
           patina=.40, wear=.22, metal=1., lum_extra=None, rough_extra=None):
    """Metal precurseur a partir d'un relief (m). tile : metres par repetition (u, v)."""
    base = mean_rgb(name, page) if base is None else np.asarray(base, float)
    px = tile[0] / w                                                # m par pixel
    n = normal_from_height(hm, tile[0], tile[1], gain)
    cav = cavity(hm, .06 / px, .012) * cavity(hm, .015 / px, .004)   # grands creux x fines gravures
    edge = edges(hm, .03 / px, .006)
    lum = 1. + .035 * fft_noise(w, h, 2.4, seed, 2, 40)
    lum *= 1. - patina * (1. - cav)                                 # patine sombre au fond des creux
    lum *= 1. + wear * edge                                         # aretes polies par l'usure
    if lum_extra is not None: lum = lum * lum_extra
    col = colour_field(base * 1.04, lum, 1.08)
    col = col * (1. - (1. - cav)[..., None] * np.array([.0, .03, .07]))          # patine un peu plus froide
    rough = np.clip(rough0 + .30 * (1. - cav) - .14 * edge, .18, .95)
    if rough_extra is not None: rough = np.clip(rough + rough_extra, .18, .95)
    emit(name, np.clip(col, 0, 1), alpha_of(name, w, h, page), n, hm, grain, rough, metal, 0., cav)


# ---------------------------------------------------------------- jeux plaques selon le monde
def world_grain(w=1024, tile=GRAIN_TILE):
    """Grain fin du metal : peau de fonderie, martelage doux, quelques piqures et rayures. Volontairement calme :
    un grain trop marque scintille (effet de givre) sous une lampe proche."""
    px = tile / w
    cast = fft_noise(w, w, 2.2, 11, 10, 160) * .00010                           # peau de fonderie
    dimples = splats(w, w, 700, .016 / px, 12)                                  # martelage doux (~3 cm)
    dimples = (dimples - dimples.mean()) / dimples.std() * .00030
    pits_field = splats(w, w, 900, .0022 / px, 13, (.3, 1.))                    # piqures (3-4 mm), eparses
    pits = np.clip(pits_field / pits_field.max() * 1.6, 0, 1)
    fine = scratches(w, w, 260, 14, (.04, .25), .8)                             # rayures fines
    deep = scratches(w, w, 22, 15, (.08, .5), 1.5)                              # quelques rayures franches
    hm = cast + dimples - pits * .00030 - blur(fine, .8) * .00010 - blur(deep, 1.) * .00030
    n = normal_from_height(hm, tile, tile, 1.0)
    slope = np.hypot(n[..., 0], n[..., 1]) / n[..., 2]
    n = normal_from_height(hm, tile, tile, .055 / np.sqrt((slope ** 2).mean()))  # pente efficace 0,055
    cav = np.clip(1. - pits * .8 - blur(deep, 1.) * .7 - blur(fine, .8) * .2, 0, 1)
    rmod = .5 + .10 * fft_noise(w, w, 2.4, 16, 3, 50) + .15 * pits - .06 * blur(fine, .8)
    world_list.append(save(OUT, f'mv2-grain-{FAMILY}', np.dstack([to8(n[..., 0] * .5 + .5), to8(n[..., 1] * .5 + .5), to8(cav), to8(rmod)])))


def world_macro(w=1024):
    """Grandes variations du metal : nuages doux de patine (un peu plus sombre et mat) et de zones polies (un peu plus
    claires et lisses), legers ecarts de teinte. Volontairement discret : c'est du metal, pas de la pierre tachee."""
    clouds = fft_noise(w, w, 3.4, 21, 1, 12); mottle = fft_noise(w, w, 2.6, 22, 5, 60); hue = fft_noise(w, w, 3.0, 23, 1, 10)
    patina = smooth(-1.6, 1.6, clouds + mottle * .22)                           # 0 : metal poli, 1 : oxyde
    polished, oxid = np.array([1.07, 1.045, 1.0]), np.array([.90, .885, .89])
    tint = polished + (oxid - polished) * patina[..., None]
    warm, yellow = np.array([1.03, .985, .955]), np.array([.99, 1.012, .965])
    tint = tint * (warm + (yellow - warm) * smooth(-1.4, 1.4, hue)[..., None])
    rough = .5 + (patina - .5) * .30 + .03 * mottle
    world_list.append(save(OUT, f'mv2-macro-{FAMILY}', np.dstack([to8(tint * .5), to8(rough)])))


def world_env(w=512, h=256, probe=(8., 9., 6.7)):
    """Reflets de la salle sur le metal : panorama (equirectangulaire) des lampes vues du centre du lieu, sur un fond
    sombre et chaud. Chaque lampe du niveau (materials-v2/lights/<niveau>-lamps.json) y est une tache de sa couleur,
    a sa place et a sa taille apparente. Lu avec un flou qui grandit avec la rugosite. Codage : racine(radiance / 4)."""
    lamps = json.loads((HERE / 'lights/comba-lamps.json').read_text())['faces']
    groups = {}
    for f in lamps:
        if f['geom'] == 0: groups.setdefault((f['material'], f['tree'], f['instance']), []).append(f)
    lon = (np.arange(w) + .5) / w * 2 * np.pi - np.pi; lat = (np.arange(h) + .5) / h * np.pi      # lat : 0 = haut
    LON, LAT = np.meshgrid(lon, lat)
    D = np.stack([np.sin(LAT) * np.cos(LON), np.cos(LAT), np.sin(LAT) * np.sin(LON)], -1)       # x, y (haut), z
    up = D[..., 1]
    # fond : salle sombre et chaude ; lueur ambree du plafond (lampes jaunes), lueur bleue a l'horizon (neons bleus
    # a hauteur d'homme) : le metal prend des reflets chauds sur le dessus, froids en vue rasante
    floor, horizon, ceiling = np.array([.030, .020, .012]), np.array([.040, .040, .052]), np.array([.105, .062, .022])
    band = np.exp(-(up / .16) ** 2)[..., None]
    env = (floor + (ceiling - floor) * smooth(-.1, .75, up)[..., None]) * (1. - .6 * band) + horizon * band
    colours = {'comb-temp-glass': np.array([.10, .30, 1.0]), 'comb-yell-light': np.array([1.0, .62, .12])}
    for (material, *_), fs in groups.items():
        P = np.array([[v['p'] for v in f['vertices']] for f in fs])
        area = (np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1) / 2).sum()
        c = P.reshape(-1, 3).mean(0) - np.array(probe); r = np.linalg.norm(c)
        if r < 2. or r > 140.: continue
        d = c / r
        theta = np.clip(np.sqrt(area / np.pi) / r, .03, .35)                     # rayon apparent (rad), 2 degres au moins
        cosang = np.clip(D @ d, -1, 1)
        blob = np.exp(-(1. - cosang) / (theta * theta * .5))
        env += blob[..., None] * colours[material][None, None, :] * 2.6 * min(1., 30. / r)
    env = np.sqrt(np.clip(env / 4., 0, 1))
    world_list.append(save(OUT, f'mv2-env-{FAMILY}', np.dstack([to8(env), np.full((h, w), 255, np.uint8)])))


def lamp(name, w=1024, h=512, core=.12):
    """Lampe : recreee en haute definition d'apres le dessin d'origine (bande lumineuse en travers, cloisons).
    Deux couches : la lumiere interieure (couleur : halo + tube lumineux au centre) et la surface du verre (relief :
    cloisons, segments bombes ; hauteur = transparence). Le rendu decale la lumiere derriere le verre (parallaxe)."""
    o = original(name)[..., :3] / 255.
    oh, ow = o.shape[:2]
    lum = o @ np.array([.2126, .7152, .0722])
    # rampe de couleur de l'original : couleur moyenne par niveau de luminance
    order = np.argsort(lum.ravel()); bins = np.array_split(order, 24)
    ramp_l = np.array([lum.ravel()[b].mean() for b in bins]); ramp_c = np.array([o.reshape(-1, 3)[b].mean(0) for b in bins])
    pv = lum.mean(1); su = lum.mean(0)
    # variation large en u (sans les cloisons fines) et cloisons
    pad = np.concatenate([su[-8:], su, su[:8]])
    closed = np.array([pad[i:i + 5].max() for i in range(len(pad) - 4)])
    closed = np.array([closed[i:i + 5].min() for i in range(len(closed) - 4)])[4:4 + ow]
    k = np.exp(-.5 * (np.arange(-12, 13) / 4.) ** 2); k /= k.sum()
    broad = np.convolve(np.concatenate([closed[-12:], closed, closed[:12]]), k, 'valid')[:ow]
    sep = np.clip((broad * .78 - su) / (broad * .25 + 1e-6), 0, 1)                # 1 sur une cloison
    xs = (np.arange(w) + .5) / w * ow - .5; ys = (np.arange(h) + .5) / h * oh - .5
    broad_hd = np.interp(xs, np.arange(ow), broad, period=ow)
    sep_hd = np.interp(xs, np.arange(ow), sep, period=ow)
    sep_hd = smooth(.35, .65, sep_hd)                                            # bords nets a haute definition
    pv_hd = np.interp(ys, np.arange(oh), pv)
    v = (np.arange(h) + .5) / h
    peak = float(ys[np.argmax(pv_hd)] + .5) / oh
    tube = np.exp(-((v - peak) / .085) ** 2)                                     # coeur un peu plus vif (discret : le
    inner_l = (pv_hd[:, None] / pv.max()) * (broad_hd[None, :] / broad.max())    # dessin d'origine reste le meme)
    inner_l = np.clip(inner_l + core * tube[:, None] * (broad_hd[None, :] / broad.max()), 0, 1.25)
    target = inner_l * lum.max()
    col = np.stack([np.interp(target, ramp_l, ramp_c[:, c]) for c in range(3)], -1)
    hot = np.clip(target - ramp_l[-1], 0, 1)[..., None]                          # au-dela du plus clair : coeur plus clair
    col = np.clip(col + hot * (1. - col) * 1.5, 0, 1)
    albedo_list.append(save(OUT, name, np.dstack([to8(col), alpha_of(name, w, h)])))
    # surface du verre : cloisons en creux, segments legerement bombes
    seg = blur(np.broadcast_to(1. - sep_hd, (h, w)).copy(), 10.)
    hm = -.004 * np.broadcast_to(sep_hd, (h, w)) + .002 * seg
    n = normal_from_height(hm, 6., 1., 1.)
    trans = 1. - .78 * np.broadcast_to(sep_hd, (h, w))                           # transparence (cloisons sombres)
    map_list.append(dict(save(OUT, name + '.n', pack_normal(n, trans, 0.)), base=name, lamp=True))
    map_list.append(dict(save(OUT, name + '.m', pack_matter(.14 + .3 * np.broadcast_to(sep_hd, (h, w)), 0., 1., 1.)), base=name, lamp=True))


# ---------------------------------------------------------------- textures a dessin (releves sur l'original)
def plain(name, size=64, rough0=.42, grain=1., page='comba-tfrag', base=None, emis=0., fade=None):
    """Aplat : toute la richesse vient du grain et de la variation du monde."""
    w = h = size
    base = mean_rgb(name, page) if base is None else np.asarray(base, float)
    lum = np.ones((h, w)) if fade is None else fade
    col = colour_field(base * 1.04, lum, 1.08)
    n = np.zeros((h, w, 3)); n[..., 2] = 1.
    emit(name, np.clip(col, 0, 1), alpha_of(name, w, h, page), n, np.zeros((h, w)), grain, rough0, 1., emis, 1.)


def plate_02(w=1024, h=512, tile=(6.0, 3.4)):
    """Plaque : grande face lisse, rainure verticale (u = 0,78..0,84), bandeau de rive a droite avec son arete."""
    u, v = grid(w, h)
    groove = smooth(.775, .790, u) * (1. - smooth(.830, .845, u))
    lip = smooth(.845, .852, u)                                    # bandeau de rive, un peu en retrait
    edge_line = smooth(.985, .992, u)                              # arete saillante au bord
    hm = -.028 * groove - .006 * lip + .010 * edge_line
    # rivets le long du bandeau (8 par repetition)
    ru = (u - .92) * tile[0]; rv = ((v * 8.) % 1. - .5) * tile[1] / 8.
    rivet = np.clip(1. - np.hypot(ru, rv) / .045, 0, 1)
    hm += .012 * np.sqrt(rivet) * lip
    bronze('comb-plate-02', w, h, tile, hm, seed=31)


def tarn_wall(w=1024, h=512, tile=(10.0, 4.6)):
    """Moulure murale : bandeau haut, gorge, grand demi-rond, filet, bandeau bas."""
    u, v = grid(w, h)
    top = 1. - smooth(.118, .125, v)
    gorge = smooth(.125, .132, v) * (1. - smooth(.150, .158, v))
    x = (v - .49) / .335
    torus = np.sqrt(np.clip(1. - x * x, 0, 1)) * smooth(.155, .16, v) * (1. - smooth(.82, .825, v))
    fillet = smooth(.865, .872, v) * (1. - smooth(.885, .892, v))
    bottom = smooth(.892, .9, v)
    hm = .012 * top - .022 * gorge + .085 * torus + .014 * fillet + .004 * bottom
    bronze('comb-tarn-wall-01', w, h, tile, hm, seed=32, gain=1.3)


def pipe2(w=1024, h=1024, tile=(4.8, 3.1)):
    """Lames verticales (16 par repetition) : profil en dent de scie, chaque lame recouvre la suivante."""
    u, v = grid(w, h)
    p = (u * 16.) % 1.
    hm = .020 * (p / .93) * (1. - smooth(.93, 1., p)) + .020 * smooth(.93, 1., p) * 0.
    bronze('comb-pipe2', w, h, tile, hm, seed=33, gain=1.5)


def pipe1(w=512, h=512, tile=(4.8, 4.1)):
    """Gaine annelee d'acier sombre : 16 anneaux bombes separes par des gorges etroites."""
    u, v = grid(w, h)
    p = (u * 16.) % 1.
    hm = .016 * np.abs(np.sin(np.pi * p)) ** .55
    base = np.array([92., 93., 96.])                                # acier sombre, sans le reflet peint
    bronze('comb-pipe1', w, h, tile, hm, base=base, rough0=.36, grain=.7, seed=34, patina=.55, wear=.30, gain=1.5)


def pipe3(w=512, h=512, tile=(4.4, 4.2)):
    """Tuyau lisse d'acier gris-vert : 4 colliers (bande saillante entre deux gorges) par repetition."""
    u, v = grid(w, h)
    p = ((u - 1. / 16.) * 4.) % 1.; d = np.minimum(p, 1. - p) / 4.            # distance au collier (en u)
    band = 1. - smooth(.010, .013, d)
    gorge = smooth(.013, .015, d) * (1. - smooth(.019, .022, d))
    hm = .008 * band - .006 * gorge
    base = np.array([88., 94., 90.])
    bronze('comb-pipe3', w, h, tile, hm, base=base, rough0=.33, grain=.7, seed=35, patina=.5, wear=.25)


def comb_tile(w=1024, h=1024, tile=(7.4, 6.2)):
    """Dalles alveolees : grands hexagones separes par des canaux, cercles graves autour des aretes verticales.
    Geometrie relevee sur l'original (128 px) : aretes verticales x=32 (y 100..156) et x=0 (y 46..78), periode 64 en x."""
    u, v = grid(w, h)
    X, Y = u * 128., v * 128.
    segs = []
    for kx in range(-1, 3):
        for ky in (-128., 0., 128.):
            ox = 64. * kx
            segs += [((32 + ox, 100 + ky), (32 + ox, 156 + ky)), ((ox, 46 + ky), (ox, 78 + ky)),
                     ((32 + ox, 28 + ky), (ox, 46 + ky)), ((32 + ox, 28 + ky), (64 + ox, 46 + ky)),
                     ((ox, 78 + ky), (32 + ox, 100 + ky)), ((64 + ox, 78 + ky), (32 + ox, 100 + ky))]
    dist = np.full(X.shape, 1e9)
    for (x0, y0), (x1, y1) in segs:
        dx, dy = x1 - x0, y1 - y0
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / (dx * dx + dy * dy), 0, 1)
        dist = np.minimum(dist, np.hypot(X - x0 - t * dx, Y - y0 - t * dy))
    channel = 1. - smooth(1.6, 2.9, dist)                            # canal a fond plat entre les dalles
    bevel = 1. - smooth(2.9, 4.4, dist)                              # chanfrein des dalles
    circ = np.full(X.shape, 1e9)
    for kx in range(-1, 3):
        for cy in (-128., 0., 128.):
            for cx, cyy in ((32 + 64 * kx, 0.), (64 * kx, 62.)):
                circ = np.minimum(circ, np.abs(np.hypot(X - cx, Y - cyy - cy) - 14.))
    engraving = (1. - smooth(.35, .9, circ)) * (1. - channel)
    # leger bombe de chaque dalle (coussin) : lit la lumiere des lampes
    cushion = smooth(2.9, 22., dist)
    hm = -.034 * channel - .010 * bevel * (1. - channel) - .009 * engraving + .006 * cushion
    bronze('comb-comb-tile', w, h, tile, hm, seed=36, gain=1.25, patina=.5)


def ring(w=512, h=256, tile=(4.2, 1.8)):
    """Collier : levre haute, bandeau, gorge, bandeau cannele (16 cannelures)."""
    u, v = grid(w, h)
    lipt = 1. - smooth(.045, .06, v)
    gorge = smooth(.255, .27, v) * (1. - smooth(.30, .315, v))
    p = (u * 16.) % 1.
    flute = (1. - np.abs(np.sin(np.pi * p)) ** .5) * smooth(.33, .38, v)
    hm = .008 * lipt - .014 * gorge - .006 * flute
    bronze('comb-ring', w, h, tile, hm, seed=37)


def pipe(w=512, h=512, tile=(2.2, 2.8)):
    """Tuyau de metal sombre brosse : joint horizontal (bourrelet + gorge), brossage le long du joint."""
    u, v = grid(w, h)
    bead = smooth(.455, .465, v) * (1. - smooth(.475, .485, v))
    gorge = smooth(.485, .49, v) * (1. - smooth(.50, .505, v))
    brush = blur(fft_noise(w, h, 1.0, 38, 40, 400), 0)                         # brossage : bruit etire en u
    k = np.fft.fft2(brush); fx = np.fft.fftfreq(w)[None, :]
    brush = np.fft.ifft2(k * np.exp(-(fx * w / 9.) ** 2)).real; brush /= brush.std()
    hm = .010 * bead - .008 * gorge + .00025 * brush
    base = np.array([96., 80., 78.])
    bronze('comb-pipe', w, h, tile, hm, base=base, rough0=.34, grain=.5, seed=39, patina=.5, wear=.3,
           rough_extra=.05 * brush)


def long_vent(w=1024, h=256, tile=(7.0, 2.1)):
    """Grille d'aeration : 16 fentes verticales aux bouts arrondis, dans un cadre."""
    u, v = grid(w, h)
    p = (u * 16.) % 1.
    xs = (p - .5) / 16. * tile[0]                                    # m, travers de la fente
    half_w, top, bot = .075, .20, .86
    ys = (np.clip(v, top + half_w / tile[1], bot - half_w / tile[1]) - v) * tile[1]
    d = np.hypot(xs, ys) - half_w                                    # distance signee au bord de la fente
    slot = 1. - smooth(-.012, .012, d)
    rim = (1. - smooth(.0, .03, np.abs(d))) * (1. - slot)
    frame = (1. - smooth(.05, .07, v)) + smooth(.93, .95, v)
    hm = -.045 * slot + .004 * rim + .006 * np.clip(frame, 0, 1)
    dark = 1. - .55 * slot                                           # fond de fente : noir de l'interieur
    bronze('comb-long-vent', w, h, tile, hm, seed=40, lum_extra=dark, patina=.3)


def grate(w=512, h=512, tile=(2.6, 2.6)):
    """Caillebotis d'acier : barres croisees en losanges (5 par repetition), mailles en creux."""
    u, v = grid(w, h)
    a = ((u + v) * 5.) % 1.; b = ((u - v) * 5.) % 1.
    da = np.minimum(a, 1. - a); db = np.minimum(b, 1. - b)
    bar_a = 1. - smooth(.07, .12, da); bar_b = 1. - smooth(.07, .12, db)
    bars = np.maximum(bar_a, bar_b)
    round_ = np.maximum(np.sqrt(np.clip(1. - (da / .12) ** 2, 0, 1)) * bar_a, np.sqrt(np.clip(1. - (db / .12) ** 2, 0, 1)) * bar_b)
    hm = .014 * round_ - .010 * (1. - bars)
    base = np.array([92., 96., 90.])
    bronze('comb-grate', w, h, tile, hm, base=base, rough0=.40, grain=.6, seed=41, page='comba-alpha', patina=.6,
           lum_extra=1. - .35 * (1. - bars))


def main():
    world_grain(); world_macro(); world_env()
    plate_02(); tarn_wall(); pipe2(); pipe1(); pipe3(); comb_tile(); ring(); pipe(); long_vent(); grate()
    plain('comb-crct-medium'); plain('comb-temp-dark'); plain('comb-temp-medium')
    plain('comb-crct-small', rough0=.40); plain('comb-crct-small-drk', rough0=.46)
    u, v = grid(64, 64)
    plain('comb-tarn-fade-wall-01', fade=.62 + .5 * smooth(.15, .7, v))         # fondu vers le sombre en haut
    plain('comb-temp-light', emis=1., grain=0.)                                  # voyants jaunes
    lamp('comb-temp-glass'); lamp('comb-yell-light', core=.10)                      # lampes (verre lumineux, mode 2)
    (HERE / 'comb').mkdir(exist_ok=True)
    page = f'mv2:{FAMILY}:{GRAIN_TILE}:{MACRO_TILE}'
    (HERE / 'comb/materials.json').write_text(json.dumps(
        {'family': FAMILY, 'levels': list(LEVELS), 'albedo': albedo_list,
         'maps': [dict({k: v for k, v in t.items() if k != 'lamp'}, page=('mv2lamp' + page[3:]) if t.get('lamp') else page) for t in map_list],
         'world': [dict(t, page=page) for t in world_list]}, indent=1))
    print(len(albedo_list), 'couleurs,', len(map_list), 'cartes,', len(world_list), 'jeux du monde')


if __name__ == '__main__':
    main()
