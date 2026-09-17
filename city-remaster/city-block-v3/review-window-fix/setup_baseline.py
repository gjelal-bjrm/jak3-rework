"""Temporary native before-capture setup. Keeps a pinned copy of live data."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent
R=H.parents[2]
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 parent=json.loads((H.parent/'architecture/installed.json').read_text())
 current=json.loads((H.parent/'architecture/revision-002/installed.json').read_text())
 before=Path(parent['base_path']);live=R/'data'/parent['path']
 assert sha(before)==parent['base_sha256']
 assert sha(live)==current['output_sha256']
 backup=H/'baseline/live-before';backup.mkdir(parents=True,exist_ok=True)
 record={'description':'Before the two-house building pass, with the previously remastered textures retained. Not the original PS2 renderer.',
         'source':str(before),'source_sha256':sha(before),'restore':{}}
 for relative in ('out/jak3/fr3/wascitya.fr3','custom_assets/jak3/city-interiors/runtime.json'):
  source=R/'data'/relative;dest=backup/relative
  assert not dest.exists(),'Existing baseline backup must not be overwritten'
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
  record['restore'][relative]={'backup':str(dest),'sha256':sha(dest)}
 shutil.copy2(before,live)
 config=R/'data/custom_assets/jak3/city-interiors/runtime.json'
 j=json.loads(config.read_text());j['windows']=[];config.write_text(json.dumps(j,indent=2))
 (H/'baseline/setup.json').write_text(json.dumps(record,indent=2)+'\n')
 print('Temporary before-capture data ready; exact live state preserved')
if __name__=='__main__':main()
