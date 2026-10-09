"""Static concept-matching studies only. NO rigging, export or Godot integration.
V0 stays intact. One mesh set, three shape-key proportion variants, grey clay.
"""
import bpy,sys,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from hero_geometry import Builder,bv,gv,V
OUT=ROOT/'Art/Characters/Hero_Silhouette'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Assets/Models/Characters/Hero/Hero_Kaze.blend'))
rig=bpy.data.objects['HeroRig']
# Snapshot the V0 rest data only; no bones/weights/animation will be authored here.
rest={b.name:(gv(b.head_local),gv(b.tail_local)) for b in rig.data.bones}
source={o.name:{'verts':[gv(v.co) for v in o.data.vertices], 'weights':[{o.vertex_groups[w.group].name:w.weight for w in v.groups} for v in o.data.vertices]} for o in bpy.context.scene.objects if o.type=='MESH'}
remove=['SuitPanels','Harness','Belt','JacketBody','JacketSleeves','JacketLapels','Collar','ShoulderInterface','Hair','Sensor','SensorSocket','Pants_L','Pants_R','PantsPelvis']
for name in remove:
 o=bpy.data.objects.get(name)
 if o:bpy.data.objects.remove(o,do_unlink=True)
# Strip all armature binding in the study copy, preserving V0 on disk.
for o in list(bpy.context.scene.objects):
 if o.type=='MESH':
  o.parent=None
  for m in list(o.modifiers):o.modifiers.remove(m)
  o.vertex_groups.clear()
 else:bpy.data.objects.remove(o,do_unlink=True)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)

VARIANTS={
 'A_Concept':dict(height=2.00,waist=.77,chest=.94,hips=.85,thigh=.78,shin=.75,arm=.83,boot=.80,head=.85,shoulder=.253,leg=1.12,armspan=.355),
 'B_Powerful':dict(height=2.00,waist=.82,chest=1.01,hips=.90,thigh=.85,shin=.80,arm=.91,boot=.84,head=.87,shoulder=.270,leg=1.10,armspan=.380),
 'C_AnimeLean':dict(height=2.07,waist=.71,chest=.92,hips=.81,thigh=.73,shin=.70,arm=.78,boot=.77,head=.79,shoulder=.247,leg=1.20,armspan=.345),
}

def lerpmap(y,keys):
 if y<=keys[0][0]:return keys[0][1]+(y-keys[0][0])
 for (a,b),(c,d) in zip(keys,keys[1:]):
  if y<=c:return b+(d-b)*(y-a)/(c-a)
 return keys[-1][1]+(y-keys[-1][0])

def setup(cfg):
 H=cfg['height'];leg=cfg['leg'];chesty=H-.51;shouldery=H-.39;heady=H-.245
 torso_keys=[(0,0),(.14,.14),(.55,leg*.54),(.99,leg),(1.09,leg+.07),(1.29,chesty-.13),(1.51,shouldery),(1.68,heady),(1.93,H)]
 target={}
 for side,s in [('L',-1),('R',1)]:
  sh=V((s*cfg['shoulder'],shouldery-.015,0));el=V((s*(cfg['armspan']-.025),shouldery-.28,.005));wr=V((s*cfg['armspan'],leg-.10,-.012));ha=V((s*(cfg['armspan']+.012),leg-.205,-.025));fi=V((s*(cfg['armspan']+.014),leg-.265,-.035))
  for name,a,b in [('Upper',sh,el),('Forearm',el,wr),('Hand',wr,ha),('Fingers',ha,fi),('Thumb',wr.lerp(ha,.32)+V((-s*.014,0,-.018)),ha+V((-s*.028,.026,-.030)))]:target[name+'.'+side]=(a,b)
  h=V((s*.109*cfg['hips']/.85,leg,.01));k=V((s*.121*cfg['hips']/.85,leg*.54,-.018));a=V((s*.127*cfg['hips']/.85,.14,.025));t=V((a.x,.07,-.16*cfg['boot']))
  for name,a,b in [('Thigh',h,k),('Shin',k,a),('Foot',a,t),('Toe',t,t+V((0,0,-.06)))]:target[name+'.'+side]=(a,b)
 return torso_keys,target

