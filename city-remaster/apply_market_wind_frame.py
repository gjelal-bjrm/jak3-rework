"""Bounded, reversible world-space lighting fix for dedicated market palm leaves.

This does not package, restart, or install a runtime. --undo refuses files changed
since this script's application, so later work cannot be silently overwritten.
"""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'city-remaster/wind-material-frame.json'
SHADER='game/graphics/opengl_renderer/shaders/tie_wind.vert'
BASE='engine-src/game/graphics/opengl_renderer/background/'
EDITS={
    BASE+'PalaceMaterials.h':[(
        '    const bool market_shrub=kind && m_names[texture]=="market-shrub-orange-v1";',
        '    const bool market_shrub=kind && m_names[texture]=="market-shrub-orange-v1";\n'
        '    const bool market_wind=kind && m_names[texture]=="market-palm-leaf-v1";\n'
        '    glUniform1i(glGetUniformLocation(program,"market_wind_material"),market_wind);'),(
        '    if (kind) glUniform3f(glGetUniformLocation(program,"palace_eye"),',
        '    // These private remaster textures use authored, repeating UVs. Native\n'
        '    // atlases and the leaf/shrub alpha textures keep their original wrap.\n'
        '    if (kind && (m_names[texture]=="market-palm-trunk-v1" ||\n'
        '                 m_names[texture]=="market-support-wood-v1" ||\n'
        '                 m_names[texture]=="market-support-metal-v1")) {\n'
        '      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_REPEAT);\n'
        '      glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_REPEAT);\n'
        '    }\n'
        '    if (kind) glUniform3f(glGetUniformLocation(program,"palace_eye"),')],
    BASE+'Tie3.h':[(
        '    std::vector<std::array<math::Vector4f, 4>> wind_matrix_cache;',
        '    std::vector<std::array<math::Vector4f, 4>> wind_matrix_cache;\n'
        '    // Native instance transform after wind, before camera composition.\n'
        '    std::vector<std::array<math::Vector4f, 4>> wind_world_matrix_cache;')],
    BASE+'Tie3.cpp':[(
        '        lod_tree[l_tree].wind_matrix_cache.resize(tree.wind_instance_info.size());',
        '        lod_tree[l_tree].wind_matrix_cache.resize(tree.wind_instance_info.size());\n'
        '        lod_tree[l_tree].wind_world_matrix_cache.resize(tree.wind_instance_info.size());'),(
        '                 info.stiffness * m_wind_multiplier, mat);',
        '                 info.stiffness * m_wind_multiplier, mat);\n'
        '    tree.wind_world_matrix_cache[inst_id] = mat;'),(
        '                         GL_FALSE, tree.wind_matrix_cache.at(grp.instance_idx)[0].data());',
        '                         GL_FALSE, tree.wind_matrix_cache.at(grp.instance_idx)[0].data());\n'
        '      glUniformMatrix4fv(\n'
        '          glGetUniformLocation(render_state->shaders[shader_id].id(), "market_wind_world"),\n'
        '          1, GL_FALSE, tree.wind_world_matrix_cache.at(grp.instance_idx)[0].data());')]
}
VERTEX_EDITS=[(
    'uniform mat4 camera;',
    'uniform mat4 camera;\n'
    'uniform bool market_wind_material;\n'
    'uniform mat4 market_wind_world;'),(
    '  arena_world = palace_position / 4096.0;',
    '  arena_world = palace_position / 4096.0;\n'
    '  // Wind geometry remains local for the native projection below. Only the\n'
    '  // dedicated market leaf material needs world-space shading attributes.\n'
    '  if (market_wind_material) {\n'
    '    arena_world = (market_wind_world * vec4(palace_position,1.0)).xyz / 4096.0;\n'
    '    mat3 worldNormal = transpose(inverse(mat3(market_wind_world)));\n'
    '    if (dot(palace_smooth_normal,palace_smooth_normal)>.000001)\n'
    '      palace_smooth_normal = normalize(worldNormal * palace_smooth_normal);\n'
    '  }')]
EDITS['engine-src/'+SHADER]=VERTEX_EDITS
EDITS['data/'+SHADER]=VERTEX_EDITS


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--undo',action='store_true')
    args=parser.parse_args()
    prior=json.loads(REPORT.read_text()) if REPORT.exists() else None
    staged=[]
    for relative,edits in EDITS.items():
        path=ROOT/relative
        raw=path.read_bytes()
        # Preserve the existing line endings; matching is deliberately exact.
        newline='\r\n' if b'\r\n' in raw else '\n'
        updated=raw
        if args.undo:
            assert prior and sha(raw)==prior['files'][relative]['after_sha256'],relative+' changed after application'
            edits=[(new,old)for old,new in reversed(edits)]
        elif prior:
            assert sha(raw)==prior['files'][relative]['after_sha256'],relative+' changed after application'
        for old,new in edits:
            old=old.replace('\n',newline).encode()
            new=new.replace('\n',newline).encode()
            if not args.undo and updated.count(new)==1:continue
            assert updated.count(old)==1,(relative,'anchor count',updated.count(old))
            updated=updated.replace(old,new,1)
        if args.undo:
            assert sha(updated)==prior['files'][relative]['before_sha256'],relative+' inverse mismatch'
        if updated!=raw:staged.append((path,raw,updated))
    if not args.undo and staged:
        manifest={'scope':'Dedicated market leaf world shading and trunk/support repeating UVs; native projection and wind preserved',
                  'native_visual_validation':False,'files':prior['files'] if prior else {}}
        for path,before,after in staged:
            key=path.relative_to(ROOT).as_posix()
            manifest['files'][key]={'before_sha256':manifest['files'].get(key,{}).get('before_sha256',sha(before)),
                                   'after_sha256':sha(after)}
        REPORT.write_text(json.dumps(manifest,indent=2)+'\n')
    for path,_,updated in staged:path.write_bytes(updated)
    print(('Undid 'if args.undo else 'Applied ')+str(len(staged))+' bounded file changes')


if __name__=='__main__':main()
