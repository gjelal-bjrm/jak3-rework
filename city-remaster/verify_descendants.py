"""Read-only provenance checks called by models-v2/verify_package.py after packaging."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import struct

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'city-remaster'


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
def all_passed(proof):return proof.get('status')=='passed' and bool(proof.get('checks')) and all(v is True for v in proof['checks'].values())


def mesh_descendant(record_path,heads,check,matches,history):
    if not record_path.exists():return
    entry=load(record_path)
    check(entry.get('status') in (None,'active','installed'),'Mesh descendant must describe an installed candidate')
    relative=entry['path']
    check(relative in heads,'Mesh descendant outside tracked city levels')
    check(entry['base_sha256']==heads.get(relative),'Mesh descendant breaks predecessor hash chain')
    for key,hash_key in [('base_path','base_sha256'),('output_path','output_sha256'),('patch','patch_sha256')]:
        matches(Path(entry[key]),entry[hash_key])
    for key in ('parent_record','author_report'):
        if key+'_sha256'in entry:matches(Path(entry[key]),entry[key+'_sha256'])
    proof_path=Path(entry['preservation_report']);proof=load(proof_path)
    if 'preservation_report_sha256'in entry:matches(proof_path,entry['preservation_report_sha256'])
    check(all_passed(proof),'Native mesh preservation audit did not pass all checks')
    check(proof['before_sha256']==entry['base_sha256'] and proof['after_sha256']==entry['output_sha256'] and
          proof['patch_sha256']==entry['patch_sha256'],'Native mesh audit refers to another base/candidate/patch')
    matches(Path(proof['native_report']),proof['native_report_sha256'])
    native=load(proof['native_report'])
    check(native['merc_unchanged'] and native['collision_unchanged'] and native['hfrag_unchanged'] and
          all(t['unchanged']for t in native['textures']),'Native mesh audit does not preserve protected regions/textures')
    for tree in native['tie']:
        check(tree['wind_instances_unchanged'] and tree['wind_groups_unchanged'] and
              tree['static_triangles']['unselected_unchanged'] and tree['wind_triangles']['unselected_unchanged'],
              'Native mesh descendant changed unselected geometry or wind instances')
    heads[relative]=entry['output_sha256']
    history.append({'kind':'native_mesh','manifest':str(record_path),'path':relative,
                    'base_sha256':entry['base_sha256'],'output_sha256':entry['output_sha256']})


def environment_descendant(record_path,heads,check,matches,history,seen=None):
    if not record_path.exists():return
    seen=set()if seen is None else seen
    key=str(record_path.resolve());check(key not in seen,'Cycle in environment provenance')
    if key in seen:return
    seen.add(key)
    record=load(record_path)
    if record.get('status')=='rolled_back':
        proof=load(record['rollback_report'])
        for row in record['levels']:
            check(row['output_sha256']==heads.get(row['path']),'Rolled back environment does not restore current predecessor')
            matches(Path(row['source_path']),row['output_sha256'])
            check(proof['restored'][row['path']]==row['output_sha256'],'Rollback record mismatch')
        return
    check(record.get('status')=='active','Environment installation is not active')
    stage=Path(record['stage']);plan_path=stage/'stage.json'
    previous=stage/'previous-environment-installed.json'
    if previous.is_file():environment_descendant(previous,heads,check,matches,history,seen)
    matches(plan_path,record['stage_sha256']);plan=load(plan_path)
    matches(Path(record['audit']),record['audit_sha256']);audit=load(record['audit'])
    check(audit['status']=='passed' and audit['stage_sha256']==record['stage_sha256'],'Environment audit/stage mismatch')
    matches(HERE/'environment/audit.py',audit['auditor_sha256'])
    matches(HERE/'compare_market.py',audit['parser_sha256'])
    matches(Path(plan['prepared']),record['prepared_sha256'])
    check(plan['prepared_sha256']==record['prepared_sha256'],'Environment prepared manifest mismatch')
    prepared=load(plan['prepared'])
    matches(stage/'generation-manifest.json',prepared['manifest_sha256'])
    materials={m['name']:m for m in prepared['materials']}
    check(len(materials)==len(prepared['materials']) and bool(materials),'Duplicate/empty environment materials')
    for mat in materials.values():
        matches(Path(mat['rgba_file']),mat['rgba_sha256'])
        check(Path(mat['rgba_file']).stat().st_size==mat['width']*mat['height']*4,'Wrong immutable RGBA byte size')
        check(mat['native_alpha']==128 and bool(mat['master_sha256']) and bool(mat['rgb_sha256']),
              'Environment preparation lost native alpha or master provenance')
    for protected in plan['protected_variants']:matches(Path(protected['path']),protected['sha256'])
    proofs={p['level']:p for p in audit['levels']}
    rows={p['level']:p for p in plan['levels']}
    check(set(proofs)==set(rows)=={r['level']for r in record['levels']} and
          {'wascitya','wascityb'}<=set(rows)<= {'wascitya','wascityb','waswide'},
          'Environment level inventory differs')
    check(record['parent_records']==plan['parent_records'],'Environment parent snapshots differ from audited stage')
    for row in record['levels']:
        proof=proofs[row['level']];staged=rows[row['level']]
        check(all(row.get(k)==v for k,v in staged.items()),'Installed environment row differs from audited plan')
        relative=row['path'];parent=row['parent']
        check(row['base_sha256']==heads.get(relative),'Environment level breaks predecessor hash chain')
        check(parent['path']==relative and parent['output_sha256']==row['base_sha256'],'Environment row parent mismatch')
        # Match the exact predecessor record snapshot. A previous environment
        # record is allowed to live in this stage's immutable rollback backup.
        snapshots=[p for p in plan['parent_records']if p['path']==parent['record'] and p['sha256']==parent['record_sha256']]
        check(len(snapshots)==1,'Environment parent lacks the audited identity snapshot')
        if snapshots:
            value=snapshots[0]['value'];entries=value.get('levels',[value])
            check(any(e.get('path')==relative and e.get('output_sha256')==row['base_sha256']for e in entries),
                  'Environment parent snapshot does not contain the predecessor output')
            parent_path=Path(parent['record'])
            if parent_path.resolve()==(HERE/'environment/installed.json').resolve():
                matches(previous,parent['record_sha256'])
            else:matches(parent_path,parent['record_sha256'])
        matches(Path(row['before']),row['base_sha256']);matches(Path(row['candidate']),row['output_sha256'])
        matches(Path(row['patch']),row['patch_sha256'])
        check(all_passed(proof) and proof['before_sha256']==row['base_sha256'] and
              proof['after_sha256']==row['output_sha256'] and proof['patch_sha256']==row['patch_sha256'],
              'Environment preservation proof refers to another input/output')
        check(proof['static_sha256']==row['preserved_static_sha256'] and
              proof['merc_tail_sha256']==row['preserved_merc_tail_sha256'],
              'Environment geometry/Merc preservation digests differ')
        patch=load(row['patch'])
        check(not patch['remove'] and not patch['add'] and not patch.get('new_textures') and
              patch['source_fr3']['sha256']==row['base_sha256'],'Environment patch is not a texture-only descendant')
        selected={t['name']:t for t in patch['textures']}
        check(set(selected)==set(row['materials']),'Environment texture selection differs from plan')
        for name,texture in selected.items():
            mat=materials[name]
            check(all(texture[k]==mat[k]for k in ('name','width','height','rgba_file')),
                  'Environment patch differs from immutable prepared pixels')
        for changed in proof['changed_textures']:
            check(changed['name']in selected,'Audit records an undeclared texture change')
            mat=materials[changed['name']]
            check(changed['after']['rgba_sha256']==mat['rgba_sha256'] and
                  changed['after']['width']==mat['width'] and changed['after']['height']==mat['height'],
                  'Changed native texture pixels do not match approved encoding')
        heads[relative]=row['output_sha256']
        history.append({'kind':'environment_textures','manifest':str(record_path),'path':relative,
                        'base_sha256':row['base_sha256'],'output_sha256':row['output_sha256']})


def verify_city_chain(heads,check,matches):
    history=[]
    baseline_path=HERE/'environment/baselines/waswide/baseline.json'
    if baseline_path.exists():
        baseline=load(baseline_path)
        check(baseline['level']=='waswide' and baseline['path']=='out/jak3/fr3/waswide.fr3' and
              baseline['live_equals_active_original']is True,'WASWIDE baseline is not anchored in original data')
        snapshots=baseline['snapshots']
        check({s['role']for s in snapshots}=={'active_original','live_before'},'WASWIDE baseline snapshots incomplete')
        for snapshot in snapshots:
            matches(Path(snapshot['path']),snapshot['sha256'])
            check(snapshot['sha256']==snapshot['source_sha256']==baseline['output_sha256'],
                  'WASWIDE baseline source/snapshot hashes differ')
            if snapshot['role']=='active_original':matches(Path(snapshot['source_path']),snapshot['source_sha256'])
        check({v['variant']for v in baseline['variants']}=={'original','remaster-v1','remaster'},
              'WASWIDE baseline variants incomplete')
        for variant in baseline['variants']:
            check(variant['sha256']==baseline['output_sha256'],'WASWIDE baseline variants were not identical')
            if variant['variant']!='remaster':matches(Path(variant['path']),variant['sha256'])
        heads[baseline['path']]=baseline['output_sha256']
        history.append({'kind':'original_baseline','manifest':str(baseline_path),'path':baseline['path'],
                        'output_sha256':baseline['output_sha256']})
    mesh_descendant(HERE/'static-installed.json',heads,check,matches,history)
    mesh_descendant(HERE/'environment/foliage/installed.json',heads,check,matches,history)
    environment_descendant(HERE/'environment/installed.json',heads,check,matches,history)
    for level in ('wascitya','wascityb'):
        prior=HERE/'environment/geometry-001'/f'{level}-installed.json'
        revised=HERE/'environment/geometry-002'/f'{level}-installed.json'
        if revised.exists():
            entry=load(revised);old=load(prior)
            matches(prior,entry['replaces_record_sha256'])
            check(Path(entry['replaces_record'])==prior and entry['replaces_output_sha256']==old['output_sha256'],
                  'Revised geometry does not identify the replaced installation')
            check(entry['base_sha256']==old['base_sha256']==heads.get(entry['path']),
                  'Revised geometry is not based on the same verified city ancestor')
            matches(Path(old['output_path']),old['output_sha256'])
            mesh_descendant(revised,heads,check,matches,history)
        else:
            mesh_descendant(prior,heads,check,matches,history)
    architecture_descendant(HERE/'city-block-v3/architecture/installed.json',heads,check,matches,history)
    architecture_ornaments_descendant(HERE/'city-block-v3/architecture/revision-001/installed.json',
                                     heads,check,matches,history)
    architecture_ornaments_reanchor_descendant(HERE/'city-block-v3/architecture/revision-002/installed.json',
                                              heads,check,matches,history)
    architecture_single_window_descendant(HERE/'city-block-v3/architecture/revision-003/installed.json',
                                         heads,check,matches,history)
    architecture_expanded_descendant(HERE/'city-block-v3/architecture/revision-004/installed.json',
                                    heads,check,matches,history)
    return history


def architecture_descendant(record_path,heads,check,matches,history):
    """Two WCA houses plus their two documented window occluders, after geometry002."""
    if not record_path.exists():return
    entry=load(record_path);directory=HERE/'city-block-v3/architecture'
    parent_path=HERE/'environment/geometry-002/wascitya-installed.json'
    parent=load(parent_path);relative='out/jak3/fr3/wascitya.fr3'
    check(entry['path']==relative and entry['base_sha256']==heads.get(relative)==parent['output_sha256'],
          'Pilot architecture must extend the exact installed geometry002 WCA output')
    check(Path(entry['parent_record']).resolve()==parent_path.resolve(),
          'Pilot architecture does not name its exact geometry002 parent')
    matches(parent_path,entry['parent_record_sha256'])
    check(Path(entry['base_path']).resolve()==Path(parent['output_path']).resolve(),
          'Pilot architecture source path differs from the audited geometry002 output')
    for key in ('bvh_coverage','opening_validation','geometry_validation','window_anchors'):
        matches(Path(entry[key]),entry[key+'_sha256'])
    check(Path(entry['window_anchors']).resolve()==(directory/'window-anchors.json').resolve(),
          'Pilot architecture window anchors came from another scene')
    patch=load(entry['patch']);geometry=load(entry['geometry_validation'])
    check(patch['level']=='wascitya'and patch['source_fr3']['sha256']==entry['base_sha256']and
          patch.get('preserve_bvh')is True and not patch.get('textures')and not patch.get('new_textures'),
          'Pilot architecture changes unrelated level/texture data or native BVH')
    allowed=set()
    for lod in range(4):
        for group in (1,2):
            for draw in ((9,12,19,22)if lod<3 else(9,11,18,21)):
                allowed.add(('tie',lod,1,draw,group))
        allowed.add(('tie',lod,0,9,81))
        allowed.add(('tie',lod,0,40 if lod<3 else 38,10))
    selected={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['remove']}
    appended={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['add']}
    check(selected==allowed and appended==allowed,
          'Pilot architecture modifies a draw/group outside the two houses and exact window occluders')
    check(all('texture'not in f for f in patch['add']),
          'Pilot architecture unexpectedly reassigns native textures')
    check(geometry['passed']is True and geometry['patch_sha256']==entry['patch_sha256']and
          geometry['source_fr3']['sha256']==entry['base_sha256']and
          geometry['faces_removed']==len(patch['remove'])and geometry['faces_added']==len(patch['add'])and
          geometry['degenerate_float32']==geometry['bad_normals']==geometry['bad_palettes']==0,
          'Pilot geometry validation does not cover the exact finite exported patch')
    coverage=load(entry['bvh_coverage'])
    check(coverage['status']=='passed'and coverage['source_sha256']==entry['base_sha256']and
          coverage['patch_sha256']==entry['patch_sha256']and coverage['outside_vertices']==0 and
          coverage['all_added_vertices_inside_native_spheres']is True and coverage['source_modified']is False and
          coverage['vertices_checked']==len(patch['add'])*3,
          'Pilot geometry lacks complete coverage by unchanged native culling spheres')
    check({('tie',g['geom'],g['tree'],g['draw'],g['group'])for g in coverage['groups']}==appended and
          all(g['outside_vertices']==0 for g in coverage['groups']),
          'Pilot BVH coverage measured a different group selection')
    openings=load(entry['opening_validation']);anchors=load(entry['window_anchors'])
    expected_rays={a['id']+' LOD'+str(lod)+' actual 3x3 rays clear'for a in anchors for lod in range(4)}
    base_checks={'Every removal exists in exact source','All removed original positions match',
                 'No duplicate native removals','No nonfinite vertices or normals'}
    check(openings['passed']is True and openings['source_sha256']==entry['base_sha256']and
          openings['patch_sha256']==entry['patch_sha256']and
          {c['name']for c in openings['checks']}==expected_rays|base_checks and
          all(c['passed']is True and not c.get('hits')for c in openings['checks']),
          'Pilot openings are not clear in every authored native LOD')
    # Reuse every existing preservation check: original texture bytes, BVH,
    # matrices, palette/vertex prefixes, unselected triangles, collision and Merc.
    mesh_descendant(record_path,heads,check,matches,history)


def architecture_ornaments_descendant(record_path,heads,check,matches,history):
    """First ornament-only revision over the immutable installed pilot houses."""
    if not record_path.exists():return
    entry=load(record_path);relative='out/jak3/fr3/wascitya.fr3'
    parent_path=HERE/'city-block-v3/architecture/installed.json';parent=load(parent_path)
    check(entry['path']==relative and entry['base_sha256']==heads.get(relative)==parent['output_sha256'],
          'Ornament revision must extend the exact installed pilot architecture')
    check(Path(entry['parent_record']).resolve()==parent_path.resolve()and
          Path(entry['base_path']).resolve()==Path(parent['output_path']).resolve(),
          'Ornament revision changed its immutable architecture parent')
    matches(parent_path,entry['parent_record_sha256'])
    for key in ('geometry_validation','bvh_coverage','window_anchors','opening_validation','ornament_validation'):
        matches(Path(entry[key]),entry[key+'_sha256'])
    check(Path(entry['window_anchors']).resolve()==Path(parent['window_anchors']).resolve()and
          entry['window_anchors_sha256']==parent['window_anchors_sha256'],
          'Ornament revision changed window positions or interior alignment')
    patch=load(entry['patch'])
    check(patch['level']=='wascitya'and patch['source_fr3']['sha256']==entry['base_sha256']and
          patch.get('preserve_bvh')is True and not patch.get('textures')and not patch.get('new_textures'),
          'Ornament revision changes unrelated map, textures or native BVH')
    allowed_remove=set();allowed_add=set()
    for lod in range(4):
        plate_draw=40 if lod<3 else 38;remnant_draw=41 if lod<3 else 39
        for group in (4,5,6,7,9):
            key=('tie',lod,0,plate_draw,group)
            allowed_add.add(key);allowed_remove.add(key)
        allowed_remove.add(('tie',lod,0,plate_draw,10))
        for group in (4,5,6):allowed_remove.add(('tie',lod,0,remnant_draw,group))
    selected={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['remove']}
    appended={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['add']}
    check(selected==allowed_remove and appended==allowed_add,
          'Ornament revision changes a group outside the seven plates and their documented remnants')
    removal_ids={(f['geom'],f['tree'],f['draw'],f['group'],f['stream_index'])for f in patch['remove']}
    check(len(removal_ids)==len(patch['remove']),
          'Ornament revision repeats a native triangle removal')
    expected_removed={4:18,5:18,6:36,7:18,9:36,10:59}
    expected_remnants={4:24,5:12,6:12}
    for lod in range(4):
        plate_draw=40 if lod<3 else 38;remnant_draw=41 if lod<3 else 39
        plate_counts=expected_removed if lod<3 else {4:12,5:12,6:24,7:12,9:24,10:39}
        remnant_counts=expected_remnants if lod<3 else {4:20,5:10,6:10}
        check(all(sum(1 for f in patch['remove']if f['geom']==lod and f['draw']==plate_draw and f['group']==group)==count
                  for group,count in plate_counts.items())and
              all(sum(1 for f in patch['remove']if f['geom']==lod and f['draw']==remnant_draw and f['group']==group)==count
                  for group,count in remnant_counts.items()),
              'Ornament revision leaves a partial original plate/remnant or duplicates removals in LOD'+str(lod))
    check(all('texture'not in f for f in patch['add']),
          'Ornament revision reassigns original texture pages')
    # Check the exported float32 triangles themselves: every plaque must be a
    # closed volume, including its back and bevels, with consistent winding.
    for lod in range(4):
        for group in (4,5,6,7,9):
            faces=[f for f in patch['add']if f['geom']==lod and f['group']==group]
            adjacency={};edges={}
            for index,face in enumerate(faces):
                points=[struct.pack('<3f',*v['p'])for v in face['vertices']]
                for point in points:adjacency.setdefault(point,set()).add(index)
                for a,b in zip(points,points[1:]+points[:1]):
                    edge=tuple(sorted((a,b)));counts=edges.setdefault(edge,[0,0])
                    counts[0]+=1;counts[1]+=1 if a<b else -1
            check(all(count==2 and direction==0 for count,direction in edges.values()),
                  'Ornament has an open edge or inconsistent winding in LOD'+str(lod)+' group'+str(group))
            remaining=set(range(len(faces)));components=0
            while remaining:
                pending=[remaining.pop()];components+=1
                while pending:
                    face=faces[pending.pop()]
                    for vertex in face['vertices']:
                        for neighbor in adjacency[struct.pack('<3f',*vertex['p'])]:
                            if neighbor in remaining:remaining.remove(neighbor);pending.append(neighbor)
            check(components==(2 if group in (6,9)else 1),
                  'Ornament revision does not contain the expected seven independent closed plaques')
    geometry=load(entry['geometry_validation'])
    check(geometry['passed']is True and geometry['source_fr3']['sha256']==entry['base_sha256']and
          geometry['patch_sha256']==entry['patch_sha256']and
          geometry['faces_removed']==len(patch['remove'])and geometry['faces_added']==len(patch['add'])and
          geometry['degenerate_float32']==geometry['bad_normals']==geometry['bad_palettes']==0,
          'Ornament geometry proof does not cover the exact finite exported patch')
    coverage=load(entry['bvh_coverage'])
    check(coverage['status']=='passed'and coverage['source_sha256']==entry['base_sha256']and
          coverage['patch_sha256']==entry['patch_sha256']and coverage['outside_vertices']==0 and
          coverage['all_added_vertices_inside_native_spheres']is True and coverage['source_modified']is False and
          coverage['vertices_checked']==len(patch['add'])*3,
          'Ornament vertices escape their unchanged native culling spheres')
    check({('tie',g['geom'],g['tree'],g['draw'],g['group'])for g in coverage['groups']}==appended and
          all(g['outside_vertices']==0 for g in coverage['groups']),
          'Ornament BVH proof covers a different group selection')
    openings=load(entry['opening_validation']);anchors=load(entry['window_anchors'])
    expected_rays={a['id']+' LOD'+str(lod)+' actual 3x3 rays clear'for a in anchors for lod in range(4)}
    base_checks={'Every removal exists in exact source','All removed original positions match',
                 'No duplicate native removals','No nonfinite vertices or normals'}
    check(openings['passed']is True and openings['source_sha256']==entry['base_sha256']and
          openings['patch_sha256']==entry['patch_sha256']and
          {c['name']for c in openings['checks']}==expected_rays|base_checks and
          all(c['passed']is True and not c.get('hits')for c in openings['checks']),
          'Ornament revision obstructs a previously open window in an authored LOD')
    ornaments=load(entry['ornament_validation'])
    expected_checks={str(lod)+'/'+name for lod in range(4)for name in
                     ('seven_closed_components','every_edge_two_faces','positive_component_volumes','no_vertices_buried_in_wall')}
    check(ornaments['status']=='passed'and ornaments['patch_sha256']==entry['patch_sha256']and
          set(ornaments['checks'])==expected_checks and all(v is True for v in ornaments['checks'].values())and
          {lod['lod']for lod in ornaments['lods']}==set(range(4))and len(ornaments['lods'])==4,
          'Ornament surface/volume proof is incomplete or covers another patch')
    for lod in ornaments['lods']:
        check(lod['components']==7 and len(lod['volumes_m3'])==7 and
              all(math.isfinite(v)and v>0 for v in lod['volumes_m3'])and
              math.isfinite(lod['minimum_wall_clearance_m'])and lod['minimum_wall_clearance_m']>=0 and
              math.isfinite(lod['maximum_wall_clearance_m'])and
              lod['minimum_wall_clearance_m']<=lod['maximum_wall_clearance_m']<=0.5 and
              lod['triangles']==sum(f['geom']==lod['lod']for f in patch['add']),
              'Ornament volumes or attachment clearance differ from the reviewed bounded geometry')
    mesh_descendant(record_path,heads,check,matches,history)


def architecture_ornaments_reanchor_descendant(record_path,heads,check,matches,history):
    """Reanchor only four street-side plaques after the immutable first revision."""
    if not record_path.exists():return
    entry=load(record_path);relative='out/jak3/fr3/wascitya.fr3'
    parent_path=HERE/'city-block-v3/architecture/revision-001/installed.json';parent=load(parent_path)
    check(entry['path']==relative and entry['base_sha256']==heads.get(relative)==parent['output_sha256'],
          'Ornament reanchor must extend the exact installed first ornament revision')
    check(Path(entry['parent_record']).resolve()==parent_path.resolve()and
          Path(entry['base_path']).resolve()==Path(parent['output_path']).resolve(),
          'Ornament reanchor changed its immutable predecessor')
    matches(parent_path,entry['parent_record_sha256'])
    for key in ('geometry_validation','bvh_coverage','window_anchors','opening_validation','visibility_validation'):
        matches(Path(entry[key]),entry[key+'_sha256'])
    check(Path(entry['window_anchors']).resolve()==Path(parent['window_anchors']).resolve()and
          entry['window_anchors_sha256']==parent['window_anchors_sha256'],
          'Ornament reanchor changed window positions or interior alignment')
    patch=load(entry['patch'])
    check(patch['level']=='wascitya'and patch['source_fr3']['sha256']==entry['base_sha256']and
          patch.get('preserve_bvh')is True and not patch.get('textures')and not patch.get('new_textures'),
          'Ornament reanchor changed map scope, textures or native BVH')
    allowed={('tie',lod,0,40 if lod<3 else 38,group)for lod in range(4)for group in (5,6,7)}
    selected={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['remove']}
    appended={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['add']}
    check(selected==appended==allowed,
          'Ornament reanchor changes geometry outside the four street-side plaques')
    check(len({(f['geom'],f['tree'],f['draw'],f['group'],f['stream_index'])for f in patch['remove']})==len(patch['remove']),
          'Ornament reanchor repeats a native triangle removal')
    check(all('texture'not in f for f in patch['add']),
          'Ornament reanchor reassigns original texture pages')
    for lod in range(4):
        for group in (5,6,7):
            expected=(164 if lod<2 else 94)*(2 if group==6 else 1)
            faces=[f for f in patch['add']if f['geom']==lod and f['group']==group]
            removed=[f for f in patch['remove']if f['geom']==lod and f['group']==group]
            check(len(faces)==len(removed)==expected,
                  'Ornament reanchor leaves or adds an unexpected plate fragment')
            adjacency={};edges={}
            for index,face in enumerate(faces):
                points=[struct.pack('<3f',*v['p'])for v in face['vertices']]
                for point in points:adjacency.setdefault(point,set()).add(index)
                for a,b in zip(points,points[1:]+points[:1]):
                    edge=tuple(sorted((a,b)));counts=edges.setdefault(edge,[0,0])
                    counts[0]+=1;counts[1]+=1 if a<b else -1
            check(all(count==2 and direction==0 for count,direction in edges.values()),
                  'Reanchored ornament has an open edge or inconsistent winding')
            remaining=set(range(len(faces)));components=[]
            while remaining:
                first=remaining.pop();pending=[first];component={first}
                while pending:
                    face=faces[pending.pop()]
                    for vertex in face['vertices']:
                        for neighbor in adjacency[struct.pack('<3f',*vertex['p'])]:
                            if neighbor in remaining:
                                remaining.remove(neighbor);pending.append(neighbor);component.add(neighbor)
                components.append(component)
            check(len(components)==(2 if group==6 else 1),
                  'Ornament reanchor does not preserve the four independent plaques')
            for component in components:
                origin=faces[next(iter(component))]['vertices'][0]['p'];volume=0.
                for index in component:
                    a,b,c=([v['p'][i]-origin[i]for i in range(3)]for v in faces[index]['vertices'])
                    cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
                    volume+=sum(a[i]*cross[i]for i in range(3))/6.
                check(math.isfinite(volume)and volume>0,
                      'Reanchored ornament is inside-out or has zero enclosed volume')
    geometry=load(entry['geometry_validation'])
    check(geometry['passed']is True and geometry['source_fr3']['sha256']==entry['base_sha256']and
          geometry['patch_sha256']==entry['patch_sha256']and
          geometry['faces_removed']==len(patch['remove'])and geometry['faces_added']==len(patch['add'])and
          geometry['degenerate_float32']==geometry['bad_normals']==geometry['bad_palettes']==0,
          'Ornament reanchor proof does not cover the exact finite exported patch')
    coverage=load(entry['bvh_coverage'])
    check(coverage['status']=='passed'and coverage['source_sha256']==entry['base_sha256']and
          coverage['patch_sha256']==entry['patch_sha256']and coverage['outside_vertices']==0 and
          coverage['all_added_vertices_inside_native_spheres']is True and coverage['source_modified']is False and
          coverage['vertices_checked']==len(patch['add'])*3,
          'Reanchored plaques escape their unchanged native culling spheres')
    check({('tie',g['geom'],g['tree'],g['draw'],g['group'])for g in coverage['groups']}==appended and
          all(g['outside_vertices']==0 for g in coverage['groups']),
          'Ornament reanchor BVH proof covers a different group selection')
    openings=load(entry['opening_validation']);anchors=load(entry['window_anchors'])
    expected_rays={a['id']+' LOD'+str(lod)+' actual 3x3 rays clear'for a in anchors for lod in range(4)}
    base_checks={'Every removal exists in exact source','All removed original positions match',
                 'No duplicate native removals','No nonfinite vertices or normals'}
    check(openings['passed']is True and openings['source_sha256']==entry['base_sha256']and
          openings['patch_sha256']==entry['patch_sha256']and
          {c['name']for c in openings['checks']}==expected_rays|base_checks and
          all(c['passed']is True and not c.get('hits')for c in openings['checks']),
          'Ornament reanchor obstructs a previously open window')
    visibility=load(entry['visibility_validation'])
    check(visibility['status']=='passed'and visibility['source_sha256']==entry['base_sha256']and
          visibility['patch_sha256']==entry['patch_sha256'],
          'Ornament reanchor has no visibility proof for the exact revised geometry')
    native_path=Path(entry['visibility_validation']).parent/'native.json'
    matches(native_path,visibility['native_export_sha256'])
    native=load(native_path)
    check(native['source_fr3']['sha256']==entry['base_sha256']and
          visibility['full_block_faces']==len(native['faces'])and
          visibility['occluders_excluded']==[]and
          visibility['author_report_sha256']==entry['author_report_sha256'],
          'Ornament reanchor visibility omits occluders or refers to another block/author geometry')
    expected_plaques={'House2 metal shield group'+str(group)+'-'+str(part)+' LOD'+str(lod):(lod,group)
                      for lod in range(4)for group in (5,6,7)for part in range(2 if group==6 else 1)}
    expected_checks={name+' camera'+str(camera)+' no support wall clipping'
                     for name in expected_plaques for camera in range(3)}|{
                     name+suffix for name in expected_plaques for suffix in
                     (' all samples ahead of support wall',' fully visible in an adjacent street view')}|{
                     name+' native close camera minimum 85 percent visible'
                     for name,(lod,_)in expected_plaques.items()if lod==0}
    check(set(visibility['checks'])==expected_checks and
          all(value is True for value in visibility['checks'].values())and
          len(visibility['plaques'])==16 and {p['name']for p in visibility['plaques']}==set(expected_plaques),
          'Ornament reanchor lacks its complete local-support and three-camera visibility checks')
    cameras=visibility['cameras_m']
    expected_cameras=((2321.,31.,-16.),(2320.536865234375,31.,-17.94561195373535),
                      (2321.463134765625,31.,-14.054388046264648))
    check(len(cameras)==3 and all(len(a)==3 and all(abs(x-y)<1e-5 for x,y in zip(a,b))
                                 for a,b in zip(cameras,expected_cameras))and
          visibility['native_camera_target_m']==[2342.,27.,-21.],
          'Ornament reanchor visibility moved away from the reviewed native street camera')
    for plaque in visibility['plaques']:
        lod,group=expected_plaques[plaque['name']]
        check((plaque['lod'],plaque['group'])==(lod,group)and plaque['samples_per_camera']==13 and
              len(plaque['cameras'])==3 and {c['camera_index']for c in plaque['cameras']}==set(range(3)),
              'Ornament visibility omitted front-surface samples or a reviewed camera')
        local=plaque['local_street_side_rays']
        check(len(local)==13 and all(ray['passed']is True and
                  all(len(ray[key])==3 and all(math.isfinite(x)for x in ray[key])for key in ('sample_m','hit_m'))and
                  math.dist(ray['sample_m'],ray['hit_m'])<0.5 for ray in local),
              'A reanchored plaque intersects its own supporting wall')
        visible_by_camera=[]
        for camera in plaque['cameras']:
            rays=camera['rays'];camera_position=cameras[camera['camera_index']]
            check(camera['no_support_wall_clipping']is True and len(rays)==13 and
                  camera['visible_samples']==sum(ray['visible']is True for ray in rays),
                  'Ornament visibility miscounts its actual visible samples')
            for index,ray in enumerate(rays):
                face=ray['face'];valid_points=all(len(ray[key])==3 and all(math.isfinite(x)for x in ray[key])
                                                for key in ('sample_m','hit_m'))
                check(valid_points and ray['sample_m']==local[index]['sample_m']and face is not None,
                      'Ornament street visibility samples differ from the local support tests')
                if not valid_points or face is None:continue
                gap=math.dist(ray['sample_m'],ray['hit_m'])
                visible=(ray['visible']is True and ray['ordinary_foreground_occlusion']is False and
                         face['replacement']is True and face['tree_type']=='tie'and face['tree']==0 and
                         face['group']==group and face['draw']==(40 if lod<3 else 38)and gap<0.5)
                # A distant facade may naturally hide an otherwise correctly
                # attached plaque. This never excuses clipping by its own wall.
                occluded=(ray['visible']is False and ray['ordinary_foreground_occlusion']is True and
                          face['replacement']is False and gap>3. and
                          math.dist(camera_position,ray['hit_m'])+3.<math.dist(camera_position,ray['sample_m']))
                check(abs(gap-ray['separation_to_occluder_m'])<1e-4 and (visible or occluded),
                      'Ornament ray is neither visible nor blocked by a documented distant foreground surface')
            visible_by_camera.append((camera['camera_index'],camera['visible_samples']))
        check(any(count==13 for _,count in visible_by_camera)and
              (lod!=0 or dict(visible_by_camera)[0]/13>=.85),
              'A plaque has no fully visible adjacent angle or is mostly hidden from the native close camera')
    mesh_descendant(record_path,heads,check,matches,history)


def architecture_single_window_descendant(record_path,heads,check,matches,history):
    """Close only house1's duplicate east room after both ornament corrections."""
    if not record_path.exists():return
    entry=load(record_path);relative='out/jak3/fr3/wascitya.fr3'
    parent_path=HERE/'city-block-v3/architecture/revision-002/installed.json';parent=load(parent_path)
    check(entry['path']==relative and entry['base_sha256']==heads.get(relative)==parent['output_sha256'],
          'Single-window correction must extend the exact installed second ornament revision')
    check(Path(entry['parent_record']).resolve()==parent_path.resolve()and
          Path(entry['base_path']).resolve()==Path(parent['output_path']).resolve(),
          'Single-window correction changed its immutable predecessor')
    matches(parent_path,entry['parent_record_sha256'])
    anchors=verify_single_window_anchor_revision(entry,check,matches)
    for key in ('geometry_validation','bvh_coverage','opening_validation','closed_window_validation'):
        matches(Path(entry[key]),entry[key+'_sha256'])
    patch=load(entry['patch'])
    check(patch['level']=='wascitya'and patch['source_fr3']['sha256']==entry['base_sha256']and
          patch.get('preserve_bvh')is True and not patch.get('textures')and not patch.get('new_textures'),
          'Single-window correction changes unrelated map, textures or native BVH')
    allowed={('tie',lod,1,draw,1)for lod in range(4)for draw in (9,12 if lod<3 else 11)}
    selected={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['remove']}
    appended={(f.get('tree_type','tie'),f['geom'],f['tree'],f['draw'],f['group'])for f in patch['add']}
    check(selected==appended==allowed,
          'Single-window correction modifies a group beyond the selected house1 stucco/stone facade')
    check(len({(f['geom'],f['tree'],f['draw'],f['group'],f['stream_index'])for f in patch['remove']})==len(patch['remove']),
          'Single-window correction repeats a native triangle removal')
    check(all('texture'not in f for f in patch['add']),
          'Single-window correction reassigns original texture pages')
    for lod in range(4):
        expected_remove=(1563,1563,1561,1523)[lod];expected_add=(71,71,69,47)[lod]
        for draw,removed,added in ((9,expected_remove,expected_add),(12 if lod<3 else 11,10,2)):
            check(sum(f['geom']==lod and f['draw']==draw for f in patch['remove'])==removed and
                  sum(f['geom']==lod and f['draw']==draw for f in patch['add'])==added,
                  'Single-window correction differs from the reviewed facade/frame/balcony geometry delta')
    geometry=load(entry['geometry_validation'])
    check(geometry['passed']is True and geometry['source_fr3']['sha256']==entry['base_sha256']and
          geometry['patch_sha256']==entry['patch_sha256']and
          geometry['faces_removed']==len(patch['remove'])==6250 and
          geometry['faces_added']==len(patch['add'])==266 and
          geometry['degenerate_float32']==geometry['bad_normals']==geometry['bad_palettes']==0,
          'Single-window geometry proof does not cover the exact finite exported patch')
    coverage=load(entry['bvh_coverage'])
    check(coverage['status']=='passed'and coverage['source_sha256']==entry['base_sha256']and
          coverage['patch_sha256']==entry['patch_sha256']and coverage['outside_vertices']==0 and
          coverage['all_added_vertices_inside_native_spheres']is True and coverage['source_modified']is False and
          coverage['vertices_checked']==len(patch['add'])*3,
          'Closed facade vertices escape their unchanged native culling spheres')
    check({('tie',g['geom'],g['tree'],g['draw'],g['group'])for g in coverage['groups']}==appended and
          all(g['outside_vertices']==0 for g in coverage['groups']),
          'Closed facade BVH proof covers a different group selection')
    openings=load(entry['opening_validation'])
    expected_rays={a['id']+' LOD'+str(lod)+' actual 3x3 rays clear'for a in anchors for lod in range(4)}
    base_checks={'Every removal exists in exact source','All removed original positions match',
                 'No duplicate native removals','No nonfinite vertices or normals'}
    check(openings['passed']is True and openings['source_sha256']==entry['base_sha256']and
          openings['patch_sha256']==entry['patch_sha256']and
          {c['name']for c in openings['checks']}==expected_rays|base_checks and
          all(c['passed']is True and not c.get('hits')for c in openings['checks']),
          'Single-window correction obstructs a retained opening or still expects the removed opening')
    closed=load(entry['closed_window_validation'])
    check(closed['status']=='passed'and closed['source_sha256']==entry['base_sha256']and
          closed['patch_sha256']==entry['patch_sha256']and
          closed['author_report_sha256']==entry['author_report_sha256']and
          closed['removed_window_id']=='wca-house1-east-room'and
          closed['previous_window_anchors_sha256']==parent['window_anchors_sha256']and
          closed['window_anchors_sha256']==entry['window_anchors_sha256'],
          'Duplicate east window lacks a closure proof for the exact revised facade')
    expected_closed_checks={'Only east-room anchor removed'}|{
        'LOD'+str(lod)+suffix for lod in range(4)for suffix in
        (' exact house without lateral frame and balcony',' 49 opaque wall rays at original surface')}
    check(set(closed['checks'])==expected_closed_checks and all(v is True for v in closed['checks'].values())and
          len(closed['lods'])==4 and {row['lod']for row in closed['lods']}==set(range(4)),
          'Duplicate window closure lacks every facade and opaque-wall check in all four LODs')
    directory=HERE/'city-block-v3/architecture-single-window-r3'
    author=load(entry['author_report']);original=load(HERE/'city-block-v3/architecture/installed.json')
    historical_author=load(original['author_report'])
    check(author['source_fr3']['sha256']==entry['base_sha256']and
          author['removed_window_id']=='wca-house1-east-room'and
          author['faces_removed']==6250 and author['faces_added']==266 and
          set(author['checks'])=={'LOD'+str(lod)+' exact historical replay'for lod in range(4)}and
          all(value is True for value in author['checks'].values()),
          'Single-window author did not reproduce the exact historical house before deriving its delta')
    check(Path(author['historical_author']).resolve()==(HERE/'city-block-v3/architecture/author_buildings.py').resolve()and
          author['historical_author_sha256']==historical_author['author_sha256']and
          Path(author['historical_patch']).resolve()==Path(original['patch']).resolve()and
          author['historical_patch_sha256']==original['patch_sha256'],
          'Single-window correction was not derived from the exact accepted house author and patch')
    for key in ('historical_author','historical_patch','pre_opening_source','expected_house'):
        matches(Path(author[key]),author[key+'_sha256'])
    check(Path(author['expected_house']).resolve()==(directory/'expected-house-without-east.json').resolve()and
          closed['expected_house_sha256']==author['expected_house_sha256']and
          closed['baseline_sha256']==author['pre_opening_source_sha256'],
          'Duplicate-window closure refers to a different reconstructed house or native wall source')
    native_path=directory/'native.json';matches(native_path,closed['native_export_sha256'])
    native=load(native_path);desired=load(author['expected_house'])
    check(native['source_fr3']['sha256']==entry['base_sha256'],
          'Duplicate-window closure native export is not the installed R2 parent')
    from collections import Counter
    def signature(face):
        points=[tuple(struct.unpack('<3f',struct.pack('<3f',*vertex['p'])))for vertex in face['vertices']]
        oriented=min(tuple(points[i:]+points[:i])for i in range(3))
        return (face.get('tree_type','tie'),face['geom'],face['tree'],face['draw'],face['group'],oriented)
    def source_key(face):return tuple(face[k]for k in ('tree_type','geom','tree','draw','stream_index'))
    removed_keys={source_key(face)for face in patch['remove']}
    for row in closed['lods']:
        lod=row['lod'];expected_faces=[face for face in desired if face['geom']==lod]
        groups={(face['tree_type'],face['tree'],face['draw'],face['group'])for face in expected_faces}
        check(groups=={('tie',1,draw,1)for draw in ((9,12,19,22)if lod<3 else(9,11,18,21))},
              'Reconstructed no-east house includes unrelated geometry groups')
        actual_faces=[face for face in native['faces']if face['geom']==lod and
                      (face['tree_type'],face['tree'],face['draw'],face['group'])in groups and
                      source_key(face)not in removed_keys]+[face for face in patch['add']if face['geom']==lod]
        check(row['after_house_triangles']==len(actual_faces)==row['expected_house_triangles']==len(expected_faces)and
              Counter(signature(face)for face in actual_faces)==Counter(signature(face)for face in expected_faces),
              'The closed facade still contains its old frame/balcony or differs from the reconstructed house')
        samples=row['wall_samples'];grid=(-.45,-.3,-.15,0,.15,.3,.45)
        check(len(samples)==49 and {tuple(sample['sample'])for sample in samples}=={(x,y)for x in grid for y in grid},
              'Duplicate-window closure omits a reviewed opaque-wall sample')
        for sample in samples:
            face=sample['face'];points_valid=all(len(sample[key])==3 and
                          all(math.isfinite(x)for x in sample[key])for key in ('hit_m','baseline_hit_m'))
            check(sample['passed']is True and points_valid and face is not None and
                  face['tree_type']=='tie'and face['tree']==1 and face['group']==1 and face['draw']==9 and
                  math.isfinite(sample['native_wall_deviation_m'])and
                  0<=sample['native_wall_deviation_m']<.005 and
                  abs(math.dist(sample['hit_m'],sample['baseline_hit_m'])-sample['native_wall_deviation_m'])<1e-5,
                  'Removed east opening is not covered by opaque native facade at its original surface')
    mesh_descendant(record_path,heads,check,matches,history)