def torso(v,cfg,keys):
 p=v.copy();p.y=lerpmap(v.y,keys)
 factor=cfg['waist'] if v.y<1.22 else cfg['waist']+(cfg['chest']-cfg['waist'])*min(1,(v.y-1.22)/.23)
 p.x*=factor;p.z*=.85 if v.y<1.27 else .94
 return p

def transformed(name,data,cfg):
 keys,target=setup(cfg);out=[]
 for v,weights in zip(data['verts'],data['weights']):
  if name in ['Mask','SensorSocket','Sensor','Hair']:
   p=v.copy();p.x*=cfg['head'];p.z=(p.z+.012)*cfg['head']-.012;p.y=cfg['height']-.245+(v.y-1.68)*.99;out.append(p);continue
  if name=='NeckSeal':
   p=torso(v,cfg,keys);p.x*=.87;p.z*=.87;out.append(p);continue
  if name=='Undersuit' or name=='PantsPelvis':out.append(torso(v,cfg,keys));continue
  if name=='BackModule':
   p=torso(v,cfg,keys);p.x*=.8;p.z=.12+(p.z-.12)*.70;out.append(p);continue
  p=V();total=0
  for bone,weight in weights.items():
   if bone not in target:p+=torso(v,cfg,keys)*weight;total+=weight;continue
   a,b=rest[bone];c,d=target[bone];axis=(b-a).normalized();t=(v-a).dot(axis)/(b-a).length
   off=v-a-axis*((v-a).dot(axis));rot=axis.rotation_difference((d-c).normalized())
   scale=cfg['arm'] if bone.startswith(('Upper','Forearm','Hand','Fingers','Thumb')) else cfg['thigh'] if bone.startswith('Thigh') else cfg['shin']
   if bone.startswith(('Foot','Toe')):
    new=c+(v-a)*cfg['boot']
   else:new=c.lerp(d,t)+(rot@off)*scale
   p+=new*weight;total+=weight
  out.append(p/max(total,1e-6))
 return out

# Existing decorative islands that made human clothing read as plate armour are
# removed from the silhouette copy. Keep only broad anatomy / selected augmentation.
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 d=source[o.name]
 # Large diagonal artificial crease strips / cargo plates distract in clay.
 if o.name.startswith('Pants_'):
  keep=[p.index for p in o.data.polygons if o.data.materials[p.material_index].name.endswith('Fabric')]
  import bmesh
  bm=bmesh.new();bm.from_mesh(o.data);bm.faces.ensure_lookup_table()
  bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in keep],context='FACES');bm.to_mesh(o.data);bm.free()
  # Rebuild source vertex references after removal from the unweighted static copy.
  # Coordinates are unchanged for retained vertices; nearest original lookup is exact.
  lookup={tuple(v):w for v,w in zip(d['verts'],d['weights'])};d={'verts':[gv(v.co) for v in o.data.vertices],'weights':[lookup[tuple(gv(v.co))] for v in o.data.vertices]}
 o.shape_key_add(name='Basis')
 for key,cfg in VARIANTS.items():
  shape=o.shape_key_add(name=key)
  for vertex,p in zip(shape.data,transformed(o.name,d,cfg)):vertex.co=bv(p)
 o.data.shape_keys.key_blocks['A_Concept'].value=1

