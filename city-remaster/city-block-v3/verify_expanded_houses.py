"""Bounded R4: exact house1 restoration and four street-facing apertures."""
from pathlib import Path
from collections import Counter
import json
import math
import struct

def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def group(face):return(face.get('tree_type','tie'),face['geom'],face['tree'],face['draw'],face['group'])
def key(face):return tuple(face[k]for k in('tree_type','geom','tree','draw','stream_index'))


def anchors(entry,root,check,matches):
    architecture=root/'architecture';directory=root/'architecture-expanded-r4'
    original=load(architecture/'installed.json')
    matches(architecture/'window-anchors.json',original['window_anchors_sha256'])
    historical=load(architecture/'window-anchors.json')
    check(Path(entry['window_anchors']).resolve()==(directory/'window-anchors.json').resolve(),
          'Expanded house anchors are outside the exact R4 source')
    matches(directory/'window-anchors.json',entry['window_anchors_sha256'])
    result=load(directory/'window-anchors.json');specs=load(directory/'new-window-specs.json')
    proof=load(entry['restoration_validation'])
    matches(directory/'new-window-specs.json',proof['new_window_specs_sha256'])
    check(result==historical+specs and len(historical)==5 and len(specs)==4 and
          [a['id']for a in specs]==['wca-house-'+region+'-room'for region in('east','west','low','north')]and
          [a['building_native_instance']for a in specs]==[0,4,58,3]and
          all(a['inhabited']is True and a['tree']==1 and a['level']=='wascitya'for a in specs),
          'R4 does not preserve the five historical anchors and exactly four selected street houses')
    return result