def architecture_expanded_descendant(record_path,heads,check,matches,history):
    if not record_path.exists():return
    entry=load(record_path)
    check(entry['status']=='installed'and entry['base_sha256']==heads.get(entry['path']),
          'Expanded six-house revision does not extend the exact current city geometry head')
    helper=module(HERE/'city-block-v3/verify_expanded_houses.py','bounded_six_house_revision')
    helper.verify(entry,HERE/'city-block-v3',check,matches)
    mesh_descendant(record_path,heads,check,matches,history)


def verify_cloud_sources(check,matches):
    path=HERE/'spargus-clouds-manifest.json'
    if not path.exists():return
    record=load(path);apply=module(HERE/'apply_spargus_clouds.py','bounded_cloud_source')
    expected=set(apply.EDITS)|{'engine-src/game/graphics/opengl_renderer/SpargusClouds.h'}|{
        tree+'/game/graphics/opengl_renderer/shaders/spargus_clouds.'+extension
        for tree in ('engine-src','data')for extension in ('vert','frag')}
    check(set(record['files'])==expected,'Cloud manifest has unexpected source files')
    for relative,entry in record['files'].items():
        target=ROOT/relative;matches(target,entry['after_sha256'])
        if relative in apply.EDITS:
            raw=target.read_bytes();newline='\r\n'if b'\r\n'in raw else '\n'
            for before,after in reversed(apply.EDITS[relative]):
                before=before.replace('\n',newline).encode();after=after.replace('\n',newline).encode()
                check(raw.count(after)==1,'Missing/duplicate scoped cloud insertion')
                raw=raw.replace(after,before,1)
            check(digest(raw)==entry['before_sha256'],'Cloud insertion changed unrelated Direct renderer source')
            matches(HERE/'sky-source-baseline'/relative,entry['before_sha256'])
        else:
            author=HERE/Path(relative).name
            matches(author,entry['after_sha256'])
            check(entry['before_sha256']is None,'Unexpected cloud source file baseline')


