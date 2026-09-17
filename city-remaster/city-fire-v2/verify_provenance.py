"""Read-only chain checks, including deliberately corrupted in-memory candidates."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    apply=module(HERE/'apply.py','fire_apply');reg=module(HERE/'register.py','fire_register')
    reg.source_proof();checks={'all_source_and_fit_hashes':True};archives=[]
    for scene in ('arena','palace'):
      raw=(ROOT/'routes/remaster'/scene/'GAME.CGO').read_bytes();head,objects=reg.codec.archive(raw)
      old=next(x for x in objects if x['name']=='generic-obs')['payload']
      payload=old+b'CITY-FIRE-IN-MEMORY-PRESERVATION-TEST'
      candidate=reg.codec.replace_object(raw,payload);proof=reg.preservation(raw,candidate,payload)
      # A second object altered, even just one payload byte, must fail.
      ah,ao=reg.codec.archive(candidate);other=next(x for x in ao if x['name']!='generic-obs'and x['payload'])
      blocks=[x['block']for x in ao];block=bytearray(other['block']);block[64]^=1;blocks[other['index']]=bytes(block)
      rejected=False
      try:reg.preservation(raw,ah+b''.join(blocks),payload)
      except AssertionError:rejected=True
      assert rejected;archives.append({'scene':scene,'preserved_objects':proof['preserved_objects'],'unexpected_object_mutation_rejected':True})
    checks['archive_target_only_and_negative_mutation']=True
    record=json.loads((HERE/'manifest.json').read_text())
    for relative,entry in record['files'].items():
      text=(ROOT/relative).read_text();before=Path(entry['before_path']).read_text()
      assert apply.inverse(text,relative)==before
      # A random extra line cannot disappear through the exact inverse.
      assert apply.inverse(text+'\n// unrelated edit\n',relative)!=before
    checks['source_inverse_preserves_unrelated_edits']=True
    shared=module(ROOT/'city-remaster/verify_descendants.py','fire_shared_proof');errors=[];count=[0]
    def check(ok,msg):
      count[0]+=1
      if not ok:errors.append(msg)
    def matches(p,h):check(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,str(p))
    shared.verify_grass_sources(check,matches);assert not errors,errors
    checks['existing_grass_source_chain_preserved']=True
    output={'status':'passed','checks':checks,'shared_source_checks':count[0],'archives':archives,
            'candidate_archive_deployed':False,'native_visual_validation':False}
    (HERE/'provenance-validation.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
if __name__=='__main__':main()
