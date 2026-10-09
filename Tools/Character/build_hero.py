"""Hero production foundation. Run in a separate Blender process, never the user's scene.
Rebuild is explicit; source remains directly editable after this authored first pass.
"""
import bpy, math, sys, json, random
from pathlib import Path
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).parent))
from hero_geometry import Builder, V, bv, gv, rig_from_points, arm_parts
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Assets/Models/Characters/Hero/Hero_Kaze.blend'
if OUT.exists() and '--rebuild' not in sys.argv:raise RuntimeError('Use -- --rebuild only for an intentional source regeneration.')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.name='KAZE_HERO';scene.unit_settings.system='METRIC';scene.render.fps=30
B=Builder()
points={
 'Root':((0,0,0),(0,.18,0),None),
 'Pelvis':((0,.96,0),(0,1.09,0),'Root'),
 'Spine':((0,1.09,0),(0,1.29,0),'Pelvis'),
 'Chest':((0,1.29,0),(0,1.54,0),'Spine'),
 'Neck':((0,1.54,0),(0,1.68,0),'Chest'),
 'Head':((0,1.68,0),(0,1.91,0),'Neck'),
 'BackModule':((0,1.42,.15),(0,1.56,.15),'Chest'),
 'Jacket.L':((-.16,1.42,.0),(-.21,1.13,.0),'Chest'),
 'Jacket.R':((.16,1.42,.0),(.21,1.13,.0),'Chest'),
}
arm_points={}
for side,sign in [('L',-1),('R',1)]:
 sh=(sign*.278,1.51,0);el=(sign*.423,1.25,.005);wr=(sign*.51,1.005,-.015);ha=(sign*.551,.90,-.027);fi=(sign*.566,.827,-.045);th=(sign*.505,.891,-.09)
 arm_points[side]=dict(zip(['shoulder','elbow','wrist','hand','finger','thumb'],[sh,el,wr,ha,fi,th]))
 points['Clavicle.'+side]=((sign*.06,1.51,0),sh,'Chest')
 for name,a,b,parent in [('Upper',sh,el,'Clavicle'),('Forearm',el,wr,'Upper'),('Hand',wr,ha,'Forearm'),('Fingers',ha,fi,'Hand'),('Thumb',(sign*.528,.97,-.04),th,'Hand')]:points[name+'.'+side]=(a,b,parent+'.'+side)
 hip=(sign*.112,.99,.01);knee=(sign*.148,.55,-.018);ankle=(sign*.154,.14,.025);toe=(sign*.154,.07,-.16)
 for name,a,b,parent in [('Thigh',hip,knee,'Pelvis'),('Shin',knee,ankle,'Thigh.'+side),('Foot',ankle,toe,'Shin.'+side),('Toe',toe,(sign*.154,.065,-.235),'Foot.'+side)]:points[name+'.'+side]=(a,b,parent)
rig=rig_from_points('HeroRig',points)

def torso_weights(i,p):
 if p.y<1.07:return {'Pelvis':1}
 if p.y<1.24:
  t=(p.y-1.07)/.17;return {'Pelvis':1-t,'Spine':t}
 if p.y<1.38:
  t=(p.y-1.24)/.14;return {'Spine':1-t,'Chest':t}
 return {'Chest':1}

# Continuous tailored torso: loop density is concentrated at the waist and shoulders.
B.loft('Undersuit',[( (0,y,z),x,d) for y,x,d,z in [(.93,.155,.105,0),(1.01,.165,.118,0),(1.09,.166,.113,0),(1.18,.18,.122,0),(1.30,.221,.131,0),(1.40,.251,.137,0),(1.48,.247,.122,.005),(1.535,.206,.104,.01),(1.57,.112,.079,0)]],'Fabric',torso_weights,24)
B.loft('NeckSeal',[((0,1.54,0),.074,.064),((0,1.63,0),.061,.06),((0,1.68,0),.063,.06)],'Rubber','Neck',20)
for side,s in [('L',-1),('R',1)]:
 B.panel('SuitPanels',[(s*x,y,z) for x,y,z in [(.02,1.43,-.139),(.085,1.51,-.119),(.206,1.46,-.111),(.212,1.36,-.117),(.124,1.32,-.138),(.028,1.34,-.143)]],.007,'FabricPanel','Chest')
 B.ribbon('Harness',[(s*.09,1.56,-.093),(s*.151,1.41,-.143),(s*.105,1.21,-.131)],[.035,.041,.03],'Rubber','Chest')
 B.panel('SuitPanels',[(s*x,y,z) for x,y,z in [(.02,1.28,-.132),(.12,1.28,-.125),(.15,1.20,-.121),(.08,1.18,-.13),(.02,1.22,-.13)]],.005,'FabricPanel','Spine')