# New broad cloth surfaces shared by the three studies. No detail pass.
def clothing(cfg):
 B=Builder();keys,target=setup(cfg);H=cfg['height'];ch=H-.39;hem=cfg['leg']+.145
 # Shaped open outer layer. Front edges hang away from the narrow abdomen;
 # upper rings roll onto the shoulder slope, hem hangs unevenly.
 n=32;vs=[];fs=[]
 for j,(y,rx,rz,gap) in enumerate([(hem-.035,.185,.135,.56),(hem+.025,.183,.145,.54),(ch-.17,.228,.143,.49),(ch-.085,.263,.139,.46),(ch-.015,.25,.112,.43),(ch+.032,.126,.08,.45)]):
  for i in range(n+1):
   a=gap+(math.tau-2*gap)*i/n;fac=cfg['chest'];x=rx*math.sin(a)*fac;z=-rz*math.cos(a)
   fold=(.009*math.sin(3*a+j*.8)+.006*math.sin(5*a-j*.3))*(1 if j<4 else .3)
   x+=fold*math.sin(a);z-=fold*math.cos(a)
   yy=y
   if j==0:yy+=.022*math.cos(2*a+.6)+.012*math.sin(3*a);z-=.012*math.cos(a)
   if j>=3:yy-=.022*abs(math.sin(a))
   vs.append((x,yy,z))
 for j in range(5):
  for i in range(n):fs.append((j*(n+1)+i,j*(n+1)+i+1,(j+1)*(n+1)+i+1,(j+1)*(n+1)+i))
 B.add('Study_Jacket',vs,fs,'Jacket',{},True)
 for side,s in [('L',-1),('R',1)]:
  sh,el=target['Upper.'+side];axis=(el-sh).normalized();front=V((0,0,-1));u=axis.cross(front).normalized();v=axis.cross(u).normalized()
  start=sh+V((-s*.027,.025,0));end=sh.lerp(el,.51 if side=='L' else .74);vs=[];fs=[];N=20
  for j,(t,r) in enumerate([(0,.018),(.14,.058),(.35,.083),(.60,.082),(.83,.074),(1,.079)]):
   for i in range(N):
    an=math.tau*i/N;radius=r*(cfg['arm']/.83)
    center=start.lerp(end,t);cloth=math.sin(an*3+j*.5)*.004
    pos=center+u*(math.cos(an)*(radius+cloth))+v*(math.sin(an)*(radius*.95+cloth))
    if j==5:pos+=axis*(.009*math.sin(an*2+.7))
    vs.append(pos)
  for j in range(5):
   for i in range(N):fs.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i))
  B.add('Study_Sleeves',vs,fs,'Jacket',{},True)
  # A genuinely folded lapel: curved grid, not an extruded armour polygon.
  rows=[((s*.052,ch+.092,-.072),(s*.103,ch+.106,-.04)),((s*.073,ch+.035,-.099),(s*.141,ch+.054,-.086)),((s*.084,ch-.04,-.13),(s*.145,ch-.025,-.153)),((s*.098,ch-.105,-.142),(s*.114,ch-.126,-.169))]
  vs=[];fs=[]
  for j,(a,b) in enumerate(rows):
   for i in range(4):
    t=i/3;p=V(a).lerp(V(b),t);p.z-=math.sin(t*math.pi)*.009;vs.append(p)
  for j in range(3):
   for i in range(3):fs.append((j*4+i,j*4+i+1,(j+1)*4+i+1,(j+1)*4+i))
  B.add('Study_Lapels',vs,fs,'Jacket',{},True)
 # Back collar continues the lapels; open at the throat.
 vs=[];fs=[]
 for j in range(3):
  for i in range(17):
   a=1.1+(math.tau-2.2)*i/16;vs.append(((.088+j*.006)*math.sin(a),ch+.023+j*.032,-(.073+j*.007)*math.cos(a)))
 for j in range(2):
  for i in range(16):fs.append((j*17+i,j*17+i+1,(j+1)*17+i+1,(j+1)*17+i))
 B.add('Study_Collar',vs,fs,'Jacket',{},True)
 # Continuous large trouser masses replace V0's stacked crease/plate silhouette.
 leg=cfg['leg'];hipscale=cfg['hips']/.85
 B.loft('Study_PantsPelvis',[((0,leg+.069,0),.145*hipscale,.094),((0,leg+.035,.009),.158*hipscale,.105),((0,leg-.025,.018),.184*hipscale,.116),((0,leg-.095,.015),.171*hipscale,.103),((0,leg-.16,.004),.110*hipscale,.075)],'Fabric',{},24)
 for side,s in [('L',-1),('R',1)]:
  hip,knee=target['Thigh.'+side];_,ankle=target['Shin.'+side]
  fac=cfg['thigh']/.78
  B.tube('Study_Pants',hip,knee,[(0,.080*fac,.09*fac),(.14,.094*fac,.104*fac),(.32,.096*fac,.103*fac),(.53,.089*fac,.091*fac),(.75,.071*fac,.073*fac),(.91,.065*fac,.067*fac),(1,.06*fac,.063*fac)],'Fabric',{},20)
  fac=cfg['shin']/.75
  B.tube('Study_Pants',knee,ankle,[(0,.059*fac,.061*fac),(.13,.065*fac,.067*fac),(.32,.064*fac,.062*fac),(.59,.050*fac,.053*fac),(.81,.043*fac,.046*fac),(1,.040*fac,.040*fac)],'Fabric',{},16)
 # Elbow skin blends the two anatomical segments; no armoured cuff on the human elbow.
 sh,el=target['Upper.R'];_,wr=target['Forearm.R'];fac=cfg['arm']/.83
 B.tube('Study_HumanElbow',sh.lerp(el,.82),el.lerp(wr,.21),[(0,.049*fac,.047*fac),(.23,.051*fac,.050*fac),(.52,.049*fac,.050*fac),(.78,.052*fac,.05*fac),(1,.052*fac,.050*fac)],'Skin',{},16)
 # Broad, asymmetric swept hair volumes. The scalp is covered; no small strands.
 B.loft('Study_Hair',[((-.005,H-.13,.037),.075*cfg['head']/.85,.064),((0,H-.065,.018),.080*cfg['head']/.85,.073),((-.014,H-.025,.018),.060*cfg['head']/.85,.052),((-.023,H-.009,.014),.030,.025)],'Rubber',{},18)
 for i in range(15):
  an=math.tau*i/15
  start=V((.035+.02*math.cos(an),H-.068+.016*math.sin(an),.018+.039*math.sin(an)))
  tip=V((-.09+.054*math.cos(an),H-.145+.056*math.cos(an),.015+.10*math.sin(an)))
  if i<6:tip=V((-.118-.008*(i%3),H-.182+.021*i,-.09+.012*(i%3)))
  control=start.lerp(tip,.42)+V((-.032,.097,-.007));vs=[];fs=[]
  for j,t in enumerate([0,.2,.46,.7,.9,1]):
   center=(1-t)**2*start+2*t*(1-t)*control+t*t*tip
   tang=(2*(1-t)*(control-start)+2*t*(tip-control)).normalized();u=tang.cross(V((0,1,0))).normalized();v=tang.cross(u).normalized()
   width=(.024+(i%3)*.006)*max(.012,math.sin((t*.88+.11)*math.pi))
   for k in range(6):
    a=math.tau*k/6;vs.append(center+u*math.cos(a)*width+v*math.sin(a)*width*.38)
  for j in range(5):
   for k in range(6):fs.append((j*6+k,j*6+(k+1)%6,(j+1)*6+(k+1)%6,(j+1)*6+k))
  fs.extend([tuple(reversed(range(6))),tuple(30+k for k in range(6))]);B.add('Study_Hair',vs,fs,'Rubber',{})
 return B
