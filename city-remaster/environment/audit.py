"""Independent FR3 audit. Run using Blender's Python (zstandard), no writes to inputs."""
import argparse, sys
from common import *
sys.path.insert(0,str(CITY))
from compare_market import read_level

def audit_one(before_path,after_path,patch_path):
    patch=read(patch_path);before=read_level(Path(before_path));after=read_level(Path(after_path))
    checks={'pinned_source':patch['source_fr3']['sha256']==before['sha256'],
        'pinned_size':patch['source_fr3']['bytes']==Path(before_path).stat().st_size,
        'level_identity':before['level']==after['level']==patch['level'],
        'no_geometry_requested':not patch['remove'] and not patch['add'],
        'no_texture_append_requested':not patch.get('new_textures'),
        'entire_static_region_identical':before['static_bytes']==after['static_bytes'],
        'entire_merc_tail_identical':before['data'][before['merc_start']:]==after['data'][after['merc_start']:],
        'texture_count_identical':len(before['textures'])==len(after['textures'])}
    allowed={t['name']:t for t in patch['textures']}
    checks['unique_allowlist']=len(allowed)==len(patch['textures']) and bool(allowed)
    changed=[];seen=set();errors=[]
    for i,(old,new) in enumerate(zip(before['textures'],after['textures'])):
        if old['name'] not in allowed:
            if before['texture_bytes'][i]!=after['texture_bytes'][i]:errors.append(f'Unselected texture changed: {i}/{old["name"]}')
            continue
        target=allowed[old['name']];seen.add(old['name'])
        for key in ('name','page','combo','pool'):
            if old[key]!=new[key]:errors.append(f'Metadata changed: {i}/{key}')
        pixels=Path(target['rgba_file']).read_bytes()
        if len(pixels)!=target['width']*target['height']*4:errors.append(f'Bad declared raw size: {old["name"]}')
        if new['width']!=target['width'] or new['height']!=target['height'] or new['rgba_sha256']!=digest(pixels):errors.append(f'Wrong pixels/dimensions: {i}/{old["name"]}')
        if before['texture_bytes'][i]!=after['texture_bytes'][i]:changed.append({'index':i,'name':old['name'],'page':old['page'],'before':old,'after':new})
    checks['all_named_targets_present']=seen==set(allowed)
    checks['only_exact_allowed_pixels_changed']=not errors
    checks['visible_pixel_change']=bool(changed)
    result={'status':'passed' if all(checks.values()) else 'failed','checks':checks,'errors':errors,
        'level':before['level'],'before':str(before_path),'after':str(after_path),'patch':str(patch_path),
        'before_sha256':before['sha256'],'after_sha256':after['sha256'],'patch_sha256':sha(patch_path),
        'static_sha256':digest(before['static_bytes']),'merc_tail_sha256':digest(before['data'][before['merc_start']:]),
        'texture_count':len(before['textures']),'changed_textures':changed,'native_visual_validation':False}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path);parser.add_argument('--inventory',type=Path);parser.add_argument('--input',action='append',type=Path)
    args=parser.parse_args()
    if args.inventory:
        output={}
        for p in args.input or []:
            level=read_level(p);output[level['level']]={'sha256':level['sha256'],'textures':level['textures']}
        write(args.inventory,output);return
    assert args.stage
    plan=read(args.stage/'stage.json');reports=[]
    for row in plan['levels']:
        result=audit_one(row['before'],row['candidate'],row['patch']);write(args.stage/(row['level']+'-audit.json'),result);reports.append(result)
    passed=all(r['status']=='passed' for r in reports)
    result={'status':'passed' if passed else 'failed','stage_sha256':sha(args.stage/'stage.json'),
        'levels':reports,'auditor_sha256':sha(Path(__file__)),'parser_sha256':sha(CITY/'compare_market.py')}
    write(args.stage/'audit.json',result);print(json.dumps({'status':result['status'],'changed':[len(r['changed_textures']) for r in reports]},indent=2))
    if not passed:raise SystemExit(1)

if __name__=='__main__':main()