# Pants: each thigh is an organic shaped tube with large low-amplitude fabric folds.
for side,s in [('L',-1),('R',1)]:
 hip,knee,_=points['Thigh.'+side];_,ankle,_=points['Shin.'+side]
 h,k,a=map(V,[hip,knee,ankle]);thigh='Thigh.'+side;shin='Shin.'+side;foot='Foot.'+side
 def thigh_weights(i,p,side=side):
  t=max(0,min(1,(.99-p.y)/.18));return {'Pelvis':(1-t)*.35,'Thigh.'+side:1-(1-t)*.35}
 B.tube('Pants_'+side,h,k,[(0,.106,.112),(.10,.121,.125),(.25,.120,.123),(.40,.111,.112),(.54,.107,.102),(.67,.099,.091),(.71,.108,.099),(.77,.088,.086),(.84,.094,.085),(.94,.078,.075),(1,.075,.072)],'Fabric',thigh_weights,20)
 B.tube('Pants_'+side,k,a,[(0,.073,.072),(.08,.078,.074),(.16,.087,.083),(.28,.088,.082),(.51,.076,.073),(.71,.063,.059),(.77,.068,.061),(.84,.057,.052),(1,.05,.051)],'Fabric',shin,16)
 B.panel('Pants_'+side,[(s*x,y,z) for x,y,z in [(.188,.90,-.047),(.25,.86,-.042),(.228,.725,-.062),(.176,.70,-.072),(.164,.765,-.081)]],.012,'FabricPanel',thigh,normal=(s*.6,0,-.8),bevel=.1)
 # Large diagonal fabric crease planes around the knee.
 for j in range(3):
  y=.65+j*.075;x=s*(.153+j*.004)
  B.ribbon('Pants_'+side,[(x-s*.052,y+.022,-.078),(x,y,-.11),(x+s*.065,y+.014,-.064)],[.009,.014,.006],'FabricPanel',thigh)
 # Slim external knee shell: a human-sized joint with side hinge disks.
 B.panel('LegHardware_'+side,[(s*.148+dx,y,z) for dx,y,z in [(-.054,.598,-.077),(-.064,.55,-.10),(-.045,.498,-.082),(.037,.495,-.082),(.065,.548,-.10),(.043,.601,-.077)]],.027,'Graphite',shin,bevel=.17)
 B.panel('LegHardware_'+side,[(s*.148+dx,y,z) for dx,y,z in [(-.036,.575,-.105),(-.032,.531,-.114),(.022,.517,-.105),(.04,.559,-.113),(.019,.581,-.105)]],.009,'Steel',shin)
 for sg in [-1,1]:
  c=V((s*.148+sg*.067,.548,-.011));B.rod('LegHardware_'+side,c,c+V((sg*.019,0,0)),.027,'Graphite',shin,16)
 # Split shin armour leaves visible black calf mass and a functional shock strut.
 B.panel('LegHardware_'+side,[(s*.154+dx,y,z) for dx,y,z in [(-.055,.477,-.073),(-.066,.428,-.08),(-.041,.204,-.058),(-.015,.164,-.052),(.009,.203,-.063),(.023,.447,-.084),(.006,.486,-.077)]],.019,'Steel',shin,bevel=.13)
 B.panel('LegHardware_'+side,[(s*.154+dx,y,z) for dx,y,z in [(.036,.464,-.074),(.061,.428,-.055),(.047,.224,-.041),(.028,.197,-.06),(.019,.252,-.08)]],.018,'Graphite',shin)
 B.ribbon('LegHardware_'+side,[(s*.154-.045,.433,-.097),(s*.154-.024,.246,-.078)],[.015,.012],'Orange',shin)
 B.rod('LegHardware_'+side,(s*.154+.051,.394,-.015),(s*.154+.043,.235,-.003),.009,'Orange',shin)
 B.rod('LegHardware_'+side,(s*.154+.048,.31,-.011),(s*.154+.042,.18,.00),.0055,'Steel',shin)
 # Purpose-shaped boots: sole footprint + multiple contour sections, not box feet.
 x=s*.154
 def bootloft(group,rings,material):
  vs=[];fs=[];outline=[(-.70,-1),(-1,-.63),(-1,.45),(-.69,1),(.68,1),(1,.47),(1,-.65),(.70,-1)]
  for y,wid,length,z in rings:
   vs.extend([(x+u*wid,y,z+v*length) for u,v in outline])
  for j in range(len(rings)-1):
   for i in range(8):fs.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
  fs.extend([tuple(reversed(range(8))),tuple((len(rings)-1)*8+i for i in range(8))]);B.add(group,vs,fs,material,foot)
 bootloft('Boots_'+side,[(.025,.077,.174,-.075),(.045,.083,.18,-.075),(.065,.079,.176,-.075)],'Rubber')
 bootloft('Boots_'+side,[(.065,.075,.171,-.073),(.097,.075,.158,-.073),(.13,.062,.115,-.032),(.19,.054,.067,.016),(.215,.055,.065,.017)],'FabricPanel')
 B.panel('Boots_'+side,[(x+dx,y,z) for dx,y,z in [(-.064,.092,-.236),(-.06,.126,-.204),(.055,.126,-.204),(.066,.093,-.237),(.044,.071,-.252),(-.043,.071,-.252)]],.012,'Graphite',foot,bevel=.16)
 B.ribbon('Boots_'+side,[(x-.052,.081,-.25),(x-.056,.066,-.242),(x+.036,.063,-.245)],[.009,.012,.009],'Orange',foot)
 for y,z in [(.145,-.102),(.174,-.06)]:B.ribbon('Boots_'+side,[(x-.052,y,z),(x,y+.008,z-.012),(x+.052,y,z)],[.018,.018,.018],'Rubber',foot)

