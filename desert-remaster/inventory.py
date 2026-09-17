"""Inventory source texture placements for the desert and Spargus remaster."""
from pathlib import Path
from PIL import Image
import hashlib,json,collections
ROOT=Path(__file__).resolve().parents[1]
base=ROOT/'data/decompiler_out/jak3/textures'
records=[];pages=collections.Counter();families=collections.Counter();unique={}
for page in sorted(base.iterdir()):
    if not page.is_dir() or not page.name.startswith(('des','was')):continue
    for path in sorted(page.glob('*.png')):
        with Image.open(path) as source:
            im=source.convert('RGBA');size=im.size;alpha=im.getchannel('A').getextrema()
            digest=hashlib.sha256(bytes(str(size),'ascii')+im.tobytes()).hexdigest()
        group='terrain/architecture' if any(s in page.name for s in ('tfrag','hfrag')) else (
            'vegetation/decors' if 'shrub' in page.name else (
            'effets/eau' if any(s in page.name for s in ('water','sprite','alpha')) else (
            'interface' if any(s in page.name for s in ('minimap','warp')) else 'objets/personnages-a-trier')))
        records.append({'page':page.name,'file':path.name,'size':size,'alpha':alpha,'pixels_sha256':digest,'family':group})
        pages[page.name]+=1;families[group]+=1;unique.setdefault(digest,[]).append(str(path.relative_to(base)))
report={'scope':'Desert and Spargus texture pages; provisional categories require visual review.',
        'placements':len(records),'unique_pixel_images':len(unique),'pages':dict(pages),
        'families':dict(families),'textures':records,'shared_images':{h:p for h,p in unique.items() if len(p)>1}}
(ROOT/'desert-remaster/inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('placements','unique_pixel_images','families')},ensure_ascii=False,indent=2))