def verify_city_fire_sources(check,matches):
    """Peel exactly four source insertions; city shaders never replace palace shaders."""
    path=HERE/'city-fire-v2/manifest.json'
    if not path.exists():return {}
    record=load(path);apply=module(HERE/'city-fire-v2/apply.py','bounded_city_fire')
    check(record['status']=='applied' and set(record['files'])==set(apply.edits()),
          'City fire source scope changed')
    expected_new={'engine-src/game/graphics/opengl_renderer/'+name
                  for name in ('CityFire.h','CityFireSources.h','CityFireAttachments.inc')}|{
                  tree+'/game/graphics/opengl_renderer/shaders/'+stem+'.'+ext
                  for tree in ('engine-src','data')for stem in ('city_fire','city_fire_lighting','city_fire_embers')
                  for ext in ('vert','frag')}
    check(set(record['new_files'])==expected_new,'City fire new-file scope changed')
    predecessors={}
    for relative,entry in record['files'].items():
        before=apply.source_before(relative)
        matches(ROOT/relative,entry['after_sha256']);matches(before,entry['before_sha256'])
        predecessors[relative]=before
    for relative,expected in record['new_files'].items():matches(ROOT/relative,expected)
    return predecessors


def verify_shared_city_room(directory,check,matches,motion=None):
    helper=module(HERE/'city-block-v3/verify_shared_room.py','bounded_shared_room_provenance')
    return helper.verify(directory,check,matches,motion or{})


