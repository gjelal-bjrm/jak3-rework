"""Merge disjoint Blender parts, stage native meshes, audit and optionally deploy.

Large plant patches are streamed, never accumulated as Python face objects.
Only WCA/WCB geometry descendants of the exact installed ENV stage are allowed.
"""
from pathlib import Path
import argparse,json,hashlib,math,sys,shutil,os,subprocess
HERE=Path(__file__).resolve().parent;ENV=HERE.parent;CITY=ENV.parent;ROOT=CITY.parent
sys.path.insert(0,str(CITY))
from audit_native_patch import audit
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,j):Path(p).write_text(json.dumps(j,indent=2)+'\n')
def key(f):return tuple(f.get(k,0) for k in ('tree_type','geom','tree','draw','group','stream_index'))

class Reader:
    def __init__(self,f):self.f=f;self.buf='';self.pos=0;self.eof=False;self.decoder=json.JSONDecoder()
    def more(self):
        self.buf=self.buf[self.pos:]+self.f.read(65536);self.pos=0
        if not self.buf:self.eof=True
    def skip(self):
        while True:
            while self.pos<len(self.buf) and self.buf[self.pos].isspace():self.pos+=1
            if self.pos<len(self.buf):return self.buf[self.pos]
            self.more()
            if self.eof:raise ValueError('Unexpected EOF')
    def char(self,wanted):assert self.skip()==wanted,(wanted,self.buf[self.pos:self.pos+60]);self.pos+=1
    def value(self):
        self.skip()
        while True:
            try:v,end=self.decoder.raw_decode(self.buf,self.pos);self.pos=end;return v
            except json.JSONDecodeError:
                rest=self.buf[self.pos:];more=self.f.read(65536)
                if not more:raise
                self.buf=rest+more;self.pos=0

