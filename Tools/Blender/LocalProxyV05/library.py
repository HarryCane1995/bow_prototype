"""Low-poly gameplay vocabulary in real metre dimensions, built once, never at runtime."""
import bpy
import bmesh
import hashlib
import json
import math
from mathutils import Vector, Matrix

COLLECTION='V05_GAMEPLAY_MESH_LIBRARY'
FAMILIES=['LANDING','PLATFORM','WALL','RAMP','BRIDGE','SPEED','VERTICAL']


class Shape:
    def __init__(self):self.v=[];self.f=[]
    def part(self,vertices,faces,offset=(0,0,0),yaw=0):
        n=len(self.v);rot=Matrix.Rotation(math.radians(yaw),3,'Z')
        self.v.extend(tuple(rot@Vector(v)+Vector(offset)) for v in vertices)
        self.f.extend(tuple(n+i for i in f) for f in faces);return self
    def prism(self,outline,z0=0,z1=.5,offset=(0,0,0),yaw=0):
        n=len(outline);v=[(x,y,z) for z in [z0,z1] for x,y in outline]
        f=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        return self.part(v,f,offset,yaw)
    def box(self,l,w,h=.5,offset=(0,0,0),yaw=0):
        return self.prism([(-l/2,-w/2),(l/2,-w/2),(l/2,w/2),(-l/2,w/2)],0,h,offset,yaw)
    def ramp(self,length=4,width=5,rise=4,shift0=0,shift1=0,topwidth=None,offset=(0,0,0),yaw=0,landing=0):
        tw=width if topwidth is None else topwidth
        # A nonzero low lip makes all ramps closed solids.
        x=-length/2;X=length/2
        v=[(x,shift0-width/2,0),(x,shift0+width/2,0),(X,shift1-tw/2,0),(X,shift1+tw/2,0),
           (x,shift0-width/2,.18),(x,shift0+width/2,.18),(X,shift1-tw/2,rise+.18),(X,shift1+tw/2,rise+.18)]
        self.part(v,[(0,1,3,2),(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(4,6,7,5)],offset,yaw)
        if landing:self.box(landing,tw,.35,(offset[0]+X+landing/2,offset[1]+shift1,offset[2]+rise-.17),yaw)
        return self


def make_library():
    assert COLLECTION not in bpy.data.collections, 'Refuse to overwrite existing authored library.'
    coll=bpy.data.collections.new(COLLECTION);bpy.context.scene.collection.children.link(coll)
    coll.hide_viewport=True;coll.hide_render=True
    shapes=[]
    def add(family,name,shape):shapes.append((family,name,shape))
    add('LANDING','rectangle',Shape().box(10,7))
    add('LANDING','trapezoid',Shape().prism([(-5,-2.6),(5,-4.3),(5,4.3),(-5,2.6)]))
    add('LANDING','clipped_corners',Shape().prism([(-6,-2),(-4.4,-4),(4.8,-4),(6,-2.8),(6,2.8),(4.8,4),(-4.4,4),(-6,2)]))
    add('LANDING','asymmetric_bay',Shape().prism([(-5,-2.7),(1,-2.7),(5,-4.5),(5,3),(2,4.8),(-5,4.8)]))
    add('LANDING','L_pocket',Shape().prism([(-5,-4),(5,-4),(5,-.8),(.5,-.8),(.5,4),(-5,4)]))
    add('LANDING','split_recovery',Shape().box(7,4,.5,(-1,-2.8,0)).prism([(-3,-1.5),(4,-2.7),(4,2),(-3,2)],0,.5,(1,2.8,0)))
    add('PLATFORM','hex_pad',Shape().prism([(-3,-1.5),(-1,-3),(2,-3),(3.5,-.4),(1.8,2.8),(-2,2.8)]))
    add('PLATFORM','tri_cut_pad',Shape().prism([(-3.5,-2.5),(1.5,-2.5),(3.5,-.7),(3.5,1),(-1.5,3),(-3.5,1)]))
    add('PLATFORM','boomerang',Shape().prism([(-4,-3),(4,-.8),(3.5,2),(0,.8),(-3,3),(-4,.5)]))
    add('PLATFORM','offset_double',Shape().box(5,3.4,.45,(-2.3,-2,0)).box(4,4,.65,(2.5,2,.3)))
    add('PLATFORM','T_catch',Shape().prism([(-4,-1.5),(1,-1.5),(1,-3.5),(4,-3.5),(4,3.5),(1,3.5),(1,1.5),(-4,1.5)]))
    add('PLATFORM','spear_slab',Shape().prism([(-7,-1.9),(4,-2.7),(7,0),(4,2.7),(-7,1.9)]))
    add('WALL','stepped_strip',Shape().box(5,.4,3.4,(-5.2,0,0)).box(5,.4,4.8,(0,0,0)).box(5,.4,2.6,(5.2,0,0)))
    add('WALL','kinked_wall',Shape().prism([(-6,-.22),(0,-.22),(5.6,2.1),(5.45,2.5),(-.1,.22),(-6,.22)],0,4.2))
    add('WALL','stagger_pair',Shape().box(10,.4,4.5,(-2,-3,0)).box(6,.4,3.2,(3,3,0)))
    add('WALL','converging_pair',Shape().box(11,.4,4.2,(0,-3,0),12).box(8,.4,4.8,(1,3,0),-17))
    add('WALL','broken_run',Shape().box(4,.45,4,(-6.2,0,0)).box(5,.45,3.5,(-.7,.8,0)).box(3,.45,5,(5.2,-.7,0)))
    add('WALL','jump_pincer',Shape().box(5.5,.4,6,(-1,-2.8,0),-22).box(5,.4,4,(2,2.8,.8),24).box(2.5,2,.4,(3,0,2.8)))
    add('RAMP','clean_wedge',Shape().ramp(4,5,4))
    add('RAMP','offset_entry',Shape().ramp(4,5,4,shift0=-1.5,shift1=1,topwidth=3.5))
    add('RAMP','flared_exit',Shape().ramp(4,2.8,4,shift0=.8,shift1=-.5,topwidth=6.8))
    add('RAMP','dogleg_descent',Shape().ramp(3,3.4,3,offset=(-2,-1.5,0)).ramp(3,3.4,3,offset=(1.4,1.5,3),yaw=20))
    add('RAMP','wedge_landing',Shape().ramp(4,4.8,4,landing=3))
    add('RAMP','chute_lips',Shape().ramp(5,3.4,5).box(5,.3,1.2,(0,-1.95,0)).box(3,.3,1.8,(1,1.95,2)))
    add('BRIDGE','diagonal_plate',Shape().prism([(-6,-3.6),(-4.5,-4.7),(6,3.1),(4.4,4.8)],0,.45))
    add('BRIDGE','dogleg_link',Shape().prism([(-7,-3),(0,-3),(0,0),(7,0),(7,2.7),(-2.7,2.7),(-2.7,-.3),(-7,-.3)],0,.45))
    add('BRIDGE','staggered_chain',Shape().box(4,3,.45,(-5,-2,0)).box(3.8,4,.45,(0,.8,.4)).box(4.8,3.5,.45,(5,-.5,0)))
    add('BRIDGE','fork_connection',Shape().prism([(-6,-1.4),(-1,-1.4),(5,-4.6),(6,-2.2),(1,0),(6,2.2),(5,4.6),(-1,1.4),(-6,1.4)],0,.45))
    add('BRIDGE','unequal_rails',Shape().box(12,1.8,.4,(-1,-2,0)).box(8,2.5,.4,(2,2,.5)).box(2.5,6.5,.4,(5,0,.5)))
    add('BRIDGE','offset_transfer',Shape().box(5,5,.4,(-4,-2,0)).box(6,3,.4,(3.5,2,1.2)).prism([(-2,-.5),(2,1),(2,2.7),(-2,1.2)],0,.35,(0,0,.6)))
    add('SPEED','flared_runway',Shape().prism([(-10,-5),(-6,-2.5),(7,-2.5),(10,-4),(10,4),(7,2.5),(-6,2.5),(-10,5)],0,.45))
    add('SPEED','S_lane',Shape().prism([(-10,-3),(-4,-3),(2,0),(10,0),(10,3),(1,3),(-5,0),(-10,0)],0,.45))
    add('SPEED','chute_recovery',Shape().ramp(6,5,4,offset=(-2,0,0)).box(6,8,.5,(5,0,3.7)))
    add('SPEED','descent_gap',Shape().ramp(4,4,5,offset=(-4,-1,0)).box(5,7,.5,(4,1,4.7)))
    add('SPEED','split_speed_lanes',Shape().box(18,2.8,.45,(0,-2.6,0)).box(13,3.8,.45,(2,2.4,0)).box(3,9,.45,(8,0,0)))
    add('SPEED','banked_shelf',Shape().prism([(-9,-3),(-4,-5),(6,-3),(9,0),(7,3),(-9,2)],0,.45).box(9,.35,1.4,(-1,-3.6,.3),8))
    add('VERTICAL','alternating_stack',Shape().box(5,4,.45,(-2,-2,0)).box(4,4.5,.45,(2,2,3.3)).box(5.5,3.5,.45,(-1,-2,6.6)))
    add('VERTICAL','central_step_crowns',Shape().prism([(-3,-2),(0,-3),(3,-1),(2,2),(-2,3)],0,.4).box(3,5,.4,(0,0,3.2),28).box(5.5,3,.4,(0,0,6.4),-17))
    add('VERTICAL','wall_pair_ascent',Shape().box(7,.4,7,(0,-2.8,0)).box(5,.4,5,(1,2.8,2)).box(3.5,3,.4,(-2,0,3.3)).box(4,4,.4,(2,0,6.6)))
    add('VERTICAL','offset_balconies',Shape().prism([(-4,-3),(3,-3),(3,-.5),(0,-.5),(0,3),(-4,3)],0,.45).box(5,4,.45,(2,2,3.5)).box(3,5,.45,(-1,-1,7)))
    add('VERTICAL','sparse_catch',Shape().prism([(-4,-2),(-1,-3),(3,-2),(4,1),(0,3),(-4,2)],0,.5).box(5,4,.6,(2,1,6.3)).box(3,.45,3,(-2,-2,3.4),33))
    add('VERTICAL','cross_transfer',Shape().box(7,2.8,.4,(-1,0,0)).box(3.2,6,.4,(2,1,2.6)).box(6,3,.4,(-2,-1,5.2)).box(3.5,5,.4,(1,0,7.8)))
    manifest=[];byfamily={f:[] for f in FAMILIES}
    for index,(family,name,s) in enumerate(shapes):
        # Centre XY and align the bottom with Z=0, preserve real dimensions.
        low=[min(v[a] for v in s.v) for a in range(3)];high=[max(v[a] for v in s.v) for a in range(3)];center=[(low[a]+high[a])/2 for a in range(3)]
        vertices=[(v[0]-center[0],v[1]-center[1],v[2]-low[2]) for v in s.v]
        mesh=bpy.data.meshes.new('V05_LIB_'+family+'_'+name);mesh.from_pydata(vertices,[],s.f);mesh.update()
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh)
        assert all(e.is_manifold for e in bm.edges),(family,name)
        dims=[high[a]-low[a] for a in range(3)]
        norm=[tuple(round((v.co[a]+(dims[a]/2 if a<2 else 0))/dims[a],6) for a in range(3)) for v in bm.verts]
        normhash=hashlib.sha256(repr(sorted(tuple(sorted(norm[v.index] for v in f.verts)) for f in bm.faces)).encode()).hexdigest();bm.free()
        obj=bpy.data.objects.new(f'V05_LIB_{index:02d}_{family}_{name}',mesh);coll.objects.link(obj);obj.hide_render=True;obj.hide_select=True
        obj['variant_id']=index;obj['variant_family']=FAMILIES.index(family);obj['archetype']=name;obj['native_dimensions']=dims
        obj['allowed_scale']='uniform fit 0.65–1.35; no anisotropic deformation. Ramp slope exception: X 0.728–2.0, constrained to 45–70 degrees.'
        attr=mesh.attributes.new('variant_id','INT','FACE')
        for item in attr.data:item.value=index
        attr=mesh.attributes.new('variant_family','INT','FACE')
        for item in attr.data:item.value=FAMILIES.index(family)
        row={'id':index,'family':family,'name':name,'object':obj.name,'dimensions':dims,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),'normalized_geometry_hash':normhash}
        manifest.append(row);byfamily[family].append(row)
    assert len(set(row['normalized_geometry_hash'] for row in manifest))==len(manifest),'Scale-only duplicate vocabulary'
    return manifest,byfamily