builders={name:clothing(cfg) for name,cfg in VARIANTS.items()}
base=builders['A_Concept'];cloth=base.emit()
pant_parts=[o for o in cloth if o.name in ['Study_Pants','Study_PantsPelvis']]
bpy.ops.object.select_all(action='DESELECT')
for o in pant_parts:o.select_set(True)
bpy.context.view_layer.objects.active=pant_parts[0];bpy.ops.object.join();pants=pant_parts[0];pants.name='Study_Trousers'
mod=pants.modifiers.new('Unify large cloth volumes','REMESH');mod.mode='VOXEL';mod.voxel_size=.011;mod.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=mod.name)
mod=pants.modifiers.new('Relax hip junction','SMOOTH');mod.factor=1.;mod.iterations=5;bpy.ops.object.modifier_apply(modifier=mod.name)
pants.shape_key_add(name='Basis')
for name,cfg in VARIANTS.items():
 shape=pants.shape_key_add(name=name)
 for v,src in zip(shape.data,pants.data.vertices):
  p=gv(src.co);oldy=p.y;leg=cfg['leg'];p.y=lerpmap(p.y,[(.14,.14),(.6048,leg*.54),(1.12,leg),(1.189,leg+.069)])
  if oldy>1.05:fac=cfg['hips']/.85;p.x*=fac;p.z*=fac
  else:
   s=1 if p.x>=0 else -1;fac=(cfg['thigh']/.78 if oldy>.62 else cfg['shin']/.75)
   centre=s*(.109 if oldy>.62 else .123);p.x=centre*(cfg['hips']/.85)+(p.x-centre)*fac;p.z*=fac
  v.co=bv(p)
