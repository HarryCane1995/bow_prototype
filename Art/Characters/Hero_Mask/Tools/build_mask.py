"""Standalone mask visual source. Explicit rebuilds only; no rig, UV or export."""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from mask_surfaces import *
OUT=HERE.parent;REPO=OUT.parents[2]
STAGE=int(sys.argv[sys.argv.index('--stage')+1]) if '--stage' in sys.argv else 1
SOURCE=OUT/'Hero_Mask_Visual.blend'
if SOURCE.exists() and '--rebuild' not in sys.argv:raise RuntimeError('Rebuilding requires --rebuild. Manual edits remain source of truth otherwise.')
# Inspect the existing mannequin mask as a source reference, without altering it.
if STAGE==1:
 bpy.ops.wm.open_mainfile(filepath=str(REPO/'Assets/Models/Characters/Hero/Hero_Kaze.blend'))
 old=bpy.data.objects.get('Mask');print('V0_MASK_INSPECT',old.name,len(old.data.vertices),len(old.data.polygons),list(old.dimensions))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.name='MASK_VISUAL_ONLY';sc.unit_settings.system='METRIC'
collections={}
for name in ['01_InnerStructure','02_FrontShell','03_SideShell','04_RearShell','05_Visor','06_Vents','07_Fasteners','90_Reference']:
 c=bpy.data.collections.new(name);sc.collection.children.link(c);collections[name]=c
M={
 'metal':material('MASK / satin graphite titanium','33363B',.62,.40),
 'edge':material('MASK / machined edge alloy','474B50',.72,.34),
 'dark':material('MASK / carbon polymer','101319',.20,.53),
 'rubber':material('MASK / flexible inner gasket','080A0D',.03,.77),
 'vent':material('MASK / dark vent alloy','282E34',.75,.42),
 'orange':material('MASK / amber hardware','A44C14',.55,.43),
 'sensor':material('MASK / amber optical slit','FF7309',.15,.27),
}
bs=M['sensor'].node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Color'].default_value=(1,.23,.008,1);bs.inputs['Emission Strength'].default_value=2.8
frontcol=collections['02_FrontShell'];sidecol=collections['03_SideShell'];rearcol=collections['04_RearShell']
# A thin, shaped internal liner, with the lower rear open for a neck aperture.
verts=[];faces=[];RINGS=51;N=96
for j in range(RINGS):
 z=.002+.312*j/(RINGS-1);rx,yf,ys,yb=profile(z)
 for i in range(N):
  a=math.tau*i/N;x=rx*math.sin(a)*.96
  y=front(x,z).y+.0038 if math.cos(a)>=0 else ys+(yb-ys)*(-math.cos(a))*.955-.002
  verts.append((x,y,z))
for j in range(RINGS-1):
 z=.002+.312*(j+.5)/(RINGS-1)
 for i in range(N):
  a=math.tau*(i+.5)/N
  if z<.104 and math.cos(a)<-.03:continue
  faces.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
core=mesh('Inner structural liner',verts,faces,M['rubber'],collections['01_InnerStructure'])
mod=core.modifiers.new('Liner wall','SOLIDIFY');mod.thickness=.0016

# Deliberate plate boundary design. The diagonally rising lower brow edge is the
# upper lip of the optical recess, not a glowing decal on a closed helmet surface.
shapes={
 'Crown forehead':[(.0015,.310),(.027,.297),(.053,.267),(.057,.239),(.003,.218)],
 'Main brow shield':[(.003,.215),(.057,.237),(.083,.205),(.074,.175),(.025,.096),(.004,.123)],
 'Temple crown rail':[(.061,.247),(.083,.270),(.095,.227),(.089,.202),(.080,.209)],
 'Lower cheek guard':[(.013,.012),(.042,.044),(.069,.098),(.086,.148),(.083,.174),(.075,.170),(.029,.090)],
 'Jaw keel':[(.002,.119),(.022,.090),(.022,.046),(.007,.007),(.001,.002)],
}
for s,label in [(-1,'L'),(1,'R')]:
 for name,points in shapes.items():
  coords=[(s*x,z) for x,z in points]
  panel(name+' '+label,coords,lambda x,z:front(x,z,.0015),M['metal'],frontcol,density=8)
 # Rim / socket lie behind the two major plates. Thin amber lance is recessed.
 aperture=[(.024,.095),(.033,.098),(.074,.168),(.072,.174),(.064,.164),(.028,.109)]
 panel('Optical well '+label,[(s*x,z) for x,z in aperture],lambda x,z:front(x,z,.0003),M['dark'],collections['05_Visor'],thick=.0014,bevel=.00035,density=6)
 slit=[(.029,.101),(.036,.109),(.067,.163),(.063,.153),(.034,.103)]
 panel('Amber sensor '+label,[(s*x,z) for x,z in slit],lambda x,z:front(x,z,.0010),M['sensor'],collections['05_Visor'],thick=.0008,bevel=.00014,density=8)
 # A side bridge above the vent and a layered jaw cradle below it.
 pieces={
  'Temporal upper shell':[(-.005,.268),(.040,.287),(.080,.262),(.103,.221),(.040,.210),(.004,.225)],
  'Occipital cheek bridge':[(.047,.207),(.102,.214),(.098,.166),(.072,.124),(.056,.143)],
  'Mandible side rail':[(-.037,.073),(-.003,.096),(.040,.127),(.049,.150),(.029,.148),(-.002,.116),(-.033,.091)],
 }
 for name,pts in pieces.items():panel(name+' '+label,pts,lambda y,z,s=s:side(y,z,s,.0015),M['metal'],sidecol,density=7)
 # Surround the side vent with an open frame; preserve a dark structural recess.
 ventpts=[(-.006,.205),(.040,.198),(.056,.150),(.022,.148),(-.018,.183)]
 panel('Vent recess '+label,ventpts,lambda y,z,s=s:side(y,z,s,-.0015),M['dark'],collections['06_Vents'],thick=.001,bevel=.0004,density=8)
 for k in range(len(ventpts)):
  a,b=ventpts[k],ventpts[(k+1)%len(ventpts)];path=[side(a[0]+(b[0]-a[0])*t/12,a[1]+(b[1]-a[1])*t/12,s,.0028) for t in range(13)]
  curve('Vent lip %s %d'%(label,k),path,.0010,M['edge'],sidecol)
 # Rear cheeks leave the central spine and ventilation zones readable.
 panel('Rear side shell '+label,[(s*.030,.115),(s*.056,.147),(s*.067,.224),(s*.043,.27),(s*.016,.278),(s*.028,.222)],lambda x,z:rear(x,z,.002),M['metal'],rearcol,density=8)

