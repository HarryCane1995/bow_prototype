"""Read-only inspection in a separate Blender process; never saves source."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'Art/Environment/Skyscrapers/Skyscraper_Kit.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
report=dict(source=source.relative_to(ROOT).as_posix(),scenes=list(bpy.data.scenes.keys()),
    objects=len(bpy.data.objects),meshes=len(bpy.data.meshes),
    roots=[dict(name=o.name,children=len(o.children)) for o in bpy.data.objects if o.parent is None],
    materials=list(bpy.data.materials.keys()),
    images=[dict(name=i.name,path=i.filepath) for i in bpy.data.images if i.source=='FILE'])
out=ROOT/'Art/Environment/Highrise100/QA';out.mkdir(parents=True,exist_ok=True)
(out/'existing_source_inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
