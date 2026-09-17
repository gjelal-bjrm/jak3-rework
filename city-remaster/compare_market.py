"""Read-only FR3 v43 preservation check, using Blender's Python with zstandard.

Texture bytes and the entire serialized static region are compared, not just a
visible block. Merc parsing follows Tfrag3Data.cpp and must consume the exact EOF.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import zstandard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONTROL = 'cty-fruit-stand-lod0'
NATIVE = ROOT.parents[1] / 'active/jak3/data/decompiler_out/jak3/levels/wascityb'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Reader:
    def __init__(self, data, offset=0):
        self.data, self.offset = data, offset

    def raw(self, count):
        assert 0 <= count <= len(self.data) - self.offset
        result = self.data[self.offset:self.offset+count]
        self.offset += count
        return result

    def value(self, fmt):
        return struct.unpack('<'+fmt, self.raw(struct.calcsize('<'+fmt)))[0]

    def count(self):
        n = self.value('Q')
        assert n < 100000000
        return n

    def string(self):
        return self.raw(self.count()).decode('utf-8')

    def vector(self, element_size):
        return self.raw(self.count()*element_size)


def model(r):
    start = r.offset
    name = r.string()
    all_draws = []
    draw_offsets = []
    effect_flags = []
    for _ in range(r.count()):
        for _ in range(r.count()):
            draw_offsets.append(r.offset-start)
            values = struct.unpack('<IiBIIIB', r.raw(22))
            all_draws.append(dict(zip(('mode','texture','eye','first_index','index_count',
                                      'triangles','no_strip'), values)))
        # MercModifiableDrawGroup: mod draws, fixed draws, then vertex buffers.
        r.raw(r.count()*22)
        r.raw(r.count()*22)
        r.vector(64)
        r.vector(2)
        r.vector(1)
        r.raw(4)
        r.vector(32)  # Blerc float_data
        r.vector(4)   # Blerc int_data
        flags = r.raw(10)     # envmap mode/texture and two bools
        effect_flags.append({'envmap': bool(flags[8]), 'mod_draw': bool(flags[9])})
    parameter_offset = r.offset+8
    scalars = struct.unpack('<IIIff', r.raw(20))
    return {'name': name, 'bytes_sha256': digest(r.data[start:r.offset]),
            'draws': all_draws, 'max_draws': scalars[0], 'max_bones': scalars[1],
            'effect_flags': effect_flags,
            'native_runtime_parameters_hex': r.data[parameter_offset:parameter_offset+12].hex(),
            '_layout': {'start': start, 'end': r.offset,
                        'parameter_offset': parameter_offset-start, 'draw_offsets': draw_offsets}}


def read_level(path):
    compressed = path.read_bytes()
    size = struct.unpack_from('<Q', compressed)[0]
    data = zstandard.ZstdDecompressor().decompress(compressed[8:], max_output_size=size)
    assert len(data) == size
    r = Reader(data)
    assert r.value('H') == 43
    name = r.string()
    textures = []
    texture_count_offset = r.offset
    texture_bytes = []
    for _ in range(r.count()):
        start = r.offset
        width, height, combo = struct.unpack('<HHI', r.raw(8))
        pixels = r.vector(4)
        tex_name, page = r.string(), r.string()
        pool = r.value('B')
        assert len(pixels) == width*height*4
        textures.append({'name': tex_name, 'page': page, 'combo': combo,
                         'width': width, 'height': height, 'pool': pool,
                         'rgba_sha256': digest(pixels),
                         'serialized_sha256': digest(data[start:r.offset])})
        texture_bytes.append(data[start:r.offset])
    static_start = r.offset
    # Find the first exported Merc control, then prove the proposed boundary by
    # fully parsing MercModelGroup, its buffers and the terminal v43 field.
    occurrences = []
    for glb in (NATIVE.parent/name).glob('*.glb'):
        control = glb.stem.encode('utf-8')
        offset = data.find(struct.pack('<Q', len(control))+control, static_start)
        if offset >= 0:
            occurrences.append(offset)
    assert occurrences, 'No native Merc boundary found'
    merc_start = min(occurrences)-8
    r.offset = merc_start
    models = [model(r) for _ in range(r.count())]
    model_layouts = {m['name']: m.pop('_layout') for m in models}
    assert len({m['name'] for m in models}) == len(models)
    indices = r.vector(4)
    vertices = r.vector(64)
    assert r.value('H') == 43 and r.offset == len(data), 'Merc boundary did not consume exact EOF'
    return {'path': str(path), 'sha256': digest(compressed), 'level': name,
            'textures': textures, 'models': models,
            'model_layouts': model_layouts, 'texture_bytes': texture_bytes,
            'texture_count_offset': texture_count_offset,
            'data': data, 'static_start': static_start, 'merc_start': merc_start,
            # Includes index textures, all TFRAG/TIE/SHRUB LODs, wind, hfrag and collision.
            'static_bytes': data[static_start:merc_start],
            'merc_indices': indices, 'merc_vertices': vertices}


def merge_selected(current, extracted, selected, destination):
    """Append only selected draw payloads to the complete current native level.

