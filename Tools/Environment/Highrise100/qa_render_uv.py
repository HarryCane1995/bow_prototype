"""Actual Blender QA views; temporary checker and 1.8m marker are never saved."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
sys.path.insert(0,str(Path(__file__).resolve().parent));from build_library import aim
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
phase=args[0] if args else 'candidate';mode=args[1] if len(args)>1 else 'sample'
source=OUT/({'before':'Highrise100.blend','subset':'Highrise100_UV_Subset.blend','candidate':'Highrise100_UV_Candidate.blend','final':'Highrise100.blend'}[phase])
if phase=='before' and (QA/'PROMOTED.json').exists():source=QA/'Before/Highrise100.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
if source.parent!=OUT:
    for img in bpy.data.images:
        if img.source=='FILE':img.filepath=str(OUT/img.filepath.removeprefix('//').replace('\\','/'))
data=json.loads((QA/'Before/manifest.json').read_text())['buildings']
ids=['HR003','HR007','HR013','HR018','HR025','HR027','HR036','HR039','HR057','HR064','HR083','HR098','HR100']
scene=bpy.data.scenes['Neutral_Preview'];cam=scene.camera;inst=bpy.data.objects['PREVIEW_INSTANCE'];bpy.context.window.scene=scene
scene.eevee.taa_render_samples=16
folder=QA/('Views' if mode=='all' else phase.title());folder.mkdir(exist_ok=True)

def render_record(r,view,resolution=(480,600)):
    inst.instance_collection=bpy.data.collections[r['collection']]
    lo=Vector(r['bounds_min']);hi=Vector(r['bounds_max']);target=(lo+hi)*.5
    direction={'front':Vector((.9,-1.6,.72)),'back':Vector((-.9,1.6,.72)),'roof':Vector((.8,-1.1,1.75))}[view].normalized()
    cam.location=target+direction*1800;aim(cam,target)
    inv=cam.rotation_euler.to_matrix().transposed();pts=[inv@(Vector((x,y,z))-target) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
    cam.data.ortho_scale=max(max(q.y for q in pts)-min(q.y for q in pts),(max(q.x for q in pts)-min(q.x for q in pts))/(resolution[0]/resolution[1]))*1.13
    scene.render.resolution_x,scene.render.resolution_y=resolution
    path=(OUT/'Previews'/(r['id']+'.png')) if mode=='all' and view=='front' else folder/(r['id']+'_'+view+'.png')
    scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)

def make_human():
    m=bpy.data.materials.new('QA_ONLY_OrangeHuman_1_8m');m.diffuse_color=(1,.22,.015,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color
    objs=[]
    def ball(c,scale):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,location=c);o=bpy.context.object;o.scale=scale;objs.append(o);o.data.materials.append(m)
    def limb(a,b,r):
        a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=(b-a).length,location=(a+b)/2);o=bpy.context.object;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();objs.append(o);o.data.materials.append(m)
    ball((0,0,1.68),(.115,.105,.12));ball((0,0,1.24),(.23,.135,.29))
    for x in (-.105,.105):limb((x,0,.12),(x,0,1.01),.075);ball((x,-.05,.08),(.08,.15,.08))
    for sign in (-1,1):limb((sign*.2,0,1.43),(sign*.31,0,.91),.045)
    return objs

humans=make_human() if mode=='details' else []
positions=[]
for r in data:
    if mode!='all' and r['id'] not in ids:continue
    if mode=='details':
        col=bpy.data.collections[r['collection']];inst.instance_collection=col
        choices=[]
        for o in col.objects:
            if o.type!='MESH':continue
            for p in o.data.polygons:
                if p.normal.z>.999 and p.area>70 and (r['id']=='HR064' or '_Caps' in o.name or o.data.materials[p.material_index].name=='H100_floor_rooftop'):
                    pts=[o.matrix_world@o.data.vertices[i].co for i in p.vertices];z=sum(q.z for q in pts)/len(pts)
                    if z>r['bounds_m'][2]*.25:choices.append((z,p.area,pts,o.name,p.index))
        if not choices:continue
        z,area,pts,name,poly=max(choices,key=lambda item:(item[0],item[1]))
        x=sum(q.x for q in pts)/len(pts);y=min(q.y for q in pts)+min(2.,(max(q.y for q in pts)-min(q.y for q in pts))*.25)
        # QA marker only: HR098 has a narrower superstructure over this roof.
        # Stand on the exposed front-right corner instead of inside that mass.
        if r['id']=='HR098':x=max(q.x for q in pts)-.55;y=min(q.y for q in pts)+.55
        anchor=Vector((x,y,z))
        for o in humans:
            if 'base' not in o:o['base']=list(o.location)
            o.location=anchor+Vector(o['base'])
        target=anchor+Vector((0,0,-2));cam.location=target+Vector((12,-22,13));aim(cam,target);cam.data.ortho_scale=27
        scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.filepath=str(folder/(r['id']+'_player.png'));bpy.ops.render.render(write_still=True)
        positions.append(dict(id=r['id'],marker_height_m=1.8,anchor=list(anchor),roof_mesh=name,roof_face=poly))
    else:
        for view in (('front','back','roof') if mode=='all' else ('front','roof')):render_record(r,view,(640,800) if view=='front' else (480,600))
    print('QA_RENDER',phase,mode,r['id'],flush=True)
if positions:(folder/'player_positions.json').write_text(json.dumps(positions,indent=2))
print('QA_RENDERS_COMPLETE',phase,mode,flush=True)
