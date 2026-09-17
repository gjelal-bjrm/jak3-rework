"""Repair saved inspection visibility only; never reauthor meshes or patches."""
from pathlib import Path
import bpy
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'wcb-complete-palms.blend'))
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':
        lod=int(obj['geom']);obj['native_lod']=lod
        obj.hide_render=lod!=0;obj.hide_set(lod!=0)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'wcb-complete-palms.blend'))
