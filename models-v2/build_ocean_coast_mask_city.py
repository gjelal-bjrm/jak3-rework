"""Masque de cote de Haven (carte d'ocean *ocean-map-city*) pour le rendu moderne de la mer.

Meme principe que build_ocean_coast_mask.py (Spargus) : les tables natives ocean-trans-indices /
ocean-near-indices / ocean-mid-masks de la carte 'city' (engine/gfx/ocean/ocean-tables.gc) donnent, par
cellule de 3 m, si la mer native est dessinee (un bit de masque leve = sec). Origine : start-corner de
*ocean-map-city* (-864 m, -1728 m), niveau de la mer : y du start-corner (0 m).
Ecrit engine-src/.../ocean/OceanCoastMaskCity.h.
"""
from pathlib import Path
import hashlib, json, re

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'engine-src/goal_src/jak3/engine/gfx/ocean/ocean-tables.gc'
TARGET = ROOT / 'engine-src/game/graphics/opengl_renderer/ocean/OceanCoastMaskCity.h'
ORIGIN = (-3538944.0 / 4096, -7077888.0 / 4096)   # start-corner de *ocean-map-city*
LEVEL = 0.0


def form(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '(': depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise ValueError('forme non fermee')


def section(text, name):
    start = text.index(f'(define {name}')
    return form(text, start)


def forms(text, kind):
    return [form(text, m.start()) for m in re.finditer(r"\(new 'static '" + kind + r'(?=[\s)])', text)]


def number(value): return int(value[2:], 16) if value.startswith('#x') else int(value)


def array(item, kind, count):
    found = re.search(r"\(new 'static 'array " + kind + r' ' + str(count) + r'\s+([^)]*)\)', item)
    values = [number(v) for v in found[1].split()] if found else [0] * count
    assert len(values) == count
    return values


def main():
    text = SOURCE.read_text()
    trans = []
    for item in forms(section(text, '*ocean-trans-indices-city*'), 'ocean-trans-index'):
        fields = {k: number(v) for k, v in re.findall(r':(parent|child)\s+(#x[0-9a-f]+|-?\d+)', item)}
        trans.append((fields.get('parent', 0), fields.get('child', 0)))
    near = [array(i, 'uint16', 16) for i in forms(section(text, '*ocean-near-indices-city*'), 'ocean-near-index')]
    masks = [array(i, 'uint8', 8) for i in forms(section(text, '*ocean-mid-masks-city*'), 'ocean-mid-mask')]
    assert len(trans) == 2304, len(trans)
    print('Haven : transitions', len(trans), 'near', len(near), 'masques', len(masks))

    def wet(x, z):
        x -= ORIGIN[0]; z -= ORIGIN[1]
        if x < 0 or z < 0 or x >= 4608 or z >= 4608: return True
        ix, iz = int(x / 3), int(z / 3)
        parent, child = trans[(iz // 32) * 48 + ix // 32]
        if parent in (-1, 65535): return False
        if child >= len(near): return False
        m = near[child][((iz // 8) & 3) * 4 + ((ix // 8) & 3)]
        return m != 65535 and m < len(masks) and not (masks[m][iz & 7] & (1 << (ix & 7)))

    observations = [{'name': name, 'xz': [x, z], 'wet': wet(x, z)} for name, x, z in (
        ('quai du port, point de reprise ctyport-start', 193.0, 1754.0),
        ('bassin du port devant le quai', 150.0, 1700.0))]

    def emit(name, typ, rows):
        width = len(rows[0])
        return f'  inline static constexpr {typ} {name}[{len(rows)}][{width}] = {{\n' + ''.join('    {' + ','.join(str(v) for v in row) + '},\n' for row in rows) + '  };\n'
    header = f'''#pragma once
#include <cstdint>

// Genere par models-v2/build_ocean_coast_mask_city.py depuis *ocean-map-city* (ocean-tables.gc).
// Meme decodage que OceanCoastMask (Spargus) : 96 m -> 24 m -> 3 m ; un bit de masque leve = sec.
class OceanCoastMaskCity {{
 public:
  static constexpr int SIZE = 1536;
  static constexpr float ORIGIN_X = {ORIGIN[0]:.1f}f;
  static constexpr float ORIGIN_Z = {ORIGIN[1]:.1f}f;
  static constexpr float LEVEL = {LEVEL:.1f}f;
  static bool cell(int x, int z) {{
    if (x < 0 || z < 0 || x >= SIZE || z >= SIZE) return true;
    const auto* transition = transitions[(z / 32) * 48 + x / 32];
    if (transition[0] < 0) return false;
    if (transition[1] < 0 || transition[1] >= {len(near)}) return false;
    const auto mask = near_indices[transition[1]][((z / 8) & 3) * 4 + ((x / 8) & 3)];
    return mask != 65535 && mask < {len(masks)} && !(masks[mask][z & 7] & (1 << (x & 7)));
  }}
  static bool contains(float x, float z) {{
    x -= ORIGIN_X; z -= ORIGIN_Z;
    if (x < 0.f || z < 0.f || x >= SIZE * 3.f || z >= SIZE * 3.f) return true;
    return cell(int(x / 3.f), int(z / 3.f));
  }}
 private:
'''
    header += emit('transitions', 'int16_t', trans) + emit('near_indices', 'uint16_t', near) + emit('masks', 'uint8_t', masks) + '};\n'
    TARGET.write_text(header)
    report = {'source': str(SOURCE), 'header': str(TARGET), 'header_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
              'origin_xz': ORIGIN, 'level': LEVEL, 'observations': observations,
              'water_cells': sum(wet(ORIGIN[0] + x * 3 + 1.5, ORIGIN[1] + z * 3 + 1.5) for z in range(1536) for x in range(1536))}
    (ROOT / 'models-v2/ocean-coast-mask-city-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report['observations'], indent=1), 'cellules d eau :', report['water_cells'])


if __name__ == '__main__': main()