def verify_city_interiors(check,matches):
    """Verify the exact authored room graph, never a directory wildcard."""
    directory=HERE/'city-block-v3/interiors'
    manifest_path=directory/'source-manifest.json'
    if not manifest_path.exists():return set(),{}
    motion_helper=module(HERE/'city-block-v3/verify_inhabitant_motion.py','bounded_inhabitant_motion')
    motion=motion_helper.verify(directory.parent/'inhabitants',check,matches)
    shared=verify_shared_city_room(directory,check,matches,motion)
    ao_predecessors=verify_city_interior_ao(directory,check,matches,shared.get('shader_predecessors',{}))
    # prepare.py imports only its adjacent, separately pinned room_config module.
    import sys
    sys.path.insert(0,str(directory))
    try:apply=module(directory/'prepare.py','bounded_city_interiors')
    finally:sys.path.pop(0)
    record=load(manifest_path)
    renderer='engine-src/game/graphics/opengl_renderer/'
    expected_sources={renderer+'OpenGLRenderer.h',renderer+'OpenGLRenderer.cpp'}
    expected_new={renderer+'CityInteriors.h'}|{
        tree+'/game/graphics/opengl_renderer/shaders/city_interior.'+ext
        for tree in ('engine-src','data')for ext in ('vert','frag')}
    check(set(record['files'])==set(apply.edits())==expected_sources,
          'City interiors modified source scope changed')
    check(set(record['new_files'])==expected_new,'City interiors new source scope changed')
    predecessors={}
    for relative,entry in record['files'].items():
        before=apply.source_before(relative)
        check(before.resolve()==(directory/'before'/relative).resolve(),
              'City interior source predecessor is outside its exact snapshot path')
        matches(before,entry['before_sha256']);matches(ROOT/relative,entry['after_sha256'])
        # The native renderer must be reproduced completely by the inverse,
        # including the pre-existing palace-fire hook and every other bucket.
        check(apply.inverse((ROOT/relative).read_text(encoding='utf-8-sig'),relative)==
              before.read_text(encoding='utf-8-sig'),'Interior inverse altered unrelated renderer code')
        predecessors[relative]=before
    for relative,expected in record['new_files'].items():
        matches(ROOT/relative,expected);matches(directory/Path(relative).name,expected)

    qa=load(directory/'qa/validation.json')
    check(all_passed(qa),'City interior GPU validation did not pass')
    expected_shaders={str(directory/('city_interior.'+ext))for ext in ('vert','frag')}
    check(set(qa['shader_sha256'])==expected_shaders,'Interior GPU proof tests different shaders')
    for path,expected in qa['shader_sha256'].items():
        matches(shared.get('shader_predecessors',{}).get(Path(path).resolve(),Path(path)),expected)
    asset_prefix='custom_assets/jak3/city-interiors/'
    shader_prefix='game/graphics/opengl_renderer/shaders/'
    actors=HERE/'city-block-v3/inhabitants'
    base_mesh_names=('lounge','conversation','sitting-male','conversing-male','conversing-female')
    mesh_names=base_mesh_names+(('corner-conversation',)if shared else())
    expected_qa_assets={str((directory if name in ('lounge','conversation')else actors)/(name+'.'+ext))
                        for name in base_mesh_names for ext in ('json','bin')}
    check(set(qa['asset_sha256'])==expected_qa_assets,'Interior GPU proof asset inventory differs')
    # A retained original GPU report refers to the before-AO files; a new full
    # GPU run may test the installed AO files. Require all four room hashes to
    # describe one complete proven state, never a mixture of old/new sources.
    qa_before_ao=False
    if ao_predecessors:
        room_hashes={Path(path).resolve():expected for path,expected in qa['asset_sha256'].items()
                     if Path(path).resolve()in ao_predecessors}
        all_before=all(digest(ao_predecessors[path].read_bytes())==expected for path,expected in room_hashes.items())
        all_after=all(digest(path.read_bytes())==expected for path,expected in room_hashes.items())
        check(len(room_hashes)==4 and (all_before or all_after),
              'Interior GPU proof mixes AO predecessor and descendant states or names an unproven room')
        qa_before_ao=all_before
    for path,expected in qa['asset_sha256'].items():
        target=ao_predecessors.get(Path(path).resolve(),Path(path))if qa_before_ao else Path(path)
        target=motion.get('source_predecessors',{}).get(target.resolve(),target)
        matches(target,expected)

    manifest=load(directory/'asset-manifest.json')
    declared=manifest['assets'];expected_assets={asset_prefix+name+'.'+ext
        for name in mesh_names for ext in ('json','bin')}|{
        asset_prefix+name for name in ('runtime.json','wood.rgba','fabric.rgba')}|{
        shader_prefix+'city_interior.'+ext for ext in ('vert','frag')}
    # Encoding is checked against each actual source PNG, including alpha bytes.
    # Nothing may add an arbitrary filename just by extending asset-manifest.
    from PIL import Image
    checked_textures=set()
    def texture_from_png(png,relative):
        check(relative.startswith(asset_prefix)and '..'not in Path(relative).parts,
              'Interior texture destination escapes its asset directory')
        expected_assets.add(relative)
        if relative in checked_textures:return
        checked_textures.add(relative)
        with Image.open(png)as image:
            image=image.convert('RGBA');expected=struct.pack('<II',*image.size)+image.tobytes()
        check((ROOT/'data'/relative).read_bytes()==expected,'Interior RGBA is not a lossless source encoding: '+relative)
    for name in mesh_names:
        origin=(directory/'shared-room-v2'if name=='corner-conversation'else
                directory if name in ('lounge','conversation')else actors)
        original=load(origin/(name+'.json'));runtime=load(ROOT/'data'/asset_prefix/(name+'.json'))
        expected=json.loads(json.dumps(original))
        check(original['binary']==name+'.bin','Interior binary reference changed')
        raw=(origin/original['binary']).read_bytes()
        check((ROOT/'data'/asset_prefix/(name+'.bin')).read_bytes()==raw,
              'Interior runtime binary differs from the authored and GPU-tested source')
        frames=original.get('frame_count',1);vertices=original['vertex_count']
        expected_frames=1 if name in ('lounge','conversation','corner-conversation')else(
                        32 if motion and name in('conversing-male','conversing-female')else 4)
        check(frames==expected_frames and vertices>0 and vertices%3==0 and
              len(raw)==vertices*frames*48,'Interior binary frame layout differs')
        check(all(math.isfinite(v)for row in struct.iter_unpack('<12f',raw)for v in row),
              'Interior binary contains nonfinite coordinates/materials')
        draws=original['draws']
        check(draws and draws[0]['first']==0 and sum(d['count']for d in draws)==vertices and
              all(d['count']>0 and d['count']%3==0 for d in draws)and
              all(a['first']+a['count']==b['first']for a,b in zip(draws,draws[1:])),
              'Interior draw ranges overlap, omit or escape the frame')
        for draw in expected['draws']:
            if 'texture'in draw:
                png=draw['texture']
                check(Path(png).parts[0]=='textures'and len(Path(png).parts)==2 and Path(png).suffix=='.png',
                      'Interior actor texture escaped the selected native texture directory')
                if 'texture_sha256'in draw:matches(origin/png,draw['texture_sha256'])
                draw['texture']=Path(png).with_suffix('.rgba').as_posix()
                texture_from_png(origin/png,asset_prefix+draw['texture'])
        check(runtime==expected,'Interior runtime metadata differs beyond PNG-to-RGBA extension conversion')
    texture_from_png(HERE/'wood-hd-v2.png',asset_prefix+'wood.rgba')
    texture_from_png(HERE/'market-cotton-hd.png',asset_prefix+'fabric.rgba')
    check(set(declared)==expected_assets and len(expected_assets)==(41 if shared else 39),
          'Interior asset manifest is not the exact reviewed room asset graph')
    for relative,expected in declared.items():
        check(relative in expected_assets,'Undeclared interior runtime path')
        if relative in expected_assets:matches(ROOT/'data'/relative,expected)
    anchors,anchor_count,inhabited_count=verified_city_window_anchors(check,matches)
    config=load(ROOT/'data'/asset_prefix/'runtime.json')
    if shared:
        room_config=module(directory/'room_config.py','bounded_shared_room_config')
        rooms=room_config.rooms_for(anchors)
        check(config=={'schema':'city-physical-rooms-v2','windows':anchors,'rooms':rooms,
                       'scope':'Spargus authored apertures; shared physical rooms; visual interiors only'},
              'Shared room runtime config differs from its pinned physical apartment assignment')
        shared_ids=['wca-house1-west-room','wca-house1-east-room']
        linked=[room for room in rooms if set(room['windows'])&set(shared_ids)]
        check(len(linked)==1 and linked[0]=={
            'id':'wca-house1-corner-apartment','anchor':shared_ids[0],'windows':shared_ids,
            'mesh':'corner-conversation','scale':[1,1,1],'lamp':[.55,2.8,-1.7],
            'actors':[{'mesh':'conversing-male','position':[.25,.058,-2.15],'yaw':math.atan2(1.2,-.9),'phase':0},
                      {'mesh':'conversing-female','position':[1.45,.058,-3.05],'yaw':math.atan2(-1.2,.9),'phase':0}]},
              'Both corner windows must observe the same physical room and two persistent occupants')
        assigned=[window for room in rooms for window in room['windows']]
        check(len(rooms)==8 and len(assigned)==len(set(assigned))==9 and set(assigned)=={a['id']for a in anchors}and
              len({room['id']for room in rooms})==8 and sum(bool(room['actors'])for room in rooms)==5,
              'Shared room graph duplicates a window, room or occupant set or changes the inhabited mix')
        check(all(len(room['actors'])<2 or len({actor['phase']for actor in room['actors']})==1 for room in rooms),
              'Conversation clips lost their shared phase and encoded speaker/listener alternation')
        check(room_config.rooms_for(list(reversed(anchors)))==[linked[0]]+[
                  room for anchor in reversed(anchors)for room in rooms
                  if anchor['id']not in shared_ids and room['anchor']==anchor['id']],
              'Changing window traversal order changes a physical apartment or its inhabitants')
    else:
        check(config=={'windows':anchors,'scope':'two WCA pilot houses; visual interiors only'},
              'Interior runtime window config differs from authored facade openings')
    check(len(anchors)==anchor_count and len({a['id']for a in anchors})==anchor_count and
          {a['building_native_instance']for a in anchors}==({0,1,2,3,4,58}if shared else{1,2})and
          all(a['level']=='wascitya'and a['tree']==1 for a in anchors),
          'Interior anchor scope differs from the selected WCA houses')
    check(sum(bool(a['inhabited'])for a in anchors)==inhabited_count,
          'Interior occupancy no longer preserves the selected inhabited/empty window mix')
    for anchor in anchors:
        vectors=[anchor[k]for k in ('center','normal','right','up')]
        check(all(len(v)==3 and all(math.isfinite(x)for x in v)for v in vectors),
              'Interior anchor vectors malformed')
        normal,right,up=vectors[1:]
        check(all(abs(sum(x*x for x in v)-1)<.0001 for v in (normal,right,up))and
              abs(sum(x*y for x,y in zip(normal,right)))<.0001,
              'Interior anchor basis is not orthonormal')
    native=load(actors/'source-manifest.json');actor_check=load(actors/'validation.json')
    check(actor_check['status']=='passed'and {a['actor']for a in actor_check['actors']}==set(base_mesh_names[2:])and
          all(a['all_passed']and all(a['checks'].values())for a in actor_check['actors']),
          'Interior native inhabitant validation failed')
    check(set(native)=={'male','female'},'Interior native inhabitant source scope changed')
    for sex,entry in native.items():
        matches(Path(entry['source']),entry['source_sha256'])
        matches(actors/(sex+'-selected.glb'),entry['selected_sha256'])
    return expected_assets,predecessors


