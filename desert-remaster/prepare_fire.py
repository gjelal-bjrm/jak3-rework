"""Record the original palace fire actors for the first remaster fire test."""
from pathlib import Path
import json, collections
ROOT=Path(__file__).resolve().parents[1]
actors=json.loads((ROOT/'data/decompiler_out/jak3/entities/waspala-actors.json').read_text())
groups={'group-waspala-wallfire':2731,'group-waspala-hanging-fire':2736,'group-waspala-crucible-fire':2739}
fires=[]
for actor in actors:
    group=actor['lump'].get('art-name','')
    if group not in groups:continue
    fires.append({'aid':actor['aid'],'name':actor['lump'].get('name'),
                  'group':group,'flame_particle':groups[group],'trans_m':actor['trans'],
                  'scale':actor['lump'].get('scale')})
report={'status':'Reference inventory only; original fire still displayed.',
        'source':'data/decompiler_out/jak3/entities/waspala-actors.json',
        'counts':dict(collections.Counter(a['group'] for a in fires)), 'actors':fires}
(ROOT/'desert-remaster/palace-fire.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['counts'],indent=2))
