"""Package the generated leaf albedo and retain the accepted pots/bowls/trunks."""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;V1=ROOT/'models-v1'
image=Image.open(HERE/'leaf-tissue-master.png').convert('RGBA').resize((1024,1024),Image.Resampling.LANCZOS)
image.save(HERE/'leaf-tissue-1024.png');(HERE/'leaf-tissue.rgba').write_bytes(image.tobytes())
textures=[]
for name,page in (('waspala-palmplant-leaf-02','waspala-tfrag'),('waspala-shrub-plant','waspala-shrub'),('for-shrub-moss','waspala-shrub')):
    textures.append({'name':name,'width':1024,'height':1024,'rgba_file':str(HERE/'leaf-tissue.rgba')})
    path=ROOT/'data/custom_assets/jak3/texture_replacements'/page/(name+'.png')
    path.parent.mkdir(parents=True,exist_ok=True)
    old=HERE/'before'/(name+'.png')
    if path.exists() and not old.exists():shutil.copy2(path,old)
    image.save(path)
(HERE/'native-textures.json').write_text(json.dumps(textures,indent=2))
# Keep precisely the trunk and rivet components from the previous lot.
source=json.loads((V1/'native-objects.json').read_text())['faces']
keys={(f['geom'],f['tree'],f['draw']) for f in source if f['tree_type']=='tie' and f['proto'] in (23,28)}
kept={'description':'Accepted rounded trunks and rivets from the first lot','remove':[],'add':[]}
for name in ('foliage-patch.json','throne-patch.json'):
    part=json.loads((HERE/'before'/name).read_text())
    for action in ('remove','add'):
        kept[action].extend(f for f in part[action] if f.get('tree_type','tie')=='tie' and (name=='throne-patch.json' or (f['geom'],f['tree'],f['draw']) in keys))
(HERE/'preserved-patch.json').write_text(json.dumps(kept,separators=(',',':')))
config={'parts':['brazier-patch.json','planter-patch.json','../models-v2/preserved-patch.json','../models-v2/throne-patch.json','../models-v2/foliage-patch.json'],
        'texture_manifest':'../models-v2/native-textures.json'}
(V1/'model-set.json').write_text(json.dumps(config,indent=2))
(HERE/'generation.json').write_text(json.dumps({'tool':'built-in image_gen','master':str(HERE/'leaf-tissue-master.png'),
 'sha256':hashlib.sha256((HERE/'leaf-tissue-master.png').read_bytes()).hexdigest(),
 'prompt':'Square albedo entirely filled with the tissue of a single olive-green leaf; vertical centre vein, fine angled side veins, warm olive/sage palette, flat even lighting, no silhouette, margin, background, transparency, text, or baked highlights. Stylized realistic asset for modeled individual leaves in the Jak 3 desert remaster.',
 'packaging':'Resized to 1024x1024 RGBA; mesh geometry supplies the leaf silhouette.'},indent=2))
print('Leaf texture and active model set prepared')
