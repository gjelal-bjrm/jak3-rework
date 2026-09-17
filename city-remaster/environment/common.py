"""Local environment-texture pipeline paths and guarded file operations."""
from pathlib import Path
import hashlib, json, os, shutil

HERE=Path(__file__).resolve().parent
CITY=HERE.parent
ROOT=CITY.parent
LEVELS=('wascitya','wascityb','waswide')
BLENDER_PYTHON=Path('C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe')
BRIDGE=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def digest(data):return hashlib.sha256(data).hexdigest()
def write(path,value):
    path=Path(path);temp=path.with_name(path.name+'.new')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');os.replace(temp,path)
def copy(source,dest):
    source,dest=Path(source),Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.environment-new');shutil.copy2(source,temp)
    assert sha(temp)==sha(source);os.replace(temp,dest)
def stage_path(value):
    p=(HERE/'staging'/value).resolve()
    assert p.parent==(HERE/'staging').resolve(), 'Stage must be one local directory name'
    return p
def relative(level):return f'out/jak3/fr3/{level}.fr3'
def records():
    paths=[HERE/'baselines/waswide/baseline.json',CITY/'installed.json',CITY/'static-installed.json',HERE/'foliage/installed.json',HERE/'installed.json']
    return [{'path':str(p),'sha256':sha(p),'value':read(p)} for p in paths if p.exists()]
def parent_for(level,current,parents):
    rel=relative(level)
    for item in reversed(parents):
        value=item['value']
        candidates=value.get('levels',[value])
        for entry in candidates:
            if entry.get('path')==rel and entry.get('output_sha256')==current:
                return {'record':item['path'],'record_sha256':item['sha256'],'path':rel,'output_sha256':current}
    raise ValueError(f'{level}: current FR3 has no matching tracked baseline/Merc/static/foliage/environment parent')