def verified_city_window_anchors(check,matches):
    """Preserve historical anchors through the exact installed geometry chain."""
    directory=HERE/'city-block-v3/architecture'
    original=load(directory/'installed.json')
    historical_path=directory/'window-anchors.json'
    check(Path(original['window_anchors']).resolve()==historical_path.resolve(),
          'The historical five-window source path changed')
    matches(historical_path,original['window_anchors_sha256'])
    historical=load(historical_path)
    expanded_path=directory/'revision-004/installed.json'
    if expanded_path.exists():
        entry=load(expanded_path);parent_path=directory/'revision-003/installed.json';parent=load(parent_path)
        check(entry['status']=='installed'and Path(entry['parent_record']).resolve()==parent_path.resolve()and
              entry['base_sha256']==parent['output_sha256'],
              'Nine-window runtime lacks the exact installed R4 geometry parent')
        matches(parent_path,entry['parent_record_sha256'])
        matches(Path(entry['restoration_validation']),entry['restoration_validation_sha256'])
        helper=module(HERE/'city-block-v3/verify_expanded_houses.py','bounded_six_house_anchors')
        return helper.anchors(entry,HERE/'city-block-v3',check,matches),9,6
    revision_path=directory/'revision-003/installed.json'
    if not revision_path.exists():return historical,5,2
    return verify_single_window_anchor_revision(load(revision_path),check,matches),4,1


