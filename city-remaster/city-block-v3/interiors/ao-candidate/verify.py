from pathlib import Path
import json,struct,math,hashlib
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def length(v):return math.sqrt(sum(x*x for x in v))
def area(a,b,c):
    u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
    return .5*length((u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))
reports=[]
for layout in ('lounge','conversation'):
    old=json.loads((HERE.parent/(layout+'.json')).read_text());new=json.loads((HERE/(layout+'.json')).read_text())
    oldraw=(HERE.parent/old['binary']).read_bytes();newraw=(HERE/new['binary']).read_bytes()
    before=list(struct.iter_unpack('<12f',oldraw));after=list(struct.iter_unpack('<12f',newraw))
    old_area=[sum(area(*before[i:i+3])for i in range(d['first'],d['first']+d['count'],3))for d in old['draws']]
    new_area=[sum(area(*after[i:i+3])for i in range(d['first'],d['first']+d['count'],3))for d in new['draws']]
    checks={
      'source_hash_unchanged':sha(oldraw)==old['sha256']==new['vertex_ao']['source_sha256'],
      'candidate_hash':sha(newraw)==new['sha256'],
      'palette_and_materials_unchanged':old['materials']==new['materials'],
      'draw_material_order_unchanged':[d['material']for d in old['draws']]==[d['material']for d in new['draws']],
      'surface_area_unchanged_per_material':all(abs(a-b)<max(1e-5,a*1e-5)for a,b in zip(old_area,new_area)),
      'bounds_unchanged':all(abs(fn(v[i]for v in before)-fn(v[i]for v in after))<1e-6 for i in range(3)for fn in(min,max)),
      'finite':all(math.isfinite(x)for v in after for x in v),
      'unit_normals':all(abs(length(v[3:6])-1)<1e-5 for v in after),
      'same_authored_uv_mapping':all(abs(v[6]-(v[0]*.7+v[2]*.23))<2e-6 and abs(v[7]-(v[1]*.7+v[2]*.6))<2e-6 for v in after),
      'neutral_ao_rgb_no_hue_change':all(v[8]==v[9]==v[10] and .599<=v[8]<=1 for v in after),
      'alpha_preserved':all(v[11]==1 for v in after),
      'draws_cover_buffer':sum(d['count']for d in new['draws'])==new['vertex_count']==len(after)}
    reports.append({'layout':layout,'checks':checks,'passed':all(checks.values())})
report={'status':'passed'if all(r['passed']for r in reports)else'failed','rooms':reports,'deployed':False}
(HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['status']=='passed'