B.loft('PantsPelvis',[((0,.92,.02),.148,.104),((0,1.015,.0),.172,.123),((0,1.05,0),.169,.114)],'Fabric','Pelvis',24)
B.loft('Belt',[((0,1.037,0),.173,.122),((0,1.080,0),.171,.120)],'Rubber','Pelvis',24,True)
B.panel('Belt',[(-.027,1.038,-.127),(-.027,1.081,-.123),(.027,1.081,-.123),(.027,1.038,-.127)],.012,'Steel','Pelvis')
for side,s in [('L',-1),('R',1)]:
 B.panel('Belt',[(s*x,y,z) for x,y,z in [(.10,1.04,-.10),(.103,1.10,-.095),(.159,1.095,-.065),(.164,1.023,-.07)]],.028,'Graphite','Pelvis',normal=(s*.5,0,-.86))

for side in ['L','R']:arm_parts(B,side,arm_points[side])

# Open cloth jacket: curved cross sections with an intentional front gap.
verts=[];faces=[];n=24
for j,(y,rx,rz,gap) in enumerate([(1.15,.229,.157,.63),(1.19,.226,.162,.57),(1.31,.255,.167,.49),(1.43,.284,.160,.45),(1.51,.268,.142,.40),(1.555,.19,.102,.30)]):
 for i in range(n+1):
  a=gap+(math.tau-2*gap)*i/n
  x=rx*math.sin(a);z=-rz*math.cos(a)
  # Broad, asymmetric folds and irregular hem edge distinguish fabric from a shell.
  if j<4:z+=.010*math.sin(a*5+j*.8);x+=.006*math.sin(a*4+j)
  yy=y+(.013*math.cos(a*3) if j==0 else 0)
  verts.append((x,yy,z))
for j in range(5):
 for i in range(n):faces.append((j*(n+1)+i,j*(n+1)+i+1,(j+1)*(n+1)+i+1,(j+1)*(n+1)+i))