pants.data.shape_keys.key_blocks['A_Concept'].value=1
cloth=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('Study_') and o!=pants]
for obj in cloth:
 obj.shape_key_add(name='Basis')
 for name,builder in builders.items():
  shape=obj.shape_key_add(name=name)
  for v,p in zip(shape.data,builder.groups[obj.name]['v']):v.co=bv(p)
 obj.data.shape_keys.key_blocks['A_Concept'].value=1
 if obj.name in ['Study_Jacket','Study_Sleeves','Study_Lapels','Study_Collar']:
  mod=obj.modifiers.new('Soft cloth contour','SUBSURF');mod.levels=1;mod.render_levels=1
  mod=obj.modifiers.new('Cloth thickness','SOLIDIFY');mod.thickness=.004;mod.offset=0

clay=bpy.data.materials.new('STUDY_GreyClay');clay.diffuse_color=(.34,.35,.36,1);clay.use_nodes=True
bs=clay.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.34,.35,.36,1);bs.inputs['Roughness'].default_value=.78
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  o.data.materials.clear();o.data.materials.append(clay)
  for p in o.data.polygons:p.material_index=0
  o['study_only']='A/B/C shape keys. No rig, export, game integration or production claim.'
# Orthographic concept image reference stays a non-rendered authoring empty.
img=bpy.data.images.load(str(OUT/'Concept_Reference.png'));img.filepath='//Concept_Reference.png'
ref=bpy.data.objects.new('Concept_reference',None);bpy.context.scene.collection.objects.link(ref);ref.empty_display_type='IMAGE';ref.data=img;ref.empty_display_size=2.3;ref.location=(1.7,.2,1.0);ref.rotation_euler=(math.pi/2,0,0);ref.hide_render=True
scene=bpy.context.scene;scene.name='HERO_SILHOUETTE_ONLY';scene['selected_variant']='A_Concept'
scene['STOP']='Await user selection after three proportion studies. Do not rig/export/integrate.'
readme=bpy.data.texts.new('READ_ME_SILHOUETTE');readme.write('V0 was a technical mannequin, NOT an approved production character.\nThis file is a static clay silhouette study with ONE topology and A/B/C shape keys.\nSet all A/B/C weights to zero, then enable exactly one variant on every mesh.\nA: closest proportion study; B: slightly more powerful; C: longest/leanest stylization.\nNo rigging, export or game integration permitted until human visual approval.\n')
for o in bpy.context.selected_objects:o.select_set(False)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Hero_Silhouette_ABC.blend'))
print('SILHOUETTE_STUDIES_SAVED',list(VARIANTS))