def verify_single_window_anchor_revision(revision,check,matches):
    directory=HERE/'city-block-v3/architecture'
    original=load(directory/'installed.json');historical_path=directory/'window-anchors.json'
    matches(historical_path,original['window_anchors_sha256']);historical=load(historical_path)
    parent_path=directory/'revision-002/installed.json';parent=load(parent_path)
    check(revision['status']=='installed'and
          Path(revision['parent_record']).resolve()==parent_path.resolve()and
          revision['base_sha256']==parent['output_sha256'],
          'Four-window runtime configuration lacks its exact installed geometry revision')
    matches(parent_path,revision['parent_record_sha256'])
    check(Path(parent['window_anchors']).resolve()==historical_path.resolve()and
          parent['window_anchors_sha256']==original['window_anchors_sha256'],
          'Four-window revision is not descended from the immutable five-window source')
    anchors_path=HERE/'city-block-v3/architecture-single-window-r3/window-anchors.json'
    check(Path(revision['window_anchors']).resolve()==anchors_path.resolve(),
          'Four-window anchors came from a different or untracked source')
    matches(anchors_path,revision['window_anchors_sha256'])
    anchors=load(anchors_path)
    check(len(historical)==5 and sum(a['id']=='wca-house1-east-room'for a in historical)==1 and
          anchors==[a for a in historical if a['id']!='wca-house1-east-room'],
          'Window revision changes another anchor instead of solely removing the lateral east room')
    return anchors


