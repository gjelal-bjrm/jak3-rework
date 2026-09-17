"""Verify the WWD rebuild object-by-object and register it with the variants."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REL='out/jak3/iso/WWD.DGO'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def objects(p):
    data=p.read_bytes();count=struct.unpack_from('<I',data)[0];offset=64;result={};occurrences={}
    for _ in range(count):
        size=struct.unpack_from('<I',data,offset)[0]
        name=data[offset+4:offset+64].split(b'\0',1)[0].decode()
        occurrences[name]=occurrences.get(name,0)+1
        # WWD includes duplicate texture-page names; compare each occurrence.
        key=name if occurrences[name]==1 else f'{name}#{occurrences[name]}'
        offset+=64
        result[key]=hashlib.sha256(data[offset:offset+size]).hexdigest()
        offset+=(size+15)&~15
    assert offset==len(data)
    return result

def copy(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_name(dst.name+'.market-contact-new')
    shutil.copy2(src,tmp);os.replace(tmp,dst)

def main():
    baseline=HERE/'fruit-contact-before/WWD.DGO'
    original=ROOT.parents[1]/'active/jak3/data'/REL
    current=ROOT/'data'/REL
    assert sha(original)==sha(baseline),'Untracked original WWD change'
    before=objects(baseline);after=objects(current)
    assert list(before)==list(after),'WWD object set/order changed'
    changed=[name for name in before if before[name]!=after[name]]
    assert changed==['ctymark-obs'],changed
    files=json.loads((ROOT/'variant-files.json').read_text())
    hashes=json.loads((ROOT/'variant-hashes.json').read_text())
    if REL not in files:files.append(REL)
    for variant in ('original','remaster-v1','remaster'):
        source=current if variant=='remaster' else baseline
        dest=ROOT/'variants'/variant/REL
        if variant!='remaster' and dest.exists():assert sha(dest)==sha(baseline)
        copy(source,dest);hashes[variant][REL]=sha(dest)
    record={'path':REL,'original_path':str(original),'baseline_sha256':sha(baseline),
            'output_sha256':sha(current),'before_objects':before,'after_objects':after,
            'changed_objects':changed,'preserved_objects':len(before)-len(changed),
            'status':'passed'}
    for p,value in ((ROOT/'variant-files.json',files),(ROOT/'variant-hashes.json',hashes),
                    (HERE/'fruit-contact-installed.json',record)):
        p.write_text(json.dumps(value,indent=2))
    print(f'WWD registered: only ctymark-obs changed; {len(before)-1} objects preserved')

if __name__=='__main__':main()
