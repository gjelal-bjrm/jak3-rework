"""Validate an explicit list of city Merc GLBs; --apply extracts into isolated staging only.

This never installs FR3 files, compiles GOAL, starts a game or edits live assets.
Python 3.11+ and Pillow are required. See MERC-PIPELINE.md for import limitations.
"""
from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / 'data'
CONTROL = 'cty-fruit-stand-lod0'
SOURCE = ROOT.parents[1] / f'active/jak3/data/decompiler_out/jak3/levels/wascityb/{CONTROL}.glb'
NATIVE_LEVELS = SOURCE.parents[1]
CITY_LEVELS = {'wascitya': 'WCA.DGO', 'wascityb': 'WCB.DGO', 'waswide': 'WWD.DGO'}
EXTRACTOR = ROOT.parents[1] / 'versions/official/v0.3.6/extractor.exe'
COMPARE_PYTHON = Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe')
DGOS = ['CGO/GAME.CGO', 'DGO/WASALL.DGO', 'DGO/WWD.DGO', 'DGO/WCA.DGO', 'DGO/WCB.DGO']
LEVELS = ['WCA.DGO', 'WCB.DGO']
IDENTITY = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def multiply(a, b):
    """Column-major matrices, as used in GLTF and the native importer."""
    return [sum(a[k * 4 + row] * b[col * 4 + k] for k in range(4))
            for col in range(4) for row in range(4)]


def matrix(node):
    if 'matrix' in node:
        return node['matrix']
    x, y, z, w = node.get('rotation', [0., 0., 0., 1.])
    sx, sy, sz = node.get('scale', [1., 1., 1.])
    tx, ty, tz = node.get('translation', [0., 0., 0.])
    return [(1-2*y*y-2*z*z)*sx, (2*x*y+2*w*z)*sx, (2*x*z-2*w*y)*sx, 0.,
            (2*x*y-2*w*z)*sy, (1-2*x*x-2*z*z)*sy, (2*y*z+2*w*x)*sy, 0.,
            (2*x*z+2*w*y)*sz, (2*y*z-2*w*x)*sz, (1-2*x*x-2*y*y)*sz, 0.,
            tx, ty, tz, 1.]