def fields(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        r=Reader(f);r.char('{')
        while r.skip()!='}':
            name=r.value();r.char(':')
            if r.skip()=='[':
                r.char('[');i=0
                while r.skip()!=']':
                    yield name,i,r.value();i+=1
                    if r.skip()==',':r.char(',')
                    else:break
                r.char(']')
            else:yield name,None,r.value()
            if r.skip()==',':r.char(',')
            else:break
        r.char('}')

def stage(level):
    out=HERE/(level+'.fr3');assert not out.exists(),'Use a new immutable stage for a new candidate'
    parent_path=ENV/'installed.json';parent=next(e for e in read(parent_path)['levels'] if e['level']==level)
    base=Path(parent['candidate']);base_hash=sha(base);assert base_hash==parent['output_sha256']
    parts=[ENV/'architecture-coping'/(level+'-patch.json'),ENV/'architecture/windows'/(level+'-patch.json'),ENV/'vegetation-v2'/(level+'-patch.json')]
    assert all(p.exists() for p in parts),'Wait for all independently authored parts'
    facade=read(ENV/'architecture-coping'/(level+'-independent-validation.json'))
    windows=read(ENV/'architecture/windows/validation.json')
    plants=read(ENV/'vegetation-v2'/(level+'-validation.json'))
    assert facade['status']=='passed' and all(facade['checks'].values()) and facade['patch_sha256']==sha(parts[0])
    assert windows['status']=='passed' and all(windows['checks'].values())
    assert windows['levels'][level]['patch_sha256']==sha(parts[1])
    assert plants['passed'] and plants['patch_sha256']==sha(parts[2])
    remove=[];seen=set();textures={};part_reports=[];added=0;minimum=math.inf;maxnormal=0
    spool=HERE/(level+'-add.tmp');patch=HERE/(level+'-patch.json')
    with spool.open('w',encoding='utf-8') as output:
        for part in parts:
            nadd=nremove=0;seen_source=False
            for name,index,value in fields(part):
                if name=='source_fr3':assert value['sha256']==base_hash;seen_source=True
                elif name=='level':assert value==level
                elif name=='new_textures':
                    assert Path(value['rgba_file']).stat().st_size==value['width']*value['height']*4
                    if value['name'] in textures:assert textures[value['name']]==value
                    textures[value['name']]=value
                elif name=='remove':
                    assert key(value) not in seen,'Independent authors overlap a native face'
                    seen.add(key(value));remove.append(value);nremove+=1
                elif name=='add':
                    assert value['tree_type'] in ('tie','shrub'),'Unexpected geometry family'
                    assert len(value['vertices'])==3
                    for v in value['vertices']:
                        assert all(math.isfinite(x) for k in ('p','uv','normal','color_weights') for x in v[k])
                        maxnormal=max(maxnormal,abs(math.sqrt(sum(x*x for x in v['normal']))-1))
                        assert abs(sum(v['color_weights'])-1)<.002
                    a,b,c=[v['p'] for v in value['vertices']];u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
                    area=.5*math.sqrt(sum(x*x for x in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))
                    minimum=min(minimum,area)
                    assert area>1e-12,'Degenerate authored face; fix author before staging'
                    if added:output.write(',')
                    output.write(json.dumps(value,separators=(',',':')));added+=1;nadd+=1
            assert seen_source,'Unpinned part source'
            part_reports.append({'path':str(part),'sha256':sha(part),'removed':nremove,'added':nadd})
            print(json.dumps(part_reports[-1]),flush=True)
    assert maxnormal<.002
    header={'level':level,'source_fr3':{'sha256':base_hash,'bytes':base.stat().st_size},'preserve_bvh':True,
            'new_textures':list(textures.values()),'remove':remove}
    with patch.open('w',encoding='utf-8') as output:
        output.write(json.dumps(header,separators=(',',':'))[:-1]+',"add":[')
        with spool.open(encoding='utf-8') as input:shutil.copyfileobj(input,output,1024*1024)
        output.write(']}')
    spool.unlink()
    protected={str(ROOT/'variants'/variant/parent['path']):sha(ROOT/'variants'/variant/parent['path']) for variant in ('original','remaster-v1')}
    author=HERE/(level+'-author-validation.json')
    write(author,{'status':'passed','checks':{'disjoint_removal_keys':True,'pinned_common_parent':True,'finite_vertices':True,'normalized_normals':True,'nondegenerate_triangles':True},
                  'parts':part_reports,'minimum_area_m2':minimum,'maximum_normal_error':maxnormal,'removed':len(remove),'added':added})
    # Release author dictionaries before the native process parses the patch.
    del remove,header,seen
    bridge=ROOT/'engine-build/bin/Release/palace_mesh_bridge.exe'
    with (HERE/(level+'-bridge.log')).open('w') as log:
        subprocess.run([str(bridge),str(base),str(patch),str(out)],check=True,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
    preservation=HERE/(level+'-preservation.json');proof=audit(base,out,patch,preservation)
    assert all(sha(p)==h for p,h in protected.items())
    record={'status':'candidate_audited_not_installed','path':parent['path'],'base_path':str(base),'base_sha256':base_hash,
       'output_path':str(out),'output_sha256':sha(out),'patch':str(patch),'patch_sha256':sha(patch),
       'author_report':str(author),'author_report_sha256':sha(author),'preservation_report':str(preservation),'preservation_report_sha256':sha(preservation),
       'parent_record':str(parent_path),'parent_record_sha256':sha(parent_path),'parts':part_reports,
       'protected_variant_hashes':protected,'native_visual_validation':False,'scope':'City plaster/coping, window frames, complete cactus and grass models authored in Blender'}
    replaced_path=ENV/'geometry-001'/(level+'-installed.json')
    replaced=read(replaced_path)
    assert replaced['base_sha256']==base_hash
    record['replaces_record']=str(replaced_path)
    record['replaces_record_sha256']=sha(replaced_path)
    record['replaces_output_sha256']=replaced['output_sha256']
    record['replacement_reason']='Native visual review rejected inset facade seams; restore continuous original walls and retain authored rounded coping, windows and vegetation.'
    write(HERE/(level+'-candidate.json'),record)
    return record

def deploy(apply):
    records=[read(HERE/(level+'-candidate.json')) for level in ('wascitya','wascityb')]
    for r in records:
        for p,h in [('base_path','base_sha256'),('output_path','output_sha256'),('patch','patch_sha256'),('author_report','author_report_sha256'),('preservation_report','preservation_report_sha256'),('parent_record','parent_record_sha256')]:assert sha(r[p])==r[h]
        proof=read(r['preservation_report']);assert proof['status']=='passed' and all(proof['checks'].values())
        assert proof['before_sha256']==r['base_sha256'] and proof['after_sha256']==r['output_sha256'] and proof['patch_sha256']==r['patch_sha256']
        assert sha(r['replaces_record'])==r['replaces_record_sha256']
        for tree in ('data','variants/remaster'):assert sha(ROOT/tree/r['path'])==r['replaces_output_sha256']
        for p,h in r['protected_variant_hashes'].items():assert sha(p)==h
    print(json.dumps({'action':'deploy','apply':apply,'levels':{r['path']:r['output_sha256'] for r in records}}),flush=True)
    if not apply:return
    def copy(src,dst):
        dst=Path(dst);temp=dst.with_name(dst.name+'.geometry-new');shutil.copy2(src,temp);assert sha(temp)==sha(src);os.replace(temp,dst)
    hashes_path=ROOT/'variant-hashes.json';before=hashes_path.read_bytes();(HERE/'variant-hashes-before.json').write_bytes(before)
    try:
        hashes=json.loads(before.decode('utf-8-sig'))
        for r in records:
            for tree in ('data','variants/remaster'):copy(r['output_path'],ROOT/tree/r['path'])
            hashes['remaster'][r['path']]=r['output_sha256']
        write(hashes_path,hashes)
        for r in records:
            r['status']='installed';write(HERE/(Path(r['path']).stem+'-installed.json'),r)
    except BaseException:
        for r in records:
            for tree in ('data','variants/remaster'):copy(read(r['replaces_record'])['output_path'],ROOT/tree/r['path'])
        hashes_path.write_bytes(before);raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--level',choices=['wascitya','wascityb']);p.add_argument('--deploy',action='store_true');p.add_argument('--apply',action='store_true');args=p.parse_args()
    if args.deploy:deploy(args.apply)
    else:assert args.level and not args.apply;stage(args.level)
