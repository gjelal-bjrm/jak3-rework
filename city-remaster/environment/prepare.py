"""Discover approved master PNGs and export RGBA bytes, without image retouching."""
import argparse
from PIL import Image, ImageStat
from common import *

def prepare(destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    manifest=HERE/'generated-materials.json';manifest_hash=sha(manifest);approved=read(manifest)
    assert isinstance(approved,list) and approved
    names=[m['name'] for m in approved];assert len(names)==len(set(names)), 'Duplicate approved names'
    assert all(Path(n).name==n and '/' not in n and '\\' not in n for n in names)
    source=read(CITY/'inventory.json')['textures']
    present={p.stem:p for p in (HERE/'masters').glob('*.png')}
    assert not set(present)-set(names), f'Unapproved PNGs: {set(present)-set(names)}'
    materials=[]
    for item in approved:
        name=item['name']
        if name not in present:continue
        p=present[name];refs=[t for t in source if t['name']==name and t['page'].startswith(LEVELS)]
        assert refs, f'No native reference for {name}'
        assert all(t['alpha']==[128,128] for t in refs), f'{name}: nonopaque source requires a dedicated alpha policy'
        master_hash=sha(p)
        with Image.open(p) as im:
            assert im.format=='PNG';im.load();rgb=im.convert('RGB');w,h=im.size
            if 'A' in im.getbands():
                amin,amax=im.getchannel('A').getextrema()
                assert amin==amax and amin in (128,255), f'{name}: master has unexpected transparency'
            assert 1<=w<=16384 and 1<=h<=16384
            assert all(abs(w/h-t['size'][0]/t['size'][1])<.04 for t in refs), f'{name}: source aspect ratio changed'
            # Only engine-format encoding: RGB is copied exactly; opaque PS2 alpha is128.
            rgba=rgb.convert('RGBA');rgba.putalpha(128);pixels=rgba.tobytes()
            assert bytes(c for i,c in enumerate(pixels) if i%4!=3)==rgb.tobytes()
            raw=destination/(name+'.rgba');raw.write_bytes(pixels)
            materials.append({'name':name,'width':w,'height':h,'rgba_file':str(raw.resolve()),
                'rgba_sha256':digest(pixels),'master':str(p.resolve()),'master_sha256':master_hash,
                'rgb_sha256':digest(rgb.tobytes()),'mean_rgb':ImageStat.Stat(rgb).mean,
                'native_alpha':128,'references':[{k:t[k] for k in ('page','size','alpha','path','pixels_sha256')} for t in refs],
                'generation':item,
                'generated_file_sha256':sha(item['generated']) if item.get('generated') and Path(item['generated']).is_file() else None})
        assert sha(p)==master_hash, 'Master changed during preparation'
    assert materials, 'No approved master PNG exists yet'
    assert sha(manifest)==manifest_hash, 'Generation manifest changed during preparation'
    result={'manifest':str(manifest),'manifest_sha256':manifest_hash,'conversion':'Unchanged RGB pixels; constant native opaque alpha128',
        'materials':materials,'approved_not_yet_present':sorted(set(names)-set(present))}
    write(destination/'prepared.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=HERE/'prepared')
    a=parser.parse_args();out=a.out.resolve();assert out.is_relative_to(HERE.resolve())
    result=prepare(out);print(json.dumps({'prepared':len(result['materials']),'pending':result['approved_not_yet_present'],'report':str(out/'prepared.json')},indent=2))