class Glb:
    def __init__(self, path, fallback_rig=None):
        self.path = path
        self.fallback_rig = fallback_rig
        raw = path.read_bytes()
        magic, version, length = struct.unpack_from('<4sII', raw)
        require(magic == b'glTF' and version == 2 and length == len(raw), 'Invalid GLB header')
        chunks = {}
        offset = 12
        while offset < length:
            size, kind = struct.unpack_from('<II', raw, offset)
            offset += 8
            require(offset + size <= length and kind not in chunks, 'Invalid/duplicate GLB chunk')
            chunks[kind] = raw[offset:offset + size]
            offset += size
        self.g = json.loads(chunks[0x4e4f534a])
        self.bin = chunks[0x004e4942]
        require(len(self.g['buffers']) == 1 and 'uri' not in self.g['buffers'][0],
                'Only one embedded binary buffer is supported')
        require(not self.g.get('extensionsRequired'), 'Required GLTF extensions are unsupported')
        self.world = {}
        require(len(self.g['scenes']) == 1, 'Only one scene: importer visits every scene')

        def visit(index, parent):
            require(index not in self.world, 'Repeated/cyclic scene node')
            node = self.g['nodes'][index]
            world = multiply(parent, matrix(node))
            require(all(math.isfinite(v) for v in world), 'Non-finite node transform')
            self.world[index] = world
            for child in node.get('children', []):
                visit(child, world)

        for index in self.g['scenes'][0]['nodes']:
            visit(index, IDENTITY)

    def values(self, index):
        a = self.g['accessors'][index]
        require('sparse' not in a and 'bufferView' in a, 'Sparse/unbuffered accessors unsupported')
        v = self.g['bufferViews'][a['bufferView']]
        require(v['buffer'] == 0, 'Unexpected external buffer')
        components = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[a['type']]
        code = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[a['componentType']]
        fmt = '<' + code * components
        size = struct.calcsize(fmt)
        stride = v.get('byteStride', size)
        offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        end = offset + (a['count'] - 1) * stride + size
        require(stride >= size and end <= v.get('byteOffset', 0) + v['byteLength']
                and end <= len(self.bin), 'Accessor exceeds its buffer view')
        return [struct.unpack_from(fmt, self.bin, offset + i * stride) for i in range(a['count'])]

    def image_bytes(self, index):
        image = self.g['images'][index]
        if 'bufferView' in image:
            v = self.g['bufferViews'][image['bufferView']]
            require(v['buffer'] == 0, 'Unexpected image buffer')
            offset = v.get('byteOffset', 0)
            return self.bin[offset:offset + v['byteLength']]
        uri = image.get('uri', '')
        require(uri.startswith('data:image/png;base64,'), 'Images must be embedded PNGs')
        return base64.b64decode(uri.split(',', 1)[1], validate=True)

    def rig(self):
        if not self.g.get('skins'):
            require(self.fallback_rig is not None, 'Native GLB has no skin and no verified shared rig')
            return self.fallback_rig
        require(len(self.g['skins']) == 1, 'Keep the single native skin')
        skin = self.g['skins'][0]
        names = [self.g['nodes'][n]['name'] for n in skin['joints']]
        bind = self.values(skin['inverseBindMatrices'])
        return {'joints': names, 'inverse_bind_matrices': bind,
                'joint_world_matrices': [self.world[n] for n in skin['joints']]}

    def inspect(self):
        g = self.g
        nodes = [(i, g['nodes'][i]) for i in self.world if 'mesh' in g['nodes'][i]]
        require(len(nodes) == 1, 'Join the stand into one mesh node before export')
        node_id, node = nodes[0]
        require(node.get('skin') == 0 or (not g.get('skins') and self.fallback_rig is not None),
                'Mesh must retain native skin 0')
        require(max(abs(a-b) for a, b in zip(self.world[node_id], IDENTITY)) < 0.0001,
                'Apply mesh transforms: the stand must retain its native pivot/orientation')
        extras = node.get('extras', {})
        require(not any(extras.get(k) for k in ('set_invisible', 'copy_eye_draws', 'copy_mod_draws')),
                'Unexpected visibility/eye/mod Merc extras')
        require(extras.get('enable_custom_weights', 0) in (0, 1), 'Invalid custom weight flag')
        rig = self.rig()
        positions = []
        weights_used = Counter()
        materials = []
        primitives = g['meshes'][node['mesh']]['primitives']
        require(len({p['material'] for p in primitives}) == len(primitives),
                'Each material must occur once: importer overwrites repeated-material draw ranges')
        triangles = 0
        for p in primitives:
            require(p.get('mode', 4) == 4 and 'indices' in p, 'Only indexed triangles are supported')
            require(not p.get('targets'), 'Morph targets are ignored by this importer')
            attrs = p['attributes']
            expected = {'POSITION': ('VEC3', 5126), 'NORMAL': ('VEC3', 5126),
                        'TEXCOORD_0': ('VEC2', 5126), 'JOINTS_0': ('VEC4', 5121),
                        'WEIGHTS_0': ('VEC4', 5126)}
            for name, signature in expected.items():
                a = g['accessors'][attrs[name]]
                require((a['type'], a['componentType']) == signature,
                        f'{name} must have native-supported format {signature}')
            color = g['accessors'][attrs['COLOR_0']]
            require((color['type'] == 'VEC4' and color['componentType'] in (5121, 5123, 5126))
                    or (color['type'] == 'VEC3' and color['componentType'] == 5126),
                    'Unsupported COLOR_0 format')
            values = {name: self.values(index) for name, index in attrs.items()}
            count = len(values['POSITION'])
            require(all(len(v) == count for v in values.values()), 'Attribute vertex counts differ')
            require(all(math.isfinite(x) for v in values.values() for row in v for x in row),
                    'Non-finite vertex data')
            indices = [v[0] for v in self.values(p['indices'])]
            require(len(indices) % 3 == 0 and min(indices) >= 0 and max(indices) < count,
                    'Invalid triangle indices')
            triangles += len(indices) // 3
            # Native GLBs share an accessor across multiple Merc controls: measure only drawn vertices.
            for index in sorted(set(indices)):
                positions.append(values['POSITION'][index])
                joint = values['JOINTS_0'][index]
                weight = values['WEIGHTS_0'][index]
                require(min(weight) >= 0 and abs(sum(weight) - 1.) < .001, 'Invalid skin weights')
                require(sum(sorted(weight)[1:]) > .0001, 'Three retained weights have zero sum')
                require(all(j < len(rig['joints']) for j in joint), 'Joint index outside skin')
                for j, w in zip(joint, weight):
                    if w > .0001:
                        weights_used[rig['joints'][j]] += 1
            mat = g['materials'][p['material']]
            mode = mat.get('alphaMode', 'OPAQUE')
            require(mode in ('OPAQUE', 'MASK'), 'Wooden stand must depth-write; BLEND is unsuitable')
            require(not ('KHR_materials_specular' in mat.get('extensions', {})
                         and mat['pbrMetallicRoughness'].get('metallicRoughnessTexture')),
                    'Native envmap texture path is not part of this import')
            tex = g['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]
            sampler = g['samplers'][tex['sampler']]
            require(all(sampler.get(k, 10497) in (10497, 33071) for k in ('wrapS', 'wrapT')),
                    'Mirrored texture wrapping is unsupported by the Merc importer')
            mag, minimum = sampler.get('magFilter', -1), sampler.get('minFilter', -1)
            require((mag == 9728 and minimum == 9984) or (mag != 9728 and minimum != 9728),
                    'Unsupported nearest texture sampler combination')
            raw = self.image_bytes(tex['source'])
            image = Image.open(io.BytesIO(raw))
            image.load()
            require(image.format == 'PNG' and raw[24] == 8 and image.mode in ('RGB', 'RGBA'),
                    'Use embedded 8-bit RGB/RGBA PNG')
            # TinyGLTF preserve_image_channels defaults false: RGB expands to RGBA255.
            image = image.convert('RGBA')
            require(max(image.size) <= 4096, 'Texture exceeds the bounded stand budget')
            lo, hi = image.getchannel('A').getextrema()
            if mode == 'MASK':
                require(hi / 2 >= mat.get('alphaCutoff', .5) * 127,
                        'Alpha test would discard the entire material')
            materials.append({'name': mat.get('name'), 'alpha_mode': mode,
                              'image_size': list(image.size), 'alpha_range': [lo, hi],
                              'native_alpha_range_after_shift': [lo >> 1, hi >> 1],
                              'image_sha256': hashlib.sha256(raw).hexdigest(),
                              'ignored_pbr_extensions': list(mat.get('extensions', {})),
                              'base_color_factor_ignored_by_importer':
                                  mat['pbrMetallicRoughness'].get('baseColorFactor', [1, 1, 1, 1])})
        require(triangles <= 15000, 'Stand exceeds 15,000-triangle first-pass budget')
        return {'node': node['name'], 'rig': rig, 'triangles': triangles,
                'drawn_vertex_samples': len(positions), 'weighted_joint_counts': dict(weights_used),
                'bounds_metres_y_up': [[min(p[i] for p in positions) for i in range(3)],
                                      [max(p[i] for p in positions) for i in range(3)]],
                'materials': materials, 'primitive_count': len(primitives),
                'custom_weights': bool(extras.get('enable_custom_weights', 0))}


def validate_model(authored):
    sources = [NATIVE_LEVELS/level/authored.name for level in CITY_LEVELS
               if (NATIVE_LEVELS/level/authored.name).is_file()]
    require(sources, f'No native city Merc control matches {authored.name}')
    source = sources[0]
    fallback_rig = None
    rig_reference = None
    if authored.stem == 'wascity-awning-b-lod1':
        # waswide-obs.gc defskelgroup uses lod0-jg for BOTH Merc LOD controls.
        # The exported native lod1 has weights but omits the skin object.
        reference = source.with_name('wascity-awning-b-lod0.glb')
        fallback_rig = Glb(reference).rig()
        rig_reference = {'path': str(reference), 'sha256': sha(reference),
            'reason': 'Native defskelgroup skel-wascity-awning-b uses lod0-jg for both LODs (waswide-obs.gc:723-724)',
            'native_lod1_weighted_matrices': [3,4,5,6,7]}
    original = Glb(source, fallback_rig).inspect()
    shared_sources = []
    for other in sources[1:]:
        shared = Glb(other, fallback_rig).inspect()
        require(shared['rig']['joints'] == original['rig']['joints']
                and shared['triangles'] == original['triangles'],
                f'Shared control differs between source levels: {authored.stem}')
        for key in ('inverse_bind_matrices', 'joint_world_matrices'):
            require(max(abs(a-b) for aa,bb in zip(shared['rig'][key], original['rig'][key])
                        for a,b in zip(aa,bb)) < .0001,
                    f'Shared control skeleton differs in {other.parent.name}: {authored.stem}')
        require(max(abs(a-b) for aa,bb in zip(shared['bounds_metres_y_up'], original['bounds_metres_y_up'])
                    for a,b in zip(aa,bb)) < .0001,
                f'Shared control footprint differs in {other.parent.name}: {authored.stem}')
        shared_sources.append({'path': str(other), 'sha256': sha(other)})
    current = Glb(authored).inspect()
    require(current['rig']['joints'] == original['rig']['joints'], 'Native skin joint order changed')
    for key in ('inverse_bind_matrices', 'joint_world_matrices'):
        error = max(abs(a-b) for aa, bb in zip(current['rig'][key], original['rig'][key])
                    for a, b in zip(aa, bb))
        require(error < .0001, f'Native skeleton {key} changed (max error {error})')
    require(current['weighted_joint_counts'].keys() == original['weighted_joint_counts'].keys(),
            'Different joints influence the rebuilt stand')
    for axis in range(3):
        bounds = original['bounds_metres_y_up']
        lo, hi = bounds[0][axis], bounds[1][axis]
        margin = max(.5, (hi-lo) * .2)
        a, b = (current['bounds_metres_y_up'][i][axis] for i in (0, 1))
        require(a >= lo-margin and b <= hi+margin and b-a >= (hi-lo)*.7,
                f'Authored axis {axis} bounds changed too much: check metre scale/native pivot')
    return {'control': authored.stem,
            'source': {'path': str(source), 'sha256': sha(source), **original},
            'authored': {'path': str(authored), 'sha256': sha(authored), **current},
            'source_levels': [p.parent.name for p in sources],
            'shared_source_compatibility_checked': shared_sources,
            'shared_lod_rig_reference': rig_reference,
            'weights_policy': ('Authored weights with proven native skin order/matrices' if current['custom_weights']
                               else 'Nearest native vertex weights; authored native rig retained and validated'),
            'native_unit_scale': 4096,
            'animations': 'Original DGO control/idle retained; GLB animations are not imported',
            'native_visual_validation': False}


def protected_paths():
    paths = set()
    # The same extracted city can be deployed under ROOT and retained under DATA.
    for project in (ROOT, DATA):
        for relative in ('out/jak3/fr3/waspala.fr3', 'out/jak3/fr3/wascitya.fr3',
                         'out/jak3/fr3/wascityb.fr3', 'out/jak3/fr3/waswide.fr3',
                         'out/jak3/fr3/game.fr3', 'out/jak3/iso/WASPALA.DGO',
                         'out/jak3/iso/GAME.CGO', 'out/jak3/iso/WCA.DGO',
                         'out/jak3/iso/WCB.DGO', 'out/jak3/iso/WWD.DGO'):
            path = project / relative
            if path.is_file():
                paths.add(path)
        directory = project / 'game/graphics/opengl_renderer/shaders'
        if directory.exists():
            paths.update(p for p in directory.rglob('*') if p.is_file())
    paths.update(DATA/'iso_data/jak3'/relative for relative in DGOS)
    metadata = DATA/'iso_data/jak3/buildinfo.json'
    if metadata.is_file():
        paths.add(metadata)
    return sorted(paths)


def prepare_staging(stage, authored_models, levels):
    require(stage.parent == (HERE / 'staging').resolve(), 'Staging must be directly under city-remaster/staging')
    require(not stage.exists(), 'Staging already exists: use a new run name; never overwrite a prior run')
    stage.mkdir(parents=True)
    project = stage / 'project'
    shutil.copytree(DATA / 'decompiler/config', project / 'decompiler/config')
    inputs = {'dgo_names': DGOS, 'object_file_names': [], 'str_file_names': [],
              'str_texture_file_names': [], 'str_art_file_names': [],
              'streamed_audio_file_names': [], 'levels_to_extract': levels}
    write_json(project / 'decompiler/config/market-inputs.json', inputs)
    copied = {}
    # Copy, never hardlink: the texture extractor may alter destination files.
    for relative in ('custom_assets/jak3/texture_replacements',
                     'custom_assets/jak3/merc_replacements', 'game/assets/jak3/texture_merges'):
        source = DATA / relative
        if source.exists():
            shutil.copytree(source, project / relative)
            for path in sorted(source.rglob('*')):
                if path.is_file():
                    copied[str(path.relative_to(DATA))] = sha(path)
    for authored in authored_models:
        destination = project / 'custom_assets/jak3/merc_replacements' / authored.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            backup = stage / 'backup/previous-merc-replacement' / authored.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
        shutil.copy2(authored, destination)
    config = {'inputs_file': 'decompiler/config/market-inputs.json', 'dgo_names': DGOS,
              'process_game_text': False, 'process_game_count': False,
              'process_part_group_table': False, 'dump_objs': False,
              'levels_extract': True, 'rip_levels': False, 'extract_collision': True,
              'rip_collision': False, 'save_texture_pngs': False, 'rip_streamed_audio': False,
              'decompile_code': False}
    write_json(stage / 'config-override.json', config)
    command = [str(EXTRACTOR), str(DATA / 'iso_data/jak3'), '--game', 'jak3',
               '--proj-path', str(project), '--folder', '--decompile',
               '--decomp-config-override', json.dumps(config, separators=(',', ':'))]
    return project, command, copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, action='append',
                        help='Explicit authored GLB; repeat for several controls (default: first stand)')
    parser.add_argument('--apply', action='store_true', help='Extract into NEW isolated staging, never deploy')
    parser.add_argument('--stage-name', default=None, help='Optional new directory name under city-remaster/staging')
    args = parser.parse_args()
    authored_models = [p.resolve() for p in (args.model or [HERE / (CONTROL + '.glb')])]
    report = {'mode': 'isolated-staging-extraction' if args.apply else 'validation-only',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'deployed': False,
              'compiled_or_launched': False, 'errors': []}
    report_path = HERE / 'market-import-validation.json'
    try:
        require(len({p.name for p in authored_models}) == len(authored_models), 'Duplicate Merc control filename')
        report['models'] = [validate_model(p) for p in authored_models]
        targets = sorted({level for m in report['models'] for level in m['source_levels']})
        levels = [CITY_LEVELS[level] for level in targets]
        require(EXTRACTOR.is_file(), f'Missing official extractor: {EXTRACTOR}')
        for relative in DGOS:
            require((DATA / 'iso_data/jak3' / relative).is_file(), f'Missing ISO input {relative}')
        report['extraction_plan'] = {
            'extractor': str(EXTRACTOR), 'extractor_sha256': sha(EXTRACTOR),
            'input_dgos': DGOS, 'levels_to_extract': levels,
            'candidate_allowlist': [level+'.fr3' for level in targets],
            'never_deploy_generated': ['GAME.fr3'],
            'palace_preservation': 'WASPALA excluded; live and DATA palace remain hash-protected',
            'later_palace_reapplication': 'Only if palace is deliberately re-extracted: models-v1/apply_models.py with explicit clean source and destination; not run here',
            'city_terrain_preservation': 'Keep complete current level; append selected GLB draw payloads with explicit texture/vertex/index remapping, then prove all existing textures/static/unrelated Merc data unchanged and selected payloads match extraction',
            'safety': 'No copying to ROOT/out, DATA/out, variants, profiles or live shader directories'}
        if args.apply:
            require(COMPARE_PYTHON.is_file(), 'Blender Python with zstandard required for full FR3 comparison')
            name = args.stage_name or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            require(name not in ('', '.', '..') and Path(name).name == name
                    and '/' not in name and '\\' not in name, 'Invalid stage name')
            stage = (HERE / 'staging' / name).resolve()
            paths = protected_paths()
            before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
            project, command, copied = prepare_staging(stage, authored_models, levels)
            report['staging'] = str(stage)
            report_path = stage / 'import-report.json'
            # Reversible snapshot of original city candidates, plus all protected hashes.
            for prefix in ('', 'data/'):
                for level in targets:
                    relative = prefix + f'out/jak3/fr3/{level}.fr3'
                    source = ROOT / relative
                    if source.exists():
                        backup = stage / 'backup' / relative
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, backup)
                        require(sha(backup) == before[relative], 'City backup hash mismatch')
            write_json(stage / 'protected-before.json', before)
            write_json(stage / 'copied-input-hashes.json', copied)
            write_json(stage / 'command.json', command)
            report['command'] = command
            write_json(report_path, report)
            print(f'Extracting only {levels} into {project}; game stays untouched', flush=True)
            try:
                with (stage / 'extractor.log').open('w', encoding='utf-8') as log:
                    result = subprocess.run(command, cwd=project, stdout=log, stderr=subprocess.STDOUT)
                report['extractor_exit_code'] = result.returncode
                require(result.returncode == 0, f'Extractor failed ({result.returncode}); see extractor.log')
                output = project / 'out/jak3/fr3'
                candidates = {}
                for filename in (level+'.fr3' for level in targets):
                    path = output / filename
                    require(path.is_file() and path.stat().st_size > 10000, f'Missing candidate {filename}')
                    candidates[filename] = {'path': str(path), 'sha256': sha(path),
                                            'bytes': path.stat().st_size}
                log_text = (stage / 'extractor.log').read_text(encoding='utf-8', errors='replace')
                for model in report['models']:
                    for level in model['source_levels']:
                        require(f'Replacing {model["control"]} for {level}:' in log_text,
                                f'No native replacement confirmation for {model["control"]} in {level}')
                require(not (output / 'waspala.fr3').exists(), 'Unexpected palace output')
                require({p.name.lower() for p in output.glob('*.fr3')} <=
                        {level+'.fr3' for level in targets} | {'game.fr3'}, 'Unexpected extracted level')
                for model in report['models']:
                    require(sha(model['authored']['path']) == model['authored']['sha256'],
                            'Author GLB changed during extraction; rerun against a stable export')
                report['raw_extracted_candidates'] = candidates
                report['extractor_messages'] = [line for line in log_text.splitlines()
                                                 if '[warn]' in line or '[error]' in line]
                ready = stage/'candidates'
                ready.mkdir()
                preserved = {}
                for level in targets:
                    current = DATA/f'out/jak3/fr3/{level}.fr3'
                    source = output/(level+'.fr3')
                    destination = ready/(level+'.fr3')
                    comparison_path = stage/(level+'-preservation.json')
                    controls = [m['control'] for m in report['models'] if level in m['source_levels']]
                    comparison_command = [str(COMPARE_PYTHON), str(HERE/'compare_market.py'),
                        '--current', str(current), '--candidate', str(source),
                        '--preserve-static', str(destination), '--report', str(comparison_path),
                        '--controls', *controls]
                    with (stage/(level+'-comparison.log')).open('w', encoding='utf-8') as log:
                        comparison = subprocess.run(comparison_command, cwd=HERE, stdout=log,
                                                    stderr=subprocess.STDOUT)
                    require(comparison.returncode == 0,
                            f'Preservation check failed for {level}; see {level}-comparison.log; no deploy')
                    preserved[level+'.fr3'] = {'path': str(destination), 'sha256': sha(destination),
                        'bytes': destination.stat().st_size, 'base_sha256': sha(current),
                        'preservation_report': str(comparison_path)}
                report['candidates'] = preserved
                report['merc_replacement_confirmed_by_extractor'] = True
                report['native_visual_validation'] = False
            finally:
                after = {p.relative_to(ROOT).as_posix(): sha(p) if p.exists() else None for p in paths}
                report['protected_hashes_unchanged'] = before == after
                report['changed_protected_files'] = [p for p, digest in before.items() if after[p] != digest]
                write_json(stage / 'protected-after.json', after)
                require(before == after, 'Protected files changed during staging; do not deploy')
        report['status'] = 'passed'
    except (ValueError, KeyError, OSError, struct.error) as error:
        report['errors'].append(str(error))
        report['status'] = 'failed'
    write_json(report_path, report)
    print(json.dumps({'status': report['status'], 'mode': report['mode'], 'report': str(report_path),
                      'errors': report['errors'], 'deployed': False}, ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
