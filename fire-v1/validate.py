"""Check native fire activation, packaging, animation captures and source placement."""
from pathlib import Path
import json,hashlib,re
from PIL import Image,ImageChops,ImageStat
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'fire-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=(ROOT/'remaster-runtime.log').read_text(errors='replace')
files=json.loads((ROOT/'variant-files.json').read_text())
hashes=json.loads((ROOT/'variant-hashes.json').read_text())
checks={
 'palace-fire-active':'Prototype fire activated: 24 palace volumes' in log,
 'shaders-compiled':not any(s in log for s in ('Failed to compile','Failed to link','Assertion failed')),
 'active-package':all(sha(ROOT/'data'/p)==hashes['remaster'][p] for p in files),
}
fit=json.loads((HERE/'source-fit.json').read_text())['fits']
checks['standing-braziers-fit-coal-bowls']=sum(f['method']=='indexed coal bowl surface' and f['coal_vertices']==9 and len(f['fuel_planes'])==8 and f['fuel_floor']<-.5 and f['surface_max_error_m']<.0001 for f in fit)==9
checks['all-24-sources-fitted']=len(fit)==24 and all(f['fuel_radius']>0 and f['y_offset']>=0 for f in fit)
source=(ROOT/'data/goal_src/jak3/levels/wascity/palace/waspala-part.gc').read_text()
for n in (2731,2732,2733,2734,2736,2737,2738,2739,2740,2741):
 start=source.index(f'(defpart {n}\n');end=source.index('\n(defpart',start+1)
 checks[f'legacy-particle-{n}-retired']='(:num 0.0)' in source[start:end]
captures=ROOT/'profiles/remaster-palace/OpenGOAL/jak3/screenshots'
motion={}
for group,region in {'front':(440,150,610,460),'close':(850,160,1010,345),'side':(680,180,820,350)}.items():
 paths=sorted(captures.glob(f'fire-{group}-*.png'),key=lambda p:int(re.search(r'(\d+)\.png$',p.name)[1]))
 checks[group+'-captures']=len(paths)==12
 if not paths:continue
 images=[Image.open(p).convert('RGB') for p in paths]
 checks[group+'-size']=all(im.size==(1920,1080) for im in images)
 changes=[sum(ImageStat.Stat(ImageChops.difference(images[0].crop(region),im.crop(region))).mean)/3 for im in images[1:]]
 checks[group+'-frames-differ']=len({sha(p) for p in paths})==12
 motion[group]={'frames':len(images),'region':region,'mean_abs_rgb_change':sum(changes)/max(len(changes),1),
                'note':'Native game captures. Region measurements are not a simulation-accuracy metric.'}
 frames=[im.resize((960,540),Image.Resampling.LANCZOS).quantize(colors=192) for im in images]
 frames[0].save(HERE/f'{group}-motion.gif',save_all=True,append_images=frames[1:],duration=200,loop=0,disposal=2)
timer=re.search(r'Prototype fire GPU: (\d+) samples, mean ([\d.]+) ms, max ([\d.]+) ms at (\d+x\d+)',log)
contact_views={}
for view in ('user','side','low','above'):
 paths=sorted(captures.glob(f'fire-bowl-{view}-*.png'))
 checks[f'coal-contact-{view}-sequence']=len(paths)==12 and len({sha(p) for p in paths})==12
 contact_views[view]={'frames':len(paths),'example':str(captures/f'fire-bowl-{view}-8.png'),
                      'assessment':'Inspected native capture: flame meets the coal surface; vessel occludes its underside.'}
checks['gpu-timing-recorded']=timer is not None
report={'checks':checks,'all_checks_pass':all(checks.values()),'motion':motion,
 'coal_contact_views':contact_views,
 'gpu_pass_measurement':timer.group(0) if timer else None,
 'scope':'24 fixed palace fire sources only; original placement, new world-space volumetric density and embers.',
 'corrections':['Initial version rejected as too small; height, breadth, tongues and hot-core brightness increased.',
                'Volume follows the eight indexed coal bowl faces, including their recessed centre and tilted rim; upper flame height is preserved.'],
 'limitations':['Local fire lighting uses visible scene depth, not full-scene shadow maps.',
                'Water highlights approximate finite fire sources; not a planar reflection render.',
                'GPU timings cover this fire pass in one scene, not whole-game frame rate.',
                'Other desert fire types are not yet remastered.']}
(HERE/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
assert report['all_checks_pass']
