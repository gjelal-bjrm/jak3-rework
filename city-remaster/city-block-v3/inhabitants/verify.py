"""Independent checks on exported actor bytes, poses, materials and provenance."""
from pathlib import Path
import json,struct,math,hashlib
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def delta(a,b):return tuple(x-y for x,y in zip(a,b))
def norm(a):return math.sqrt(sum(x*x for x in a))
def area(a,b,c):
    u=delta(b,a);v=delta(c,a)
    return norm((u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))*.5
def main():
    sources=json.loads((HERE/'source-manifest.json').read_text());reports=[]
    for name in ('sitting-male','conversing-male','conversing-female'):
        j=json.loads((HERE/(name+'.json')).read_text());raw=(HERE/j['binary']).read_bytes()
        source=sources[j['source_sex']];n=j['vertex_count'];count=j['frame_count']
        vertices=list(struct.iter_unpack('<12f',raw));frames=[vertices[i*n:(i+1)*n]for i in range(count)]
        checks={
          'source_native_glb_hash':sha(Path(source['source']).read_bytes())==source['source_sha256'],
          'selected_skin_source_hash':sha((HERE/(j['source_sex']+'-selected.glb')).read_bytes())==source['selected_sha256'],
          'binary_hash':sha(raw)==j['binary_sha256'],
          'complete_float32_frames':len(raw)==n*count*48 and count==4 and n%3==0,
          'all_values_finite':all(math.isfinite(x)for v in vertices for x in v),
          'normals_unit':all(abs(norm(v[3:6])-1)<.00001 for v in vertices),
          'constant_uv_and_colour':all(a[6:]==b[6:]for frame in frames[1:]for a,b in zip(frames[0],frame)),
          'texture_bytes_preserved':all(sha((HERE/d['texture']).read_bytes())==d['texture_sha256']for d in j['draws']),
          'draws_cover_whole_frame':sum(d['count']for d in j['draws'])==n and j['draws'][0]['first']==0 and
            all(a['first']+a['count']==b['first']for a,b in zip(j['draws'],j['draws'][1:])),
          'feet_at_floor_all_frames':all(abs(min(v[1]for v in f))<1e-5 for f in frames),
          'below_2_1_metres':max(v[1]for v in vertices)<2.1,
          'normalised_material_response':all(0<=x<=1.01 for v in vertices for x in v[8:11]) and all(v[11]==2 for v in vertices),
          'not_t_pose':all(abs(p['Lhand'][0])<.6 and abs(p['Rhand'][0])<.6 for p in j['joint_positions_by_frame']),
          'both_feet_remain_planted':all(p['Lankle']==j['joint_positions_by_frame'][0]['Lankle'] and
              p['Rankle']==j['joint_positions_by_frame'][0]['Rankle']for p in j['joint_positions_by_frame'])}
        differences=[max(norm(delta(a[:3],b[:3]))for a,b in zip(frames[0],f))for f in frames[1:]]
        checks['visible_small_pose_motion']=.01<max(differences)<.13
        old_areas=[area(*[v[:3]for v in frames[0][i:i+3]])for i in range(0,n,3)]
        new_degenerate=0
        for frame in frames[1:]:
            new_degenerate+=sum(a>1e-7 and area(*[v[:3]for v in frame[i:i+3]])<1e-8 for a,i in zip(old_areas,range(0,n,3)))
        checks['no_new_zero_area_triangles']=new_degenerate==0
        reports.append({'actor':name,'checks':checks,'all_passed':all(checks.values()),
                        'max_pose_change_m':differences,'new_degenerate_triangles':new_degenerate,
                        'source_zero_area_triangles':sum(a<1e-8 for a in old_areas),'native_game_validation':False})
    output={'status':'passed'if all(r['all_passed']for r in reports)else'failed','actors':reports,
       'method':'Independent float32 binary parsing; source/material hashes; draw coverage; unit normals; planted feet; bounded nonzero pose motion',
       'native_game_validation':False}
    (HERE/'validation.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
    assert output['status']=='passed'
if __name__=='__main__':main()