def verify(entry,root,check,matches):
    directory=root/'architecture-expanded-r4';architecture=root/'architecture'
    parent_path=architecture/'revision-003/installed.json';parent=load(parent_path)
    check(entry['path']=='out/jak3/fr3/wascitya.fr3'and entry['base_sha256']==parent['output_sha256']and
          Path(entry['base_path']).resolve()==Path(parent['output_path']).resolve()and
          Path(entry['parent_record']).resolve()==parent_path.resolve(),
          'Expanded houses are not descended from the exact installed R3 geometry')
    matches(parent_path,entry['parent_record_sha256'])
    for field in('window_anchors','author_report','geometry_validation','opening_validation','bvh_coverage',
                 'restoration_validation','street_visibility_validation'):
        matches(Path(entry[field]),entry[field+'_sha256'])
    for field in('base_path','output_path','patch'):
        matches(Path(entry[field]),entry[{'base_path':'base_sha256','output_path':'output_sha256','patch':'patch_sha256'}[field]])
    windows=anchors(entry,root,check,matches);patch=load(entry['patch']);author=load(entry['author_report'])
    check(patch['level']=='wascitya'and patch['source_fr3']['sha256']==entry['base_sha256']and
          patch.get('preserve_bvh')is True and not patch.get('textures')and not patch.get('new_textures')and
          all('texture'not in face for face in patch['add']),
          'Expanded houses change textures, another map or the native BVH')
    removed={};added={}
    for lod in range(4):
        wall=12 if lod<3 else 11;wood=19 if lod<3 else 18
        for draw,r,a in ((9,(71,71,69,47)[lod],(1563,1563,1561,1523)[lod]),(wall,2,10)):
            removed[('tie',lod,1,draw,1)]=r;added[('tie',lod,1,draw,1)]=a
        for native_group,r,a,b in ((0,2,12,460),(4,4,20,552)):
            removed[('tie',lod,1,wood,native_group)]=r
            added[('tie',lod,1,wood,native_group)]=a;added[('tie',lod,1,9,native_group)]=b
        for native_group,count in((12,562),(3,470)):
            removed[('tie',lod,1,9,native_group)]=2;removed[('tie',lod,1,wall,native_group)]=2
            added[('tie',lod,1,9,native_group)]=count;added[('tie',lod,1,wall,native_group)]=10
    check(Counter(group(face)for face in patch['remove'])==removed and Counter(group(face)for face in patch['add'])==added,
          'R4 changes geometry beyond the exact restored window and four local street openings')
    check(len({key(face)for face in patch['remove']})==len(patch['remove'])==322 and len(patch['add'])==14634,
          'R4 repeats a removal or differs from its reviewed triangle counts')
    matches(directory/'author.py',author['author_sha256'])
    check(author['source_fr3']['sha256']==entry['base_sha256']and author['house_count']==6 and
          author['faces_removed']==322 and author['faces_added']==14634,
          'R4 author report refers to a different six-house patch')
    geometry=load(entry['geometry_validation'])
    check(geometry['passed']is True and geometry['source_fr3']['sha256']==entry['base_sha256']and
          geometry['patch_sha256']==entry['patch_sha256']and geometry['faces_removed']==322 and
          geometry['faces_added']==14634 and geometry['degenerate_float32']==geometry['bad_normals']==geometry['bad_palettes']==0,
          'Expanded geometry is degenerate or lacks a matching finite export proof')
    coverage=load(entry['bvh_coverage'])
    check(coverage['status']=='passed'and coverage['source_sha256']==entry['base_sha256']and
          coverage['patch_sha256']==entry['patch_sha256']and coverage['outside_vertices']==0 and
          coverage['all_added_vertices_inside_native_spheres']is True and coverage['source_modified']is False and
          coverage['vertices_checked']==14634*3 and
          {('tie',g['geom'],g['tree'],g['draw'],g['group'])for g in coverage['groups']}==set(added),
          'Expanded windows escape their unchanged native visibility spheres')
    openings=load(entry['opening_validation'])
    expected={'Every removal exists in exact source','All removed original positions match',
              'No duplicate native removals','No nonfinite vertices or normals'}|{
              window['id']+' LOD'+str(lod)+' actual 3x3 rays clear'for window in windows for lod in range(4)}
    check(openings['passed']is True and openings['source_sha256']==entry['base_sha256']and
          openings['patch_sha256']==entry['patch_sha256']and {row['name']for row in openings['checks']}==expected and
          all(row['passed']is True and not row.get('hits')for row in openings['checks']),
          'Expanded houses obstruct an authored window or omit a retained opening check')
    restoration=load(entry['restoration_validation'])
    expected_restoration={'house1_exact_R2_positions_uv_and_palette','restoration_face_count_6250',
        'removed_R3_faces_266','house2_geometry_unselected','five_historical_anchors_exact',
        'four_new_anchors_exact','six_distinct_houses','restored_faces_in_original_R3_removal_order'}
    check(restoration['status']=='passed'and set(restoration['checks'])==expected_restoration and
          all(v is True for v in restoration['checks'].values())and
          restoration['source_sha256']==entry['base_sha256']and restoration['patch_sha256']==entry['patch_sha256']and
          restoration['window_anchors_sha256']==entry['window_anchors_sha256']and
          restoration['r3_patch_sha256']==parent['patch_sha256']and
          restoration['restored_house1_triangle_count']==restoration['expected_house1_triangle_count']==17734,
          'R4 restoration does not reproduce the accepted R2 house and its original aperture')
    r2_path=root/'architecture-single-window-r3/native.json'
    matches(r2_path,restoration['r2_native_export_sha256'])
    r2={key(face):face for face in load(r2_path)['faces']};previous=load(parent['patch'])
    restored=[face for face in patch['add']if face['group']==1]
    check(len(restored)==len(previous['remove'])==6250,
          'R4 restores a different house1 triangle selection')
    for face,old_ref in zip(restored,previous['remove']):
        original=r2[key(old_ref)]
        check(group(face)==group(original)and all(
            a['p']==b['p']and a['uv']==b['uv']and a['color_indices']==[b['color']]*3 and a['color_weights']==[1,0,0]
            for a,b in zip(face['vertices'],original['vertices'])),
            'Restored house1 face loses an original R2 position, UV or palette index')
    def rounded(point):return tuple(struct.unpack('<3f',struct.pack('<3f',*point)))
    check(Counter((group(face),tuple(rounded(p)for p in face['original_positions']))
                  for face in patch['remove']if face['group']==1)==
          Counter((group(face),tuple(rounded(v['p'])for v in face['vertices']))for face in previous['add']),
          'R4 removes a house1 triangle outside the exact R3 closing patch')
    street=load(entry['street_visibility_validation']);specs={w['id']:w for w in windows[5:]}
    check(street['status']=='passed'and street['source_sha256']==entry['base_sha256']and
          street['patch_sha256']==entry['patch_sha256']and street['new_window_specs_sha256']==restoration['new_window_specs_sha256']and
          street['occluders_excluded']==[]and len(street['windows'])==16 and
          set(street['checks'])=={name+' LOD'+str(lod)+' street sight lines'for name in specs for lod in range(4)}and
          all(value is True for value in street['checks'].values()),
          'Street visibility excludes native blockers or omits one of four house/LOD combinations')
    matches(directory/'native.json',street['native_export_sha256'])
    for row in street['windows']:
        window=specs[row['id']]
        check(row['lod']in range(4)and row['camera_m']==window['street_camera']and
              math.dist(row['target_m'],window['center'])<1e-5 and row['ground_y']==window['street_ground_y']and
              len(row['rays'])==9 and {tuple(ray['sample'])for ray in row['rays']}==
              {(a,b)for a in(-.23,0,.23)for b in(-.23,0,.23)}and
              all(ray['passed']is True and ray['hit_m']is None and ray['face']is None for ray in row['rays']),
              'A new house is not visible from its recorded street camera through all nine aperture samples')
    return windows