Extraction inserts Merc texture/vertex buffers midway through other art groups.
Their offsets therefore cannot be trusted as replacements for the live level.
Keep all live records and indices, remap selected extracted draws to appended
buffers, and append only their referenced textures. No static re-extraction data
is used in the output, including the rebuilt texture order.
"""
    old = {m['name']: m for m in current['models']}
    new = {m['name']: m for m in extracted['models']}
    assert current['level'] == extracted['level'] and old.keys() == new.keys()
    assert all(not f['mod_draw'] and not f['envmap'] for n in selected
               for m in (old[n],new[n]) for f in m['effect_flags'])
    textures = list(current['texture_bytes'])
    texture_lookup = {digest(raw): i for i,raw in enumerate(textures)}
    tex_remap = {}
    indices = bytearray(current['merc_indices'])
    vertices = bytearray(current['merc_vertices'])
    records = []
    copied = []
    for original_model in current['models']:
        name = original_model['name']
        if name not in selected:
            layout = current['model_layouts'][name]
            records.append(current['data'][layout['start']:layout['end']])
            continue
        layout = extracted['model_layouts'][name]
        record = bytearray(extracted['data'][layout['start']:layout['end']])
        vertex_remap = {}
        for draw, offset in zip(new[name]['draws'], layout['draw_offsets']):
            assert draw['no_strip'] and draw['index_count'] == draw['triangles']*3
            texture_id = draw['texture']
            assert 0 <= texture_id < len(extracted['textures'])
            assert extracted['textures'][texture_id]['page'] == 'custom-level', \
                'Selected draw did not come from a Merc replacement GLB'
            if texture_id not in tex_remap:
                raw_texture = extracted['texture_bytes'][texture_id]
                key = digest(raw_texture)
                if key not in texture_lookup:
                    texture_lookup[key] = len(textures)
                    textures.append(raw_texture)
                tex_remap[texture_id] = texture_lookup[key]
            first = len(indices)//4
            begin = draw['first_index']*4
            raw_indices = extracted['merc_indices'][begin:begin+draw['index_count']*4]
            assert len(raw_indices) == draw['index_count']*4
            for (index,) in struct.iter_unpack('<I', raw_indices):
                assert index < len(extracted['merc_vertices'])//64
                if index not in vertex_remap:
                    raw_vertex = extracted['merc_vertices'][index*64:(index+1)*64]
                    # Each original control determines which matrices GOAL sends.
                    weights = struct.unpack_from('<3f', raw_vertex, 32)
                    mats = struct.unpack_from('<3B', raw_vertex, 60)
                    assert all(m <= old[name]['max_bones'] for m,w in zip(mats,weights) if w > .0001), \
                        f'{name}: replacement references a matrix absent from the native control'
                    vertex_remap[index] = len(vertices)//64
                    vertices.extend(raw_vertex)
                indices.extend(struct.pack('<I',vertex_remap[index]))
            struct.pack_into('<i', record, offset+4, tex_remap[texture_id])
            struct.pack_into('<I', record, offset+9, first)
        p = layout['parameter_offset']
        record[p:p+12] = bytes.fromhex(old[name]['native_runtime_parameters_hex'])
        records.append(record)
        copied.append({'control': name, 'vertices': len(vertex_remap),
                       'triangles': sum(d['triangles'] for d in new[name]['draws'])})
    raw = (current['data'][:current['texture_count_offset']] + struct.pack('<Q',len(textures))
           + b''.join(textures) + current['static_bytes'] + struct.pack('<Q',len(records))
           + b''.join(records) + struct.pack('<Q',len(indices)//4) + indices
           + struct.pack('<Q',len(vertices)//64) + vertices + struct.pack('<H',43))
    destination.write_bytes(struct.pack('<Q',len(raw))+zstandard.ZstdCompressor(level=1).compress(raw))
    return {'extracted_candidate_sha256': extracted['sha256'],
            'raw_extraction_static_identical': current['static_bytes'] == extracted['static_bytes'],
            'preserved_current_static_bytes': len(current['static_bytes']),
            'native_merc_runtime_parameters_preserved': sorted(selected),
            'method': 'Copy current level; append selected GLB draw payloads with explicit vertex/index/texture remapping',
            'selected_payloads': copied,
            'texture_remap': {str(k):v for k,v in tex_remap.items()}}


def selected_payloads(level, selected):
    """Hash the actual ordered vertices drawn, independent of storage offsets."""
    result = {}
    for model in level['models']:
        if model['name'] not in selected:
            continue
        draws = []
        for draw in model['draws']:
            h = hashlib.sha256()
            start = draw['first_index']*4
            raw_indices = level['merc_indices'][start:start+draw['index_count']*4]
            for (index,) in struct.iter_unpack('<I',raw_indices):
                if index == 0xffffffff:
                    h.update(b'STRIP_BREAK')
                else:
                    h.update(level['merc_vertices'][index*64:(index+1)*64])
            draws.append({k:draw[k] for k in ('mode','eye','index_count','triangles','no_strip')} | {
                'ordered_vertex_payload_sha256': h.hexdigest(),
                'texture_sha256': level['textures'][draw['texture']]['serialized_sha256']})
        result[model['name']] = draws
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current', type=Path, default=ROOT/'data/out/jak3/fr3/wascityb.fr3')
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--controls', nargs='+', default=[CONTROL],
                        help='Exact allowed Merc controls; only controls present in this level must change')
    parser.add_argument('--preserve-static', type=Path,
                        help='Write a NEW staging FR3 with exact current static bytes; never overwrite either input')
    args = parser.parse_args()
    current = read_level(args.current.resolve())
    candidate = read_level(args.candidate.resolve())
    selected = set(args.controls) & {m['name'] for m in current['models']}
    assert selected, 'No selected control exists in current level'
    preservation = None
    imported_payloads = None
    if args.preserve_static:
        destination = args.preserve_static.resolve()
        assert destination.is_relative_to(HERE/'staging'), 'Output must remain in city staging'
        assert not destination.exists(), 'Refusing to overwrite an existing output'
        assert destination not in (args.current.resolve(), args.candidate.resolve())
        imported_payloads = selected_payloads(candidate, selected)
        preservation = merge_selected(current, candidate, selected, destination)
        candidate = read_level(destination)
    checks = {}
    checks['same_level'] = (current['level'] == candidate['level']
                            and current['level'] in ('wascitya', 'wascityb', 'waswide'))
    old_textures = current['textures']
    new_textures = candidate['textures']
    checks['all_existing_textures_same_order_dimensions_rgba_and_flags'] = (
        old_textures == new_textures[:len(old_textures)])
    raw_static_identical = current['static_bytes'] == candidate['static_bytes']
    checks['entire_static_region_including_collision_bit_identical'] = raw_static_identical
    old_models = {m['name']: m for m in current['models']}
    new_models = {m['name']: m for m in candidate['models']}
    selected = set(args.controls) & old_models.keys()
    assert selected, 'No selected control exists in current level'
    checks['same_merc_control_set'] = old_models.keys() == new_models.keys()
    changed_models = [n for n in old_models if old_models[n] != new_models.get(n)]
    checks['only_selected_merc_models_changed'] = set(changed_models) == selected
    checks['selected_models_have_no_unhandled_mod_draws_or_envmaps'] = all(
        not f['mod_draw'] and not f['envmap'] for n in selected for f in old_models[n]['effect_flags'])
    appended_ids = set(range(len(old_textures), len(new_textures)))
    used_added = {d['texture'] for n in selected for d in new_models[n]['draws']
                  if d['texture'] >= len(old_textures)}
    # A later geometry pass can reuse every HD image from the previous install.
    # An empty append set is valid: unchanged pixels and the exact referenced
    # texture payload are verified separately, as are all selected vertices.
    checks['appended_textures_only_used_by_selected_models'] = (used_added == appended_ids
        and all(d['texture'] not in appended_ids
            for n,m in new_models.items() if n not in selected for d in m['draws']))
    checks['existing_merc_index_buffer_identical'] = candidate['merc_indices'].startswith(current['merc_indices'])
    checks['existing_merc_vertex_buffer_identical'] = candidate['merc_vertices'].startswith(current['merc_vertices'])
    checks['selected_models_keep_native_runtime_parameters'] = all(
        old_models[n]['native_runtime_parameters_hex'] == new_models[n]['native_runtime_parameters_hex'] for n in selected)
    if imported_payloads is not None:
        checks['selected_draw_payloads_match_extraction'] = selected_payloads(candidate,selected) == imported_payloads
    result = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
              'current': {'path': current['path'], 'sha256': current['sha256']},
              'candidate': {'path': candidate['path'], 'sha256': candidate['sha256']},
              'existing_texture_count': len(old_textures),
              'new_textures': new_textures[len(old_textures):],
              'changed_merc_models': changed_models,
              'selected_models_before': [old_models[n] for n in sorted(selected)],
              'selected_models_after': [new_models[n] for n in sorted(selected)],
              'unchanged_static_bytes': len(current['static_bytes']),
              'current_static_sha256': digest(current['static_bytes']),
              'candidate_static_sha256': digest(candidate['static_bytes']),
              'static_preservation': preservation,
              'imported_draw_payloads': imported_payloads,
              'deployed': False}
    args.report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