def jacket_weight(i,p):
 t=max(0,min(.65,(1.43-p.y)*2.5));return {'Chest':1-t,('Jacket.L' if p.x<0 else 'Jacket.R'):t}
B.add('JacketBody',verts,faces,'Jacket',jacket_weight,True)
# Folded lapels / raised collar, broad enough to frame the mask.
for side,s in [('L',-1),('R',1)]:
 B.panel('JacketLapels',[(s*x,y,z) for x,y,z in [(.062,1.62,-.081),(.139,1.60,-.08),(.21,1.45,-.12),(.165,1.42,-.19),(.122,1.51,-.156)]],.008,'JacketEdge','Chest',bevel=.03)
 B.ribbon('JacketLapels',[(s*.126,1.51,-.166),(s*.113,1.40,-.176),(s*.13,1.28,-.174),(s*.135,1.16,-.152)],[.018,.013,.012,.018],'JacketEdge',{'Chest':.7,'Jacket.'+side:.3})
 B.ribbon('JacketBody',[(s*.224,1.18,-.026),(s*.24,1.27,-.04),(s*.267,1.39,-.031)],[.009,.007,.006],'JacketEdge',{'Chest':.65,'Jacket.'+side:.35})
# Rear collar folds.
collar_v=[];collar_f=[]
for y,rx,rz in [(1.548,.11,.098),(1.60,.105,.102),(1.626,.111,.10)]:
 for i in range(19):
  an=.73+(math.tau-1.46)*i/18;collar_v.append((rx*math.sin(an),y,-rz*math.cos(an)+.008))
for j in range(2):
 for i in range(18):collar_f.append((j*19+i,j*19+i+1,(j+1)*19+i+1,(j+1)*19+i))
B.add('Collar',collar_v,collar_f,'JacketEdge','Chest',True)

# Smooth predatory mask, custom ring contours and central prow.
B.loft('Mask',[((0,1.657,-.053),.019,.028),((0,1.70,-.028),.062,.078),((0,1.775,-.011),.094,.103),((0,1.84,.003),.095,.092),((0,1.885,.014),.070,.062),((0,1.902,.016),.026,.023)],'Graphite','Head',24)
B.panel('Mask',[(-.018,1.879,-.056),(.015,1.879,-.056),(.025,1.793,-.111),(.006,1.692,-.104),(-.011,1.671,-.082),(-.020,1.778,-.117)],.004,'Graphite','Head',bevel=.04)
B.panel('SensorSocket',[(.036,1.813,-.108),(.080,1.845,-.075),(.070,1.792,-.087),(.039,1.773,-.108)],.007,'Rubber','Head',bevel=.08)
B.panel('Sensor',[(.045,1.809,-.116),(.071,1.832,-.095),(.062,1.793,-.108),(.046,1.783,-.116)],.003,'Sensor','Head',bevel=.03)
# Layered hair clumps: swept cross-section loops, no alpha cards / hair simulation.
random.seed(13)
B.loft('Hair',[((0,1.82,.055),.085,.045),((0,1.88,.023),.096,.083),((-.012,1.926,.023),.058,.052)],'Rubber','Head',20)
for i in range(22):
 a=math.tau*i/22;start=V((.028+.035*math.cos(a),1.897+.010*math.sin(a),.017+.04*math.sin(a)))
 tip=V((-.08+.077*math.cos(a),1.81+.064*math.cos(a)-.016*(i%3),.018+.105*math.sin(a)))
 if i<7:tip=V((-.119-.010*(i%3),1.80+.012*i,-.08+.009*(i%4)))
 control=start.lerp(tip,.47)+V((-.031,.070,.005));vs=[];fs=[]
 for j,t in enumerate([0,.22,.48,.72,.9,1]):
  center=(1-t)**2*start+2*(1-t)*t*control+t*t*tip
  tangent=(2*(1-t)*(control-start)+2*t*(tip-control)).normalized()
  u=tangent.cross(V((0,1,0))).normalized();v=tangent.cross(u).normalized();width=(.025+.003*(i%3))*max(.02,math.sin((t*.85+.13)*math.pi))*(1-t*.7)
  for k in range(6):
   an=math.tau*k/6;vs.append(center+u*math.cos(an)*width+v*math.sin(an)*width*.37)
 for j in range(5):
  for k in range(6):fs.append((j*6+k,j*6+(k+1)%6,(j+1)*6+(k+1)%6,(j+1)*6+k))
 fs.extend([tuple(reversed(range(6))),tuple(30+k for k in range(6))]);B.add('Hair',vs,fs,'Rubber','Head')

