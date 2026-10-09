"""Eleven simple canonical primitives; V05's 42 forms are not modified."""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SPECS=[('PLATFORM_RECT',(10,6,.5)),('PLATFORM_WIDE',(18,10,.5)),('PLATFORM_NARROW',(24,4,.5)),('WALL_RECT',(12,.5,6)),('WALL_LONG',(24,.5,8)),('WALL_SHORT',(6,.5,4)),('RAMP_WEDGE',(6,6,6)),('STEEP_RAMP',(4,7,8)),('BRIDGE_STRIP',(20,3.5,.5)),('ARENA_SLAB',(60,60,.6)),('VERTICAL_PAD',(6,4.5,.55))]
def build():
    c=bpy.data.collections.get('V06_SIMPLE_PRIMITIVES')
    if not c:c=bpy.data.collections.new('V06_SIMPLE_PRIMITIVES');bpy.context.scene.collection.children.link(c)
    c.hide_viewport=True;c.hide_render=True;manifest=[]
    cube=[(x,y,z) for z in [-.5,.5] for y in [-.5,.5] for x in [-.5,.5]]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    wedge=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),(-.5,.5,-.5),(.5,.5,-.5),(.5,.5,.5)]
    wedgefaces=[(1,2,0),(5,4,3),(3,4,1,0),(4,5,2,1),(5,3,0,2)]
    for i,(name,dims) in enumerate(SPECS):
        objname='V06_PRIM_'+name;o=bpy.data.objects.get(objname)
        if not o:
            m=bpy.data.meshes.new(objname);vs,fs=(wedge,wedgefaces) if i in [6,7] else (cube,faces)
            m.from_pydata([tuple(p[k]*dims[k] for k in range(3)) for p in vs],[],fs);m.update()
            o=bpy.data.objects.new(objname,m);c.objects.link(o)
        o['primitive_id']=i;o['purpose']='Simple V06 blockout primitive; dimensions chosen by role and local space.'
        manifest.append({'id':i,'name':name,'object':objname,'dimensions':dims,'shape':'wedge' if i in [6,7] else 'box'})
    (ROOT/'Docs/Reviews/LocalProxyV06/active_primitives.json').write_text(json.dumps(manifest,indent=2))
    return manifest
