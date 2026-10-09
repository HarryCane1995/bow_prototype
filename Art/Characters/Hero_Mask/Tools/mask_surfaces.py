"""Editable parametric surface tools for the standalone visual mask.
Blender metres: X lateral, -Y face forward, Z up. No UV, rig or game export.
"""
import bpy,math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
V=Vector

PROFILE=[ # height, half-width, front, side, rear
 (0,.004,-.135,-.134,-.131),(.035,.025,-.132,-.090,-.030),
 (.070,.047,-.131,-.047,.036),(.110,.067,-.124,-.012,.075),
 (.160,.083,-.109,.010,.104),(.205,.094,-.079,.025,.113),
 (.245,.082,-.040,.040,.101),(.285,.054,-.002,.049,.073),
 (.310,.010,.039,.045,.052),(.318,.001,.047,.048,.049)]

def profile(z):
 for a,b in zip(PROFILE,PROFILE[1:]):
  if z<=b[0]:
   t=max(0,min(1,(z-a[0])/(b[0]-a[0])))
   return [a[j]+(b[j]-a[j])*t for j in range(1,5)]
 return list(PROFILE[-1][1:])

def front(x,z,offset=0):
 rx,yf,ys,yb=profile(z);t=abs(x)/max(rx,.001)
 # Broad controlled curvature. A distinct centre keel avoids a helmet bubble.
 y=yf+(ys-yf)*t**1.65
 return V((x,y-offset,z))

def side(y,z,sign=1,offset=0):
 rx,yf,ys,yb=profile(z)
 if y<ys:
  t=max(0,(y-yf)/max(.001,ys-yf));x=rx*t**(1/1.65)
 else:
  t=min(.98,(y-ys)/max(.001,yb-ys));x=rx*math.sqrt(max(.04,1-t*t))
 return V((sign*(x+offset),y,z))

def rear(x,z,offset=0):
 rx,yf,ys,yb=profile(z);t=min(.998,abs(x)/max(rx,.001))
 return V((x,ys+(yb-ys)*math.sqrt(max(.003,1-t*t))+offset,z))

def material(name,hexcolor,metal=.0,rough=.5):
 c=[int(hexcolor[i:i+2],16)/255 for i in (0,2,4)];c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*c,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 return m

def mesh(name,verts,faces,mat,collection,smooth=True):
 d=bpy.data.meshes.new(name+'_Surface');d.from_pydata(verts,[],faces);d.update()
 o=bpy.data.objects.new(name,d);collection.objects.link(o)
 if mat:d.materials.append(mat)
 for p in d.polygons:p.use_smooth=smooth
 return o

def panel(name,coords,surface,mat,collection,thick=.0024,bevel=.00065,density=5):
 """Tessellated surface patch with shared vertices, solidify, multi-segment bevel.
 Sampling curvature before thickness keeps broad plates smooth and edge tools editable.
 """
 ps=[V((x,z,0)) for x,z in coords];tris=tessellate_polygon([ps]);vs=[];fs=[];lookup={}
 def index(p):
  key=tuple(round(v,8) for v in p)
  if key not in lookup:lookup[key]=len(vs);vs.append(surface(p.x,p.y))
  return lookup[key]
 for tri in tris:
  a,b,c=[ps[i] for i in tri] if isinstance(tri[0],int) else tri
  idx={}
  for i in range(density+1):
   for j in range(density+1-i):idx[i,j]=index(a+(b-a)*(i/density)+(c-a)*(j/density))
  for i in range(density):
   for j in range(density-i):
    fs.append((idx[i,j],idx[i+1,j],idx[i,j+1]))
    if j<density-i-1:fs.append((idx[i+1,j],idx[i+1,j+1],idx[i,j+1]))
 o=mesh(name,vs,fs,mat,collection)
 # Recalculate on newly-authored geometry only. Thickening is outward-normal agnostic.
 import bmesh
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
 solid=o.modifiers.new('Shell wall / editable','SOLIDIFY');solid.thickness=thick;solid.offset=0
 edge=o.modifiers.new('Machined edge / editable','BEVEL');edge.width=bevel;edge.segments=4;edge.limit_method='ANGLE';edge.angle_limit=.50
 edge.harden_normals=True
 weighted=o.modifiers.new('Surface normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=30
 return o

def curve(name,pts,radius,mat,collection,resolution=3):
 d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.resolution_u=resolution;d.bevel_depth=radius;d.bevel_resolution=3
 sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,co in zip(sp.points,pts):p.co=(*co,1)
 o=bpy.data.objects.new(name,d);collection.objects.link(o);d.materials.append(mat);return o

def cylinder(name,center,normal,radius,depth,mat,collection,vertices=48):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=center)
 o=bpy.context.object;o.name=name;o.rotation_euler=V(normal).to_track_quat('Z','Y').to_euler()
 for c in list(o.users_collection):c.objects.unlink(o)
 collection.objects.link(o);o.data.materials.append(mat)
 mod=o.modifiers.new('Edge radius','BEVEL');mod.width=min(.0005,depth*.18);mod.segments=3
 o.modifiers.new('Surface normals','WEIGHTED_NORMAL')
 for p in o.data.polygons:p.use_smooth=True
 return o

def torus(name,center,normal,major,minor,mat,collection):
 bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=10,location=center,major_radius=major,minor_radius=minor)
 o=bpy.context.object;o.name=name;o.rotation_euler=V(normal).to_track_quat('Z','Y').to_euler()
 for c in list(o.users_collection):c.objects.unlink(o)
 collection.objects.link(o);o.data.materials.append(mat)
 for p in o.data.polygons:p.use_smooth=True
 return o