# Asymmetric shoulder interface and compact rear reel.
B.panel('ShoulderInterface',[(-.245,1.556,-.073),(-.326,1.529,-.085),(-.364,1.446,-.071),(-.303,1.412,-.093),(-.248,1.45,-.104)],.025,'Steel','Upper.L',bevel=.17)
B.ribbon('ShoulderInterface',[(-.338,1.479,-.094),(-.315,1.433,-.11)],[.015,.013],'Orange','Upper.L')
B.panel('BackModule',[(-.099,1.48,.173),(-.092,1.565,.143),(.091,1.565,.143),(.103,1.477,.18),(.062,1.357,.193),(-.054,1.357,.193)],.055,'Graphite','BackModule',normal=(0,0,1),bevel=.15)
B.rod('BackModule',(.019,1.44,.189),(.019,1.44,.224),.068,'Rubber','BackModule',24)
B.rod('BackModule',(.019,1.44,.222),(.019,1.44,.233),.058,'Orange','BackModule',24)
B.rod('BackModule',(.019,1.44,.233),(.019,1.44,.240),.051,'Graphite','BackModule',24)
B.rod('BackModule',(.019,1.44,.239),(.019,1.44,.247),.020,'Steel','BackModule',16)
B.ribbon('BackModule',[(-.038,1.52,.175),(-.032,1.59,.146),(.008,1.603,.143)],[.021,.022,.020],'Orange','BackModule',normal=(0,0,1))
# Compact grapple hook silhouette attached to the pack (decorative only).
B.rod('BackModule',(.075,1.50,.20),(.106,1.596,.17),.012,'Steel','BackModule')
B.panel('BackModule',[(.103,1.579,.18),(.122,1.615,.17),(.145,1.612,.17),(.151,1.587,.18),(.135,1.602,.17),(.120,1.593,.18)],.012,'Graphite','BackModule',normal=(0,0,1))

objects=B.emit(rig)
for o in objects:
 if o.name=='JacketBody':
  mod=o.modifiers.new('Cloth edge thickness','SOLIDIFY');mod.thickness=.006;mod.offset=0
  bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_move_up(modifier=mod.name)
rig['asset_role']='Editable full-body hero foundation; visual only. Left mechanical / right human.'
rig['pose_library']='Named keyed readiness poses, not a locomotion animation set.'
from hero_poses import add_library
add_library(rig)
readme=bpy.data.texts.new('README_HERO');readme.write('KAZE / BowPrototype hero production foundation\nMetres. Godot -Z forward. Left cyber arm, right exposed forearm.\nSeparate logical surfaces; normalized explicit skin weights; UV islands for future texture painting.\nPrincipled solid PBR palette. No concept texture, cloth/hair simulation, collisions or gameplay code.\nEdit this source directly. Generator rebuild must be explicit and will replace manual edits.\n')
scene.world=bpy.data.worlds.new('HeroWorld');scene.world.color=(.055,.055,.055)
for o in bpy.context.selected_objects:o.select_set(False)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   space=area.spaces.active;space.region_3d.view_distance=3.3;space.region_3d.view_location=bv((0,1.05,0));space.shading.color_type='MATERIAL';space.shading.light='STUDIO';space.overlay.show_floor=False
   space.region_3d.view_rotation=V((0,-1,.13)).to_track_quat('Z','Y')
scene.render.engine='CYCLES';scene.cycles.samples=32
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
stats={'meshes':len(objects),'vertices':sum(len(o.data.vertices) for o in objects),'faces':sum(len(o.data.polygons) for o in objects),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects),'bones':len(rig.data.bones),'materials':list(B.materials),'height':max(v.co.z for o in objects for v in o.data.vertices)}
(ROOT/'.godot/hero-pass/hero-stats.json').write_text(json.dumps(stats,indent=2));print('HERO_SAVED',json.dumps(stats))
