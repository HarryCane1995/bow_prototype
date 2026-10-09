"""Small editable surface builders shared by the hero and its FP representations.
Coordinates here use Godot's metres / Y-up / -Z forward; Blender conversion is local.
No imported asset, gameplay transform or generated Godot cache is edited.
"""
import bpy, math
from mathutils import Vector, Matrix

def bv(p): return Vector((p[0], -p[2], p[1]))
def gv(p): return Vector((p[0], p[2], -p[1]))
V=Vector
PALETTE={
 'Fabric':((.028,.031,.034),0,.86),
 'FabricPanel':((.048,.054,.060),0,.75),
 'Rubber':((.014,.018,.021),0,.73),
 'Graphite':((.075,.083,.091),.55,.40),
 'Steel':((.20,.22,.23),.72,.34),
 'Jacket':((.255,.119,.044),0,.82),
 'JacketEdge':((.37,.19,.075),0,.76),
 'Orange':((.80,.255,.025),.25,.44),
 'Skin':((.43,.30,.225),0,.67),
 'Sensor':((1,.30,.015),.2,.30),
 'Marking':((.43,.45,.43),.05,.71),
}

class Builder:
 def __init__(self):
  self.groups={}; self.materials={}
  for key,(c,m,r) in PALETTE.items():
   # Palette is specified as display sRGB; Principled inputs are scene-linear.
   c=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)
   mat=bpy.data.materials.new('M_Hero_'+key); mat.diffuse_color=(*c,1); mat.use_nodes=True
   bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1)
   bs.inputs['Metallic'].default_value=m;bs.inputs['Roughness'].default_value=r
   if key=='Sensor':bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=.65
   self.materials[key]=mat
 def add(self,group,verts,faces,material,bone,smooth=False):
  d=self.groups.setdefault(group,{'v':[],'f':[],'m':[],'w':[],'smooth':[]})
  offset=len(d['v']);d['v'].extend([V(v) for v in verts]);d['f'].extend([tuple(offset+i for i in f) for f in faces]);d['m'].extend([material]*len(faces));d['smooth'].extend([smooth]*len(faces))
  for i,v in enumerate(verts):d['w'].append(bone(i,V(v)) if callable(bone) else ({bone:1} if isinstance(bone,str) else bone))
 def loft(self,group,rings,material,bone,n=16,facets=False):
  # Ring: centre, horizontal width radius, depth radius. Designed profile loops.
  vs=[];fs=[]
  for j,(c,rx,rz) in enumerate(rings):
   for i in range(n):
    a=math.tau*i/n;vs.append(V(c)+V((rx*math.cos(a),0,rz*math.sin(a))))
  for j in range(len(rings)-1):
   for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
  fs.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
  self.add(group,vs,fs,material,bone,not facets)
 def tube(self,group,a,b,profile,material,bone,n=12,front=(0,0,-1),facets=False):
  a,b=V(a),V(b);axis=(b-a).normalized();v=V(front);v=(v-axis*v.dot(axis)).normalized()
  if v.length<.01:v=axis.cross(V((1,0,0))).normalized()
  u=axis.cross(v).normalized();vs=[];fs=[]
  for t,ru,rv in profile:
   for i in range(n):
    ang=math.tau*(i+.5)/n;vs.append(a.lerp(b,t)+u*(math.cos(ang)*ru)+v*(math.sin(ang)*rv))
  for j in range(len(profile)-1):
   for i in range(n):fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
  fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
  self.add(group,vs,fs,material,bone,not facets)
 def rod(self,g,a,b,r,mat,bone,n=10): self.tube(g,a,b,[(0,r*.8,r*.8),(.07,r,r),(.93,r,r),(1,r*.8,r*.8)],mat,bone,n)
 def panel(self,g,points,thickness,mat,bone,normal=(0,0,-1),bevel=.1):
  # Closed polygon with inset edge loops: broad intentional chamfer, not a cube.
  ps=[V(p) for p in points];c=sum(ps,V())/len(ps);normal=V(normal).normalized();vs=[];n=len(ps)
  for depth,inset in [(0,bevel),(-thickness*.22,0),(-thickness*.8,0),(-thickness,bevel)]:
   vs.extend([p.lerp(c,inset)+normal*depth for p in ps])
  fs=[tuple(reversed(range(n))),tuple(3*n+i for i in range(n))]
  for ring in range(3):
   for i in range(n):fs.append((ring*n+i,ring*n+(i+1)%n,(ring+1)*n+(i+1)%n,(ring+1)*n+i))
  self.add(g,vs,fs,mat,bone)
 def ribbon(self,g,centres,widths,mat,bone,normal=(0,0,-1),thickness=.006):
  ps=[V(x) for x in centres];side=[]
  for i,p in enumerate(ps):
   tangent=ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)]
   side.append(tangent.cross(V(normal)).normalized()*widths[i]*.5)
  vs=[]
  for p,s in zip(ps,side):vs.extend([p-s,p+s])
  for i in range(len(ps)-1):self.panel(g,[vs[2*i],vs[2*i+1],vs[2*i+3],vs[2*i+2]],thickness,mat,bone,normal,.025)
 def emit(self,rig=None):
  obs=[]
  for name,d in self.groups.items():
   mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata([bv(v) for v in d['v']],[],d['f']);mesh.update()
   obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
   keys=list(dict.fromkeys(d['m']))
   for m in keys:mesh.materials.append(self.materials[m])
   for p,m,s in zip(mesh.polygons,d['m'],d['smooth']):p.material_index=keys.index(m);p.use_smooth=s
   if rig:
    for bone in set(k for w in d['w'] for k in w):
     vg=obj.vertex_groups.new(name=bone)
     for i,w in enumerate(d['w']):
      if w.get(bone,0)>.0001:vg.add([i],w[bone],'REPLACE')
    obj.parent=rig;mod=obj.modifiers.new('Hero skin','ARMATURE');mod.object=rig
   # Explicit UV islands; smart project once on new authored surfaces only.
   bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
   bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False) if hasattr(bpy.ops.mesh,'normals_make_consistent') else None
   bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.018);bpy.ops.object.mode_set(mode='OBJECT')
   obs.append(obj)
  return obs

