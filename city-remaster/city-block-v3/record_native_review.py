"""Record the evidence inspected by the parent; does not imply user approval."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 screen=R/'profiles/remaster-palace/OpenGOAL/jak3/screenshots'
 names=['city-window-corner-before-v3','city-window-corner-after-v3',
        'city-lounge-native-v3','city-conversation-native-v3',
        'city-conversation-final-pose-a','city-conversation-final-pose-b',
        'city-house-silhouette-native-v3','city-buildings-gameplay-v3',
        'city-house2-corrected-native-v3','city-house2-corrected-open-angle-v3',
        'city-fire-wcb-native-v3-a','city-fire-wcb-native-v3-b']
 screenshots={}
 for name in names:
  p=screen/(name+'.png');assert p.is_file(),name
  screenshots[name]={'path':str(p),'sha256':sha(p)}
 package=R/'models-v2/package-validation.json';p=json.loads(package.read_text())
 assert p['passed'],p['errors']
 log=R/'remaster-runtime.log';text=log.read_text(errors='replace')
 assert 'muted output; every stereo sample is cleared before playback'in text
 assert 'City interiors live:'in text and 'City fire live:'in text
 evidence=H/'runtime-reviewed.log';evidence.write_bytes(log.read_bytes())
 report={'status':'native_views_reviewed','user_approval':False,
   'scope':'Two WCA pilot houses, five openings and furnished rooms; city fire in WCA/WCB',
   'runtime_sha256':sha(R/'runtime/liquids-v3/gk.exe'),
   'data_wca_sha256':sha(R/'data/out/jak3/fr3/wascitya.fr3'),
   'data_wcb_sha256':sha(R/'data/out/jak3/fr3/wascityb.fr3'),
   'package_report':str(package),'package_report_sha256':sha(package),
   'runtime_log':str(evidence),'runtime_log_sha256':sha(evidence),'screenshots':screenshots,
   'observations':[
    'Actual facade openings and furniture visible from multiple native camera angles.',
    'House2 ornaments checked from two native angles after R2 street-facing correction.',
    'Neutral room contact shading inspected in native lounge and conversation views.',
    'Native male/female inhabitants have posed meshes and looping interpolation.',
    'Native conversation capture changes 5175 pixels in the actor rectangle between two frames.',
    'Normal third-person camera restored at the first house; movement remains native.',
    'New city fire visible and anchored in a WCB vessel, and in WCA wider views.',
    'Corrected generic-obs survived boot WCA-to-palace and subsequent WCA/WCB transitions.'
   ],
   'limitations':[
    'Two pilot buildings only; surrounding city and complete AAA finish remain unfinished.',
    'Decorative inhabitants use original NPC models; no interior gameplay AI or access.',
    'Open apertures currently have no reflective glass pane.',
    'No exhaustive gameplay/cutscene/performance audit; NPC sand and grass deferred.'
   ]}
 (H/'native-review.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 print('Recorded',len(screenshots),'inspected native captures; package checks',p['checks'])
if __name__=='__main__':main()