def verify_city_interior_ao(directory,check,matches,shader_predecessors=None):
    """Neutral vertex contact shading on exactly the two furnished room meshes."""
    names=('lounge','conversation');record_path=directory/'ao-installed.json'
    active={name:'vertex_ao'in load(directory/(name+'.json'))for name in names}
    if not record_path.exists():
        check(not any(active.values()),'Room contact shading has no immutable source record')
        return {}
    record=load(record_path);candidate=directory/'ao-candidate'
    check(record['status']=='installed'and all(active.values())and len(record['rooms'])==2 and
          {room['layout']for room in record['rooms']}==set(names),
          'Room contact shading changed its two-room scope')
    expected_proofs={str(candidate/name)for name in
                     ('validation.json','bake-report.json','bake.py','verify.py','gpu-comparison.json')}
    check(set(record['proofs'])==expected_proofs,'Room contact shading proof inventory differs')
    for path,expected in record['proofs'].items():matches(Path(path),expected)
    validation=load(candidate/'validation.json');bake=load(candidate/'bake-report.json')
    expected_checks={'source_hash_unchanged','candidate_hash','palette_and_materials_unchanged',
                     'draw_material_order_unchanged','surface_area_unchanged_per_material','bounds_unchanged',
                     'finite','unit_normals','same_authored_uv_mapping','neutral_ao_rgb_no_hue_change',
                     'alpha_preserved','draws_cover_buffer'}
    check(validation['status']=='passed'and len(validation['rooms'])==2 and
          {r['layout']for r in validation['rooms']}==set(names)and
          all(r['passed']is True and set(r['checks'])==expected_checks and
              all(x is True for x in r['checks'].values())for r in validation['rooms']),
          'Room contact shading lacks all 24 reviewed validation checks')
    check(bake['parameters']=={'rays':128,'radius_m':0.7,'gain':0.4,'edge_m':0.34}and
          len(bake['rooms'])==2 and {r['layout']for r in bake['rooms']}==set(names),
          'Room contact shading baking parameters or source scope changed')
    bake_rooms={r['layout']:r for r in bake['rooms']}
    def surface_area(rows,start,count):
        result=0.
        for index in range(start,start+count,3):
            a,b,c=rows[index:index+3]
            u=[b[i]-a[i]for i in range(3)];w=[c[i]-a[i]for i in range(3)]
            cross=(u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0])
            result+=.5*math.sqrt(sum(x*x for x in cross))
        return result
    predecessors={}
    for room in record['rooms']:
        name=room['layout'];files=room['files'];row=bake_rooms[name]
        check(set(files)=={name+'.json',name+'.bin'},'Contact shading changed an unrelated room file')
        for filename,entry in files.items():
            before=directory/'no-ao'/filename;after=directory/filename
            check(Path(entry['before_path']).resolve()==before.resolve()and
                  Path(entry['after_path']).resolve()==after.resolve(),
                  'Contact shading source snapshot or active target escaped its exact path')
            matches(before,entry['before_sha256']);matches(after,entry['after_sha256'])
            matches(candidate/filename,entry['after_sha256'])
            predecessors[after.resolve()]=before
        old=load(directory/'no-ao'/(name+'.json'));new=load(directory/(name+'.json'))
        old_raw=(directory/'no-ao'/(name+'.bin')).read_bytes();new_raw=(directory/(name+'.bin')).read_bytes()
        check(old['binary']==new['binary']==name+'.bin'and
              digest(old_raw)==old['sha256']==new['vertex_ao']['source_sha256']==row['source_sha256']and
              digest(new_raw)==new['sha256']==row['candidate_sha256'],
              'Contact shading source/candidate bytes differ from the reviewed bake')
        allowed_changes={'vertex_count','draws','sha256','vertex_ao'}
        check({k:v for k,v in old.items()if k not in allowed_changes}==
              {k:v for k,v in new.items()if k not in allowed_changes},
              'Contact shading changed room metadata beyond tessellation and vertex shading')
        check(len(old['draws'])==len(new['draws'])and
              all({k:v for k,v in a.items()if k not in ('first','count')}==
                  {k:v for k,v in b.items()if k not in ('first','count')}
                  for a,b in zip(old['draws'],new['draws'])),
              'Contact shading changed the room material palette or draw material order')
        old_rows=list(struct.iter_unpack('<12f',old_raw));new_rows=list(struct.iter_unpack('<12f',new_raw))
        check(len(old_rows)==old['vertex_count']==row['source_vertices']and
              len(new_rows)==new['vertex_count']==row['candidate_vertices'],
              'Contact shading vertex counts differ from the reviewed source and candidate')
        for a,b in zip(old['draws'],new['draws']):
            before_area=surface_area(old_rows,a['first'],a['count'])
            after_area=surface_area(new_rows,b['first'],b['count'])
            check(abs(before_area-after_area)<max(1e-5,before_area*1e-5),
                  'Contact shading changes the modeled surface area of a room material')
        check(all(abs(fn(v[i]for v in old_rows)-fn(v[i]for v in new_rows))<1e-6
                  for i in range(3)for fn in (min,max)),
              'Contact shading changes the room bounds')
        check(all(math.isfinite(x)for v in new_rows for x in v)and
              all(abs(math.sqrt(sum(x*x for x in v[3:6]))-1)<1e-5 for v in new_rows),
              'Contact shading has nonfinite data or invalid normals')
        check(all(abs(v[6]-(v[0]*.7+v[2]*.23))<2e-6 and
                  abs(v[7]-(v[1]*.7+v[2]*.6))<2e-6 for v in new_rows),
              'Contact shading changes the authored room UV mapping')
        check(all(v[8]==v[9]==v[10]and .599<=v[8]<=1 and v[11]==1 for v in new_rows),
              'Contact shading recolors the rooms, overdarkens them or changes transparency')
        check(new['draws'][0]['first']==0 and sum(d['count']for d in new['draws'])==len(new_rows)and
              all(d['count']>0 and d['count']%3==0 for d in new['draws'])and
              all(a['first']+a['count']==b['first']for a,b in zip(new['draws'],new['draws'][1:])),
              'Contact shading draw ranges do not cover the exact vertex buffer')
    gpu=load(candidate/'gpu-comparison.json')
    check(gpu['status']=='rendered'and len(gpu['rooms'])==2 and
          {r['layout']for r in gpu['rooms']}==set(names)and
          all(r['changed_pixels']>0 and r['mean_absolute_channel_change']>0 for r in gpu['rooms']),
          'Contact shading has no visible rendered comparison for both rooms')
    check(set(gpu['shader_sha256'])=={str(directory/('city_interior.'+ext))for ext in ('vert','frag')},
          'Contact shading rendered comparison used different shaders')
    for path,expected in gpu['shader_sha256'].items():
        target=(shader_predecessors or{}).get(Path(path).resolve(),Path(path))
        matches(target,expected)
    return predecessors


