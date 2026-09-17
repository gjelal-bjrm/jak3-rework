"""Select complete native Spargus outfits, preserving GLB skin and textures."""
from pathlib import Path
import sys,json,struct,hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'city-remaster'))
from compare_market import Reader
import zstandard

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    source=BASE/'active/jak3/data'
    compressed=(source/'out/jak3/fr3/waswide.fr3').read_bytes()
    raw=zstandard.ZstdDecompressor().decompress(compressed[8:])
    result={}
    for sex,effects in [('male',[2,3,4,5,8,9]),('female',[4,5,8,9,10,17])]:
        name='wlander-'+sex+'-lod0'
        path=source/('decompiler_out/jak3/levels/waswide/'+name+'.glb')
        data=path.read_bytes();size=struct.unpack_from('<I',data,12)[0]
        j=json.loads(data[20:20+size]);tail=data[20+size:]
        key=name.encode();r=Reader(raw,raw.find(struct.pack('<Q',len(key))+key))
        assert r.string()==name
        selections=[];all_primitives=j['meshes'][0]['primitives'];offset=0;chosen=[]
        for effect in range(r.count()):
            count=r.count();r.raw(count*22)
            if effect in effects:
                chosen.extend(all_primitives[offset:offset+count])
                selections.append({'effect':effect,'primitives':list(range(offset,offset+count)),
                    'materials':[j['materials'][p['material']].get('name')for p in all_primitives[offset:offset+count]]})
            offset+=count
            r.raw(r.count()*22);r.raw(r.count()*22);r.vector(64);r.vector(2);r.vector(1);r.raw(4);r.vector(32);r.vector(4);r.raw(10)
        assert offset==len(all_primitives)
        j['meshes'][0]['primitives']=chosen
        encoded=json.dumps(j,separators=(',',':')).encode()
        encoded+=b' '*((-len(encoded))%4)
        output=struct.pack('<III',0x46546c67,2,12+8+len(encoded)+len(tail))+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+tail
        target=HERE/(sex+'-selected.glb');target.write_bytes(output)
        result[sex]={'source':str(path),'source_sha256':sha(data),'selected_sha256':sha(output),
          'fr3_sha256':sha(compressed),'effects':selections,'excluded':'weapons and alternate overlapping bodies; complete single outfit selected from native Merc effect ranges'}
    (HERE/'source-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
