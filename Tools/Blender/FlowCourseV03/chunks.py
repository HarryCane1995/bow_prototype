"""Save an evaluated section as a portable local .blend, without touching source meshes."""
import bpy, json
from pathlib import Path
from datetime import datetime
from common import *

def save_chunk(sid):
    obj,mod,ids=context();previous=mod[ids['Section Preview']]
    mesh=None;scene=None;piece=None
    try:
        set_controls(**{'Section Preview':sid+1})
        mesh=evaluated();meta=sections(mesh)[0];part=section_mesh(mesh,sid,relative=True)
        dest=ROOT/'Assets/Levels/Level_Freestyle_01/Sections/Source'
        dest.mkdir(parents=True,exist_ok=True);(dest/'.gdignore').touch()
        scene=bpy.data.scenes.new('FLOW_SECTION_%02d_%s'%(sid,meta['kind']))
        piece=bpy.data.objects.new(scene.name,part);scene.collection.objects.link(piece)
        piece['flow_section']=sid;piece['kind']=meta['kind'];piece['seed']=int(mod[ids['Seed']]);piece['layout_mode']=int(mod[ids['Layout Mode']])
        piece['original_entry']=meta['entry'];piece['local_exit']=[b-a for a,b in zip(meta['entry'],meta['exit'])]
        markers=[]
        for name,location in [('ENTRY',(0,0,0)),('EXIT',piece['local_exit'])]:
            marker=bpy.data.objects.new(name,None);scene.collection.objects.link(marker);marker.location=location;marker.empty_display_type='ARROWS';markers.append(marker)
        if meta['kind']=='GRAPPLE_CATCH':
            marker=bpy.data.objects.new('GrappleAnchor_SECTION',None);scene.collection.objects.link(marker);marker.location=[b-a for a,b in zip(meta['entry'],meta['anchor'])];markers.append(marker)
        path=dest/('%s_seed%d_%s.blend'%(scene.name,piece['seed'],datetime.now().strftime('%Y%m%d-%H%M%S-%f')))
        bpy.data.libraries.write(str(path),{scene},fake_user=True,compress=True)
        # Inspect the saved file's data-block directory rather than trusting a successful write.
        with bpy.data.libraries.load(str(path),link=False) as (available,loaded):
            assert scene.name in available.scenes and piece.name in available.objects
        return str(path)
    finally:
        set_controls(**{'Section Preview':previous})
        if scene:
            meshes=[o.data for o in scene.objects if o.type=='MESH']
            for o in list(scene.objects):bpy.data.objects.remove(o,do_unlink=True)
            bpy.data.scenes.remove(scene)
            for data in meshes:
                if not data.users:bpy.data.meshes.remove(data)
        if mesh:bpy.data.meshes.remove(mesh)
