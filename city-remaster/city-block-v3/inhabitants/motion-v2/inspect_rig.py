from pathlib import Path
import bpy,json
HERE=Path(__file__).resolve().parent
out={}
for sex in ('male','female'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(HERE.parent/(sex+'-selected.glb')))
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    arm.animation_data_clear()
    for b in arm.pose.bones:b.matrix_basis.identity()
    bpy.context.view_layer.update()
    out[sex]={b.name:{'parent':b.parent.name if b.parent else None,'head':list(b.head),'tail':list(b.tail),'length':b.length} for b in arm.pose.bones}
(HERE/'rest-rig.json').write_text(json.dumps(out,indent=2))
