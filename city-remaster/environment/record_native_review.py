"""Record inspected native captures, separately from binary-preservation audits."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
shots=ROOT/'profiles/remaster-palace/OpenGOAL/jak3/screenshots'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
items={
 'city-panorama-before-v1':'Baseline before citywide textures, thirteen further palms and cloud changes.',
 'city-panorama-after-v1':'First cloud pass rejected: broad uniform cream shapes.',
 'city-panorama-after-v2':'Same fixed camera: citywide surfaces and full palms visible, cloud interiors improved.',
 'city-center-after-v1':'Rejected display regression: procedural ocean covered a dry WCA street.',
 'city-center-dry-v2':'Same WCA start: native coast mask removes water from street.',
 'city-coast-mask-swim-v2':'Coastal water retained; live target-swim-stance and touch-water=true confirmed at (1647,-430).',
}
record={'reviewed_utc':datetime.now(timezone.utc).isoformat(),
 'runtime_sha256':sha(ROOT/'runtime/liquids-v3/gk.exe'),
 'captures':[{'name':n,'path':str(shots/(n+'.png')),'sha256':sha(shots/(n+'.png')),'observation':v} for n,v in items.items()],
 'scope':'First broad Spargus environment pass, WCA/WCB/WASWIDE.',
 'limits':['No complete traversal, collision, cutscene or performance benchmark.',
 'Building geometry, cactus geometry, all grass and regional fire are not complete.',
 'Cloud rendering still uses the native dome with an animated volume-derived mask.',
 'This records agent inspection, not user approval.']}
(HERE/'native-review.json').write_text(json.dumps(record,indent=2)+'\n')
print('Recorded six inspected native captures.')