def verify_grass_sources(check,matches):
    """Verify the complete bounded insertion, then expose exact predecessors."""
    fire_predecessors=verify_city_fire_sources(check,matches)
    blade_predecessors={}
    blade_manifest=HERE/'grass-contact-v2/manifest.json'
    if blade_manifest.exists():
        blade=module(blade_manifest.with_name('apply.py'),'bounded_grass_roots')
        blade_predecessors=blade.verify_sources(check,matches)
    path=HERE/'grass-contact/manifest.json'
    if not path.exists():return {}
    record=load(path);apply=module(HERE/'grass-contact/apply.py','bounded_grass_contact')
    expected=set(apply.edits())
    check(record['status']=='applied' and set(record['files'])==expected,
          'Grass contact manifest changed its six-file scope')
    check(record['scope']=='Jak only; WCA/WCB; market-shrub-orange-v1 only',
          'Grass contact scope changed')
    check(record['new_header']=='engine-src/game/graphics/opengl_renderer/GrassContacts.h',
          'Grass contact header path changed')
    matches(ROOT/record['new_header'],record['new_header_sha256'])
    matches(HERE/'grass-contact/GrassContacts.h',record['new_header_sha256'])
    predecessors={}
    for relative,entry in record['files'].items():
        target=blade_predecessors.get(relative,fire_predecessors.get(relative,ROOT/relative));before=Path(entry['before_path'])
        cactus_path=HERE/'environment/geometry-001/material-response.json'
        if relative==apply.MATERIAL and cactus_path.exists():
            cactus=module(cactus_path.with_name('material_response.py'),'bounded_cactus_response')
            target=cactus.source_before()
            cactus_record=load(cactus_path)
            matches(ROOT/relative,cactus_record['after_sha256'])
            matches(target,cactus_record['before_sha256'])
            check(cactus_record['relative']==relative,'Cactus response changed unrelated source scope')
        matches(target,entry['after_sha256']);matches(before,entry['before_sha256'])
        check(apply.inverse(target.read_text(),relative)==before.read_text(),
              'Grass contact inverse changed unrelated accepted source: '+relative)
        predecessors[relative]=before
    check((ROOT/'engine-src'/apply.SHADER).read_bytes()==(ROOT/'data'/apply.SHADER).read_bytes(),
          'Grass contact shader engine/data copies differ')
    check((ROOT/'engine-src'/apply.GOAL).read_text()==(ROOT/'data'/apply.GOAL).read_text(),
          'Grass contact GOAL engine/data copies differ')
    return predecessors


def material_response_baseline(check,matches,predecessors=None):
    """Return the byte-verified predecessor for wind-frame validation, if extended."""
    path=HERE/'environment/material-response.json'
    if not path.exists():return {}
    record=load(path);before=Path(record['before_path']);after=Path(record['after_path'])
    relative=after.relative_to(ROOT).as_posix()
    after=(predecessors or {}).get(relative,after)
    matches(before,record['before_sha256']);matches(after,record['after_sha256'])
    old=before.read_text();new=after.read_text()
    replacements=[(
        '    const bool market = level.level_name == "wascityb" || level.level_name == "wascitya" ||\n'
        '                        level.level_name == "waswide";',
        '    const bool market = level.level_name == "wascityb";'),(
        '      // Regional response only for explicit, high-resolution replacement\n'
        '      // materials. Alpha decals, windows, liquids and unchanged atlases keep\n'
        '      // the native path. The palace classification is unchanged.\n'
        '      const int kind=market ? (std::max(texture.w,texture.h)>=512 ?\n'
        '          classify_market(texture.debug_name) : 0) : classify(texture.debug_name);',
        '      // Only newly authored, dedicated market materials opt in. Native city\n'
        '      // atlases also cover untouched scenery and must retain their own path.\n'
        '      const int kind=market ? classify_market(texture.debug_name) : classify(texture.debug_name);'),(
        '    if (name=="wascity-ocean-shore-rocks" ||\n'
        '        name=="wascity-ground2ocean-shore-rocks" ||\n'
        '        name=="wascity-rock-small" || name=="wascity-outerwall-rock") return 7;\n'
        '    if (name=="wascity-roof-1" || name=="city-slum-burning-can" ||\n'
        '        name=="wascity-outerwall-metal" || name=="wascity-outerwall-metal-b" ||\n'
        '        name=="wascity-metal-dirty") return 3;\n'
        '    if (name=="wascity-ground-01" || name=="wascity-cement-road" ||\n'
        '        name=="wascity-stucco-wall-bleached-01" || name=="wascitya-stone-top" ||\n'
        '        name=="wascitya-stone-bottom" || name=="wascity-stonewall-bricks" ||\n'
        '        name=="wascity-stucco-wall-bleached-2-bricks-01" ||\n'
        '        name=="wascity-ditch-wall-top-to-ground" || name=="wascity-stone-plain-wall-3" ||\n'
        '        name=="wascity-ground-2-ditch-03" || name=="wascity-ground-2-ditch-04" ||\n'
        '        name=="wascity-ground-2-ditch-05" || name=="wascity-stone-bricks-2-plain") return 1;\n',
        '')]
    for added,original in replacements:
        check(new.count(added)==1,'Environment material response exceeds its exact city allowlist')
        new=new.replace(added,original,1)
    check(new==old,'Environment material response changed accepted bind/palace classification/source')
    return {relative:before}


def verify_wind_frame(check,matches,predecessors=None):
    record=load(HERE/'wind-material-frame.json')
    replacements=material_response_baseline(check,matches,predecessors)
    apply=module(HERE/'apply_market_wind_frame.py','bounded_market_wind')
    check(set(record['files'])==set(apply.EDITS),'Wind frame manifest changed its file scope')
    for relative,entry in record['files'].items():
        target=replacements.get(relative,ROOT/relative)
        # When ENV extends PalaceMaterials, its exact predecessor must equal the
        # final wind-frame header. The new header is independently checked above.
        matches(target,entry['after_sha256'])
        raw=target.read_bytes();newline='\r\n'if b'\r\n'in raw else '\n'
        for before,after in reversed(apply.EDITS[relative]):
            before=before.replace('\n',newline).encode();after=after.replace('\n',newline).encode()
            check(raw.count(after)==1,'Missing/duplicate bounded wind frame insertion')
            raw=raw.replace(after,before,1)
        check(digest(raw)==entry['before_sha256'],'Wind frame inverse changed unrelated accepted source')
