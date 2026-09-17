"""Bounded shared-apartment source, mesh, AO and actual GPU provenance."""
from pathlib import Path
import hashlib
import json
import math
import struct

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(directory,check,matches,motion=None):
    motion=motion or{}
    here=directory/'shared-room-v2';record_path=here/'provenance.json'
    if not record_path.exists():
        check('m_rooms'not in (directory/'CityInteriors.h').read_text(),
              'Shared room renderer has no final immutable source provenance')
        return {}
    record=load(record_path)
    before={'CityInteriors-before.h','city_interior-before.frag','source-manifest-before.json','asset-manifest-before.json'}
    after={'CityInteriors.h','city_interior.frag','room_config.py','prepare.py'}
    proofs={'author.py','author-report.json','corner-conversation.bin','corner-conversation.json',
            'no-ao/corner-conversation.bin','no-ao/corner-conversation.json',
            'ao/corner-conversation.bin','ao/corner-conversation.json','ao/bake-report.json',
            'qa_gpu_shared.py','qa/validation.json'}
    check(record['status']=='installed'and set(record)=={'status','before','after','proofs'}and
          set(record['before'])==before and set(record['after'])==after and set(record['proofs'])==proofs,
          'Shared apartment provenance broadens its exact source and proof inventory')
    for field,base in (('before',here),('after',directory),('proofs',here)):
        for relative,expected in record[field].items():matches(base/relative,expected)
    historical=load(here/'source-manifest-before.json');current=load(directory/'source-manifest.json')
    check(historical['files']==current['files'],
          'Shared apartment revision changes an unrelated OpenGLRenderer hook')
    render='engine-src/game/graphics/opengl_renderer/'
    matches(here/'CityInteriors-before.h',historical['new_files'][render+'CityInteriors.h'])
    for tree in ('engine-src','data'):
        matches(here/'city_interior-before.frag',historical['new_files'][tree+'/game/graphics/opengl_renderer/shaders/city_interior.frag'])
        check(historical['new_files'][tree+'/game/graphics/opengl_renderer/shaders/city_interior.vert']==
              current['new_files'][tree+'/game/graphics/opengl_renderer/shaders/city_interior.vert'],
              'Shared apartment revision changed its vertex shader')
    old=(here/'CityInteriors-before.h').read_text();new=(directory/'CityInteriors.h').read_text()
    for start,end in (('  GLint location(', '  void initialize('),('  void draw(', '  bool m_attempted=')):
        check(old[old.index(start):old.index(end)]==new[new.index(start):new.index(end)],
              'Shared apartment revision changed mesh loading, draw submission or GL state restoration')
    check(new.count('for(const auto& room:m_rooms)')==1 and
          new.count('for(const auto& actor:room.actors)')==1 and
          'const auto& anchor=m_windows[room.anchor]'in new and
          'room.origin=m_windows[room.anchor].origin'in new and
          'window belongs to two rooms'in new and 'window has no room'in new,
          'Shared apartment renderer no longer draws persistent occupants once per physical room')
    fragment=(directory/'city_interior.frag').read_text()
    inverse=[('uniform vec3 material_color,room_eye,room_fog,room_lamp;',
              'uniform vec3 material_color,room_eye,room_fog;'),
             ('uniform float roughness,room_occupancy,room_side_light;',
              'uniform float roughness,room_occupancy;'),
             (' vec3 lamp_local=room_lamp-local_pos;',
              ' vec3 lamp_local=vec3(0,2.94,-1.65)-local_pos;'),
             (' illumination+=vec3(.56,.55,.46)*max(dot(n,normalize(room_basis*vec3(1.,.45,.05))),0.)*room_side_light;\n','')]
    for current_text,previous_text in inverse:
        check(fragment.count(current_text)==1,'Shared room lighting insertion missing or repeated')
        fragment=fragment.replace(current_text,previous_text,1)
    check(fragment==(here/'city_interior-before.frag').read_text(),
          'Shared room shader modifies another material, alpha, fog or lighting operation')
    assets_before=load(here/'asset-manifest-before.json')['assets']
    assets_now=load(directory/'asset-manifest.json')['assets']
    prefix='custom_assets/jak3/city-interiors/'
    changed={prefix+'runtime.json','game/graphics/opengl_renderer/shaders/city_interior.frag'}
    check(len(assets_before)==39 and len(assets_now)==41 and
          set(assets_now)-set(assets_before)=={prefix+'corner-conversation'+ext for ext in('.bin','.json')}and
          all(motion.get('runtime_predecessor_sha256',{}).get(path,assets_now.get(path))==expected
              for path,expected in assets_before.items()if path not in changed),
          'Shared apartment revision changes an existing room, actor, texture or unrelated asset')

    author=load(here/'author-report.json');old_meta=load(here/'no-ao/corner-conversation.json')
    meta=load(here/'corner-conversation.json');bake=load(here/'ao/bake-report.json')
    matches(here/'author.py',author['author_sha256'])
    check(author['one_world_instance']is True and author['shared_windows']==
          ['wca-house1-west-room','wca-house1-east-room']and
          author['occupants']==[{'mesh':'conversing-male','position':[.25,.058,-2.15],'yaw':math.atan2(1.2,-.9)},
                               {'mesh':'conversing-female','position':[1.45,.058,-3.05],'yaw':math.atan2(-1.2,.9)}],
          'Shared room author duplicates or relocates its residents by window')
    check(meta['binary']==old_meta['binary']=='corner-conversation.bin'and
          sha(here/'corner-conversation.bin')==meta['sha256']==author['sha256']and
          sha(here/'no-ao/corner-conversation.bin')==old_meta['sha256']==meta['vertex_ao']['source_sha256']and
          (here/'ao/corner-conversation.bin').read_bytes()==(here/'corner-conversation.bin').read_bytes()and
          load(here/'ao/corner-conversation.json')==meta,
          'Shared room binaries differ from the authored and contact-shaded geometry')
    check(bake['parameters']=={'rays':128,'radius_m':.7,'gain':.4,'edge_m':.34}and len(bake['rooms'])==1,
          'Shared room changed its neutral contact-shading recipe')
    row=bake['rooms'][0]
    check(row['layout']=='corner-conversation'and row['source_sha256']==old_meta['sha256']and
          row['candidate_sha256']==meta['sha256']and row['source_vertices']==old_meta['vertex_count']and
          row['candidate_vertices']==meta['vertex_count'],
          'Shared room contact shading was baked from another source')
    allowed={'vertex_count','draws','sha256','vertex_ao'}
    check({k:v for k,v in old_meta.items()if k not in allowed}=={k:v for k,v in meta.items()if k not in allowed}and
          len(old_meta['draws'])==len(meta['draws'])and all(
              {k:v for k,v in a.items()if k not in('first','count')}==
              {k:v for k,v in b.items()if k not in('first','count')}
              for a,b in zip(old_meta['draws'],meta['draws'])),
          'Shared room AO modifies material assignment or metadata beyond tessellation/shading')
    old_rows=list(struct.iter_unpack('<12f',(here/'no-ao/corner-conversation.bin').read_bytes()))
    rows=list(struct.iter_unpack('<12f',(here/'corner-conversation.bin').read_bytes()))
    def area(vertices,draw):
        result=0.
        for index in range(draw['first'],draw['first']+draw['count'],3):
            a,b,c=vertices[index:index+3];u=[b[k]-a[k]for k in range(3)];v=[c[k]-a[k]for k in range(3)]
            cross=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            result+=.5*math.sqrt(sum(x*x for x in cross))
        return result
    check(len(rows)==meta['vertex_count']and len(old_rows)==old_meta['vertex_count']and
          all(math.isfinite(x)for vertex in rows for x in vertex),
          'Shared room has nonfinite data or incorrect vertex counts')
    check(all(abs(fn(v[k]for v in rows)-fn(v[k]for v in old_rows))<1e-6 for k in range(3)for fn in(min,max)),
          'Shared room AO changes its physical bounds')
    for old_draw,draw in zip(old_meta['draws'],meta['draws']):
        original_area=area(old_rows,old_draw)
        check(abs(original_area-area(rows,draw))<max(1e-5,original_area*1e-5),
              'Shared room AO changes the surface area of a material')
    check(all(abs(math.sqrt(sum(x*x for x in v[3:6]))-1)<1e-5 and
              v[8]==v[9]==v[10]and .599<=v[8]<=1 and v[11]==1 and
              abs(v[6]-(v[0]*.7+v[2]*.23))<2e-6 and abs(v[7]-(v[1]*.7+v[2]*.6))<2e-6 for v in rows),
          'Shared room AO changes UVs, normals, opacity or color beyond neutral contact shading')

    qa=load(here/'qa/validation.json')
    expected_checks={view+'_'+suffix for view in('front','side')for suffix in
                     ('animation_changes_pixels','nonempty_render','timing_finite')}|{
                     'actual_shaders_compile_link','all_geometry_finite','one_room_two_fixed_actor_instances',
                     'gl_no_errors','sources_assets_textures_unchanged'}
    check(qa['status']=='passed'and set(qa['checks'])==expected_checks and all(v is True for v in qa['checks'].values())and
          qa['room_instances']==1 and qa['actor_instances']==[
              ['conversing-male',[.25,.058,-2.15],math.atan2(1.2,-.9),0.],
              ['conversing-female',[1.45,.058,-3.05],math.atan2(-1.2,.9),0.]],
          'Shared room GPU proof does not use one physical room with both fixed animated occupants')
    matches(here/'qa_gpu_shared.py',qa['script_sha256']);matches(directory/'qa_gpu.py',qa['harness_sha256'])
    check(set(qa['shader_sha256'])=={str(directory/('city_interior.'+ext))for ext in('vert','frag')},
          'Shared room GPU proof compiled different shaders')
    actors=directory.parent/'inhabitants'
    expected_meshes={str((here if name=='corner-conversation'else actors)/(name+ext))
                     for name in('corner-conversation','conversing-male','conversing-female')for ext in('.bin','.json')}
    check(set(qa['asset_sha256'])==expected_meshes,'Shared room GPU proof drew different meshes')
    for field in('shader_sha256','asset_sha256','texture_sha256'):
        for path,expected in qa[field].items():matches(Path(path),expected)
    check({(row['view'],row['seconds'])for row in qa['renders']}=={(view,seconds)for view in('front','side')for seconds in(0.,1.4)},
          'Shared room GPU proof lacks both views and both animated poses')
    for render in qa['renders']:matches(Path(render['path']),render['sha256'])
    check(len(qa['timing'])==2 and {row['view']for row in qa['timing']}=={'front','side'}and
          all(row['samples']==24 and row['warmup']==10 and math.isfinite(row['gpu_elapsed_median_ms'])and
              row['gpu_elapsed_median_ms']>0 for row in qa['timing']),
          'Shared room timing proof is incomplete or nonfinite')
    return {'shader_predecessors':{(directory/'city_interior.frag').resolve():here/'city_interior-before.frag'}}