panel('Rear axial cap',[(-.013,.289),(0,.312),(.013,.289),(.022,.249),(.014,.220),(-.014,.220),(-.022,.249)],lambda x,z:rear(x,z,.003),M['metal'],rearcol,density=8)
panel('Rear service spine',[(-.012,.217),(.012,.217),(.017,.145),(.025,.123),(.018,.097),(-.018,.097),(-.025,.123),(-.017,.145)],lambda x,z:rear(x,z,.005),M['metal'],rearcol,density=8)
# Technical inner neck seal, no head or neck anatomy.
path=[]
for i in range(97):
 a=math.tau*i/96;path.append((.044*math.cos(a),.024+.037*math.sin(a),.072+.022*math.sin(a)))
curve('Open neck gasket',path,.0045,M['rubber'],collections['01_InnerStructure'])

if STAGE>=2:
 # Corrections are applied consistently to every surface/edge before later detail.
 # Narrower frontal width; extend the prow down and forward, calm the crown horns.
 def correction(v):
  v=V(v);v.x*=.96
  if v.z<.13:
   t=(.13-v.z)/.13;v.z-=.012*t;v.y-=.008*t
  if v.z>.245 and abs(v.x)>.062:v.z-=.005*min(1,(abs(v.x)-.062)/.025)
  return v
 for o in list(sc.objects):
  if o.type=='MESH':
   for v in o.data.vertices:v.co=correction(v.co)
  elif o.type=='CURVE':
   for spline in o.data.splines:
    for p in spline.points:p.co=(*correction(p.co.xyz),1)

if STAGE>=3:
 # Final surface / mechanical detail is implemented separately from the silhouette.
 from mask_detail import detail_pass
 detail_pass(sc,M,collections)

refimg=bpy.data.images.load(str(OUT/'Mask_Concept_Reference.png'));refimg.filepath='//Mask_Concept_Reference.png'
ref=bpy.data.objects.new('Mask concept / reference only',None);collections['90_Reference'].objects.link(ref);ref.empty_display_type='IMAGE';ref.data=refimg;ref.empty_display_size=.45;ref.location=(.37,.14,.15);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
sc['visual_pass_stage']=STAGE;sc['scope']='Standalone mask only. No hair/body/rig/UV/bake/export/Godot.'
readme=bpy.data.texts.new('READ_ME_MASK');readme.write('MASK / standalone hero visual study\nBlender metres. Front -Y; up Z. No head, hair, rig or gameplay integration.\nShell pieces retain Solidify, bevel and weighted-normal stacks. Major surfaces are separately editable.\nProcedural object-space preview shaders, no UV or baking.\nReference image is a non-rendered image empty, never a model texture.\nDo not rebuild this file after manual edits unless you intentionally want the generator state.\n')
sc.world=bpy.data.worlds.new('Mask studio environment');sc.world.color=(.05,.05,.05)
for o in bpy.context.selected_objects:o.select_set(False)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   s=area.spaces.active;s.region_3d.view_location=(0,0,.15);s.region_3d.view_distance=.60;s.region_3d.view_rotation=V((.50,-1,.24)).to_track_quat('Z','Y');s.shading.type='MATERIAL';s.overlay.show_overlays=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print('MASK_SAVED_STAGE',STAGE,len([o for o in sc.objects if o.type=='MESH']),'meshes')
