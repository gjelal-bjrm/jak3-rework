"""Stage/apply the blade-root successor. Never build, start or package the game."""
from pathlib import Path
import argparse,hashlib,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SHADER='game/graphics/opengl_renderer/shaders/shrub.vert'
CPP='engine-src/game/graphics/opengl_renderer/background/Shrub.cpp'
H='engine-src/game/graphics/opengl_renderer/background/Shrub.h'
ANCHORS='engine-src/game/graphics/opengl_renderer/GrassAnchors.h'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return Path(path).read_text(encoding='utf-8-sig')
def edits():
 old=read(HERE.parent/'grass-contact/contact.glsl').strip()
 new=read(HERE/'contact.glsl').strip()
 load='''    // GRASS_ROOTS_BEGIN: per-blade anchors from the actual loaded mesh.
    const auto grass_anchors = GrassAnchors::build(tree, lev_data->textures, lev_data->level_name);
    if (!grass_anchors.vertices.empty()) {
      glGenBuffers(1, &m_trees[l_tree].grass_root_buffer);
      glBindBuffer(GL_ARRAY_BUFFER, m_trees[l_tree].grass_root_buffer);
      glBufferData(GL_ARRAY_BUFFER, grass_anchors.vertices.size() * sizeof(GrassAnchors::Attribute),
                   grass_anchors.vertices.data(), GL_STATIC_DRAW);
      glEnableVertexAttribArray(4);
      glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, sizeof(GrassAnchors::Attribute), nullptr);
      lg::info("Remaster grass roots [{}]: {} blades, {} vertices, max height {:.3f}m, {} missing roots",
               lev_data->level_name, grass_anchors.blades, grass_anchors.affected_vertices,
               grass_anchors.max_height, grass_anchors.unanchored_components);
    } else {
      glDisableVertexAttribArray(4);
      glVertexAttrib4f(4, 0.f, 0.f, 0.f, 0.f);
    }
    // GRASS_ROOTS_END

'''
 return {
  **{tree+'/'+SHADER:[(old,new)]for tree in('engine-src','data')},
  CPP:[('#include "Shrub.h"\n','#include "Shrub.h"\n#include "game/graphics/opengl_renderer/GrassAnchors.h"\n'),
       ('    glGenBuffers(1, &m_trees[l_tree].single_draw_index_buffer);\n',load+'    glGenBuffers(1, &m_trees[l_tree].single_draw_index_buffer);\n'),
       ('    glDeleteBuffers(1, &tree.single_draw_index_buffer);\n','    glDeleteBuffers(1, &tree.single_draw_index_buffer);\n    if (tree.grass_root_buffer) glDeleteBuffers(1, &tree.grass_root_buffer);\n')],
  H:[('    GLuint vertex_buffer;\n','    GLuint vertex_buffer;\n    GLuint grass_root_buffer = 0;\n')]
 }
def inverse(source,relative):
 for old,new in reversed(edits()[relative]):
  assert source.count(new)==1, 'Modified successor block: '+relative
  source=source.replace(new,old,1)
 return source
def source_before(relative):
 manifest=json.loads(read(HERE/'manifest.json'));entry=manifest['files'][relative]
 actual=ROOT/relative;digest=sha(actual.read_bytes())
 if digest==entry['before_sha256']:return actual
 assert digest==entry['after_sha256'], 'Unrecognized grass v2 source: '+relative
 before=Path(entry['before_path'])
 assert sha(before.read_bytes())==entry['before_sha256']
 assert inverse(read(actual),relative)==read(before)
 return before
def verify_sources(check,matches):
 record=json.loads(read(HERE/'manifest.json'))
 check(set(record['files'])==set(edits()),'Grass roots successor changed its source scope')
 check(record['new_header']==ANCHORS,'Grass roots header path changed')
 matches(ROOT/ANCHORS,record['new_header_sha256'])
 matches(HERE/'GrassAnchors.h',record['new_header_sha256'])
 result={}
 for relative,entry in record['files'].items():
  matches(ROOT/relative,entry['after_sha256'])
  matches(Path(entry['before_path']),entry['before_sha256'])
  matches(Path(entry['candidate_path']),entry['after_sha256'])
  result[relative]=source_before(relative)
  check(result[relative]==Path(entry['before_path']),'Grass roots successor is not fully applied: '+relative)
 check((ROOT/'engine-src'/SHADER).read_bytes()==(ROOT/'data'/SHADER).read_bytes(),'Grass roots engine/data shader mismatch')
 proof=json.loads(read(HERE/'qa/gpu-validation.json'))
 check(proof['status']=='passed'and all(proof['checks'].values()),'Grass roots native-mesh GPU checks failed')
 matches(ROOT/'engine-src'/SHADER,proof['shader_sha256'])
 matches(Path(proof['native_export']),proof['native_export_sha256'])
 return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--apply-source',action='store_true');parser.add_argument('--apply-data',action='store_true');args=parser.parse_args()
 manifest_path=HERE/'manifest.json'
 existing=json.loads(read(manifest_path))if manifest_path.exists()else None
 entries={}
 for relative,changes in edits().items():
  target=ROOT/relative
  before=source_before(relative)if existing else target
  raw=before.read_bytes();source=read(before);updated=source
  for old,new in changes:
   assert updated.count(old)==1,'Unexpected anchor: '+relative
   updated=updated.replace(old,new,1)
  assert inverse(updated,relative)==source
  newline='\r\n'if b'\r\n'in raw else'\n';candidate=updated.replace('\n',newline).encode()
  baseline=HERE/'before'/relative;output=HERE/'staging'/relative
  baseline.parent.mkdir(parents=True,exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
  if baseline.exists():assert baseline.read_bytes()==raw
  else:baseline.write_bytes(raw)
  output.write_bytes(candidate)
  entries[relative]={'before_path':str(baseline),'before_sha256':sha(raw),'candidate_path':str(output),'after_sha256':sha(candidate)}
  apply=(relative.startswith('engine-src/')and args.apply_source)or(relative.startswith('data/')and args.apply_data)
  if apply:target.write_bytes(candidate)
 header=HERE/'GrassAnchors.h'
 if args.apply_source:(ROOT/ANCHORS).write_bytes(header.read_bytes())
 record={'status':'source_applied'if args.apply_source else('data_applied'if args.apply_data else'staged'),
  'scope':'Actual closed grass blade roots; only market-shrub-orange-v1 in WCA/WCB',
  'files':entries,'new_header':ANCHORS,'new_header_sha256':sha(header.read_bytes()),
  'goal_changed':False,'geometry_changed':False,'runtime_built':False,'native_visual_validation':False}
 manifest_path.write_text(json.dumps(record,indent=2)+'\n')
 for relative in entries:source_before(relative)
 print(json.dumps({'status':record['status'],'files':list(entries),'new_header':ANCHORS},indent=2))
if __name__=='__main__':main()
