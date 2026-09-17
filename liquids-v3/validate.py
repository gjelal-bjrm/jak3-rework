"""Check packaged hashes and report measurements from native game captures."""
from pathlib import Path
import hashlib,json,re
from PIL import Image,ImageChops,ImageStat
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=json.loads((ROOT/'variant-files.json').read_text())
hashes=json.loads((ROOT/'variant-hashes.json').read_text())
old=json.loads((ROOT/'liquids-v3/variant-hashes-before-v3.json').read_text())
checks={}
for variant in ('original','remaster-v1','remaster'):
    checks[variant]=all(sha(ROOT/'variants'/variant/f)==hashes[variant][f] for f in files)
    if variant!='remaster':
        checks[variant+'-preserved']=all(hashes[variant][f]==v for f,v in old[variant].items())
checks['active-data-matches-v3']=all(sha(ROOT/'data'/f)==hashes['remaster'][f] for f in files)
runtime=json.loads((ROOT/'liquids-v3/runtime-manifest.json').read_text())
checks['runtime']=sha(ROOT/runtime['runtime'])==runtime['sha256']
log=(ROOT/'remaster-runtime.log').read_text(errors='replace')
checks['basin-material-activated']='Prototype water activated: merc, animated basin slot 83' in log
checks['real-jak-contact-recorded']='Prototype water contact: Jak' in log
checks['landing-response-recorded']='Prototype water landing:' in log
checks['four-basin-shore-field-loaded']='Prototype shoreline: four basin contours loaded' in log
checks['shaders-compiled']=not any(s in log for s in ('Failed to compile','Failed to link','Assertion failed'))
checks['official-comparison-booted']='waspala is loaded' in (ROOT/'original-runtime.log').read_text(errors='replace')
original_routes={'arena':'28f288666a458ddb518c1b84551a09b0dc560829e504194e932d9fc99fff4d1f',
                 'palace':'f722cfe605581016b4174b212824f4c8a7dc97e7f858689bc3c4dace89a60759'}
checks['original-routes-preserved']=all(sha(ROOT/'routes'/s/'GAME.CGO')==v for s,v in original_routes.items())
checks['remaster-routes']=all(sha(ROOT/'routes/remaster'/s/'GAME.CGO')==v for s,v in runtime['routes'].items())
checks['active-core-is-v3-palace']=sha(ROOT/'data/out/jak3/iso/GAME.CGO')==runtime['routes']['palace']
def frames(profile,prefix):
    paths=list((ROOT/'profiles'/profile/'OpenGOAL/jak3/screenshots').glob(prefix+'*.png'))
    return sorted(paths,key=lambda p:int(re.search(r'(\d+)\.png$',p.name)[1]))
groups={'lava':frames('v3-arena','lava-final-'),
        'fountains':frames('remaster-palace','v3-fountain-'),
        'contact':frames('remaster-palace','v3-contact-'),
        'landing':frames('remaster-palace','v3-landing-'),
        'shore':frames('remaster-palace','v4-shore-')}
measurements={}
for name,paths in groups.items():
    checks[name+'-captures']=len(paths)==(16 if name=='shore' else 12)
    images=[Image.open(p).convert('RGB') for p in paths]
    for im in images: assert im.size==(1920,1080)
    area={'lava':(250,580,430,700),'fountains':(1420,540,1530,770),'contact':(870,770,1060,990),'landing':(870,770,1100,990),'shore':(180,830,380,1060)}[name]
    diff=ImageChops.difference(images[0].crop(area),images[-1].crop(area))
    measurements[name]={'frames':len(images),'region':area,'mean_abs_rgb_change':ImageStat.Stat(diff).mean,
                        'note':'Camera/Jak may move during capture; not a fluid-only motion metric.' if name in ('contact','landing') else 'Native frames, same scene camera.'}
    resized=[im.resize((960,540),Image.Resampling.LANCZOS).quantize(colors=192) for im in images]
    resized[0].save(ROOT/'liquids-v3'/f'{name}-motion.gif',save_all=True,append_images=resized[1:],
                    duration={'lava':333,'fountains':200,'contact':167,'landing':133,'shore':200}[name],loop=0,disposal=2)
report={'date':'2026-09-16','checks':checks,'all_checks_pass':all(checks.values()),
        'runtime':runtime,'files_per_variant':len(files),'motion':measurements,
        'routes':{s:sha(ROOT/'routes'/s/'GAME.CGO') for s in ('arena','palace')},
        'remaster_routes':runtime['routes'],
        'scope':'Palace basins/fountains and starting arena lava only.',
        'shore_correction':'Removed permanent bank foam and bank mesh oscillation. Subtle irregular normal disturbance uses real rock contours. Removed vertical bank-film branch that interrupted waterfalls at basin heights. Native shore and wider fountain views inspected.',
        'interaction_test':'Jak moved through genuine water collision and landed under game gravity; native contact and landing logs plus screenshots recorded. Movement/initial fall position were scripted through GOAL. Original particles, ripple meshes and wake trail are suppressed for Jak in the palace volumes.',
        'limitations':['Deep-water swimming not exercised in these shallow palace basins.',
                       'Screen-space reflections lack off-screen scene geometry.',
                       'No full-game playthrough or formal performance benchmark.',
                       'Native screenshot buffer warning also occurs on the official comparison.']}
(ROOT/'liquids-v3/validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'all_checks_pass':report['all_checks_pass'],'checks':checks,'motion':measurements},indent=2))
assert report['all_checks_pass']