def rig_from_points(name,points):
 data=bpy.data.armatures.new(name);rig=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(rig)
 bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
 for key,(head,tail,parent) in points.items():
  b=data.edit_bones.new(key);b.head=bv(head);b.tail=bv(tail)
  if parent:b.parent=data.edit_bones[parent]
 bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
 return rig

def arm_parts(B,side,p,fp=False):
 s,e,w,h,f,t=[V(p[key]) for key in ['shoulder','elbow','wrist','hand','finger','thumb']]
 mech=side=='L';scale=.64 if fp else 1.;front=V((0,1,0) if fp else (0,0,-1))
 g='Arms_'+side;up='Upper.'+side;fore='Forearm.'+side;hand='Hand.'+side;fingers='Fingers.'+side;thumb='Thumb.'+side
 def prof(*rows):return [(a,b*scale,c*scale) for a,b,c in rows]
 B.tube(g,s,e,prof((0,.07,.075),(.12,.095,.085),(.32,.092,.086),(.65,.075,.071),(.9,.061,.06),(1,.06,.06)),'Rubber' if mech else 'Fabric',up,16,front)
 B.tube(g,e,w,prof((0,.057,.056),(.10,.068,.062),(.32,.071,.061),(.54,.06,.055),(.76,.045,.043),(1,.039,.037)),'Graphite' if mech else 'Skin',fore,16,front)
 if not fp:
  sleeve_end=s.lerp(e,.52 if mech else .71)
  B.tube('JacketSleeves',s,sleeve_end,[(0,.103,.103),(.12,.110,.104),(.46,.105,.103),(.7,.108,.098),(.82,.097,.095),(.93,.10,.094),(1,.097,.094)],'Jacket',up,16,front)
  B.tube('JacketSleeves',s.lerp(sleeve_end,.92),sleeve_end,[(0,.101,.099),(.3,.102,.10),(1,.10,.096)],'JacketEdge',up,16,front)
 else:
  B.tube(g,s,e,prof((0,.115,.105),(.4,.103,.099),(.73,.099,.085),(.82,.09,.079),(1,.084,.075)),'Jacket',up,16,front)
  B.tube(g,e.lerp(w,.01),e.lerp(w,.17),prof((0,.078,.071),(.3,.081,.074),(1,.07,.065)),'JacketEdge',fore,16,front)
 if mech:
  axis=(w-e).normalized();v=(front-axis*front.dot(axis)).normalized();u=axis.cross(v).normalized()
  for sign in [-1,1]:
   B.rod(g,e.lerp(w,.12)+u*.048*scale,w.lerp(e,.14)+u*.032*scale,.012*scale,'Steel',fore)
  pts=[e.lerp(w,t)+u*x*scale+v*y*scale for t,x,y in [(.1,-.051,.049),(.18,-.061,.058),(.66,-.046,.052),(.88,-.025,.04),(.88,.027,.04),(.35,.05,.058),(.13,.038,.053)]]
  B.panel(g,pts,.018*scale,'Graphite',fore,v,.18)
  B.ribbon(g,[e.lerp(w,.26)+v*.071*scale,e.lerp(w,.48)+v*.071*scale,e.lerp(w,.69)+v*.062*scale],[.018*scale]*3,'Orange',fore,v,.003)
  B.tube(g,e-V(axis)*.023*scale,e+axis*.024*scale,prof((0,.068,.065),(.2,.073,.069),(.8,.073,.069),(1,.067,.064)),'Rubber',fore,16,front)
 else:
  # A pair of tendons are large anatomical cues, not skin microdetail.
  axis=(w-e).normalized();v=(front-axis*front.dot(axis)).normalized();u=axis.cross(v).normalized()
  for sign in [-1,1]:B.rod(g,e.lerp(w,.43)+u*.016*scale*sign+v*.056*scale,e.lerp(w,.90)+u*.010*scale*sign+v*.036*scale,.0032*scale,'Skin',fore,8)
 B.tube(g,e.lerp(w,.87),w.lerp(h,.17),prof((0,.046,.043),(.18,.051,.049),(.78,.048,.045),(1,.043,.04)),'Rubber',fore,12,front)
 B.tube(g,w,h,prof((0,.041,.026),(.22,.048,.029),(.70,.050,.026),(1,.043,.021)),'Rubber',hand,12,front)
 hv=(h-w).normalized();vv=(front-hv*front.dot(hv)).normalized();uu=hv.cross(vv).normalized()
 B.panel(g,[w.lerp(h,a)+uu*x*scale+vv*y*scale for a,x,y in [(.25,-.033,.025),(.68,-.04,.027),(.85,-.03,.027),(.85,.03,.027),(.30,.032,.026)]],.011*scale,'Graphite',hand,vv,.17)
 # Four readable glove fingers, controlled in two broad groups in the full rig.
 for i in range(4):
  offset=uu*((i-1.5)*.021*scale);a=h+offset;end=f+offset*.87;mid=a.lerp(end,.52)+vv*.011*scale
  B.tube(g,a,mid,[(0,.010*scale,.012*scale),(.18,.011*scale,.012*scale),(.83,.009*scale,.011*scale),(1,.009*scale,.010*scale)],'Rubber',fingers,8,front)
  B.tube(g,mid,end,[(0,.009*scale,.010*scale),(.3,.01*scale,.01*scale),(1,.007*scale,.008*scale)],'Rubber',fingers,8,front)
  B.rod(g,a+vv*.012*scale,a.lerp(mid,.55)+vv*.012*scale,.006*scale,'Graphite',fingers,8)
 a=w.lerp(h,.35)+uu*.033*scale
 B.tube(g,a,t,[(0,.016*scale,.015*scale),(.4,.017*scale,.015*scale),(.76,.013*scale,.014*scale),(1,.012*scale,.011*scale)],'Rubber',thumb,10,front)
 B.ribbon(g,[w.lerp(h,-.18)+vv*.044*scale,w.lerp(h,-.02)+vv*.043*scale],[.012*scale,.012*scale],'Orange',fore,vv,.003)
