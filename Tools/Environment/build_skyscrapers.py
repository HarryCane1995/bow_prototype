"""Ten additive, source-authored skyline archetypes. Blender owns all geometry.

Godot XYZ is used in layout only. Meshes are authored Z-up in metres; glTF performs
the axis conversion. Each tower has editable semantic modules and simplified
collision-only bodies. Existing level objects are verified before the source save.
Run --library first for silhouette review, then --integrate to append to the map.
"""
import bpy, math, json, random, hashlib, sys
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'Art/Environment/Skyscrapers'
LIB=ART/'Skyscraper_Kit.blend'
OWNER='skyscraper_environment_v1'
COL='60_SKYSCRAPER_ENVIRONMENT'
random.seed(431)

def signature(o):
    d={'name':o.name,'type':o.type,'matrix':[list(r) for r in o.matrix_world],
       'parent':o.parent.name if o.parent else None,'collections':sorted(c.name for c in o.users_collection)}
    if o.type=='MESH':
        d.update(vertices=[list(v.co) for v in o.data.vertices], faces=[list(p.vertices) for p in o.data.polygons],
                 materials=[m.name if m else None for m in o.data.materials])
    return hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()

def material(name, color, metal=0, rough=.7, emission=0):
    m=bpy.data.materials.new('M_Level01_Skyline_'+name);m.use_nodes=True
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    m.diffuse_color=(*rgb,1);b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=(*rgb,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    if emission:
        b.inputs['Emission Color'].default_value=(*rgb,1);b.inputs['Emission Strength'].default_value=emission
    return m

class Tower:
    def __init__(self,index,name,loc,height,yaw=0):
        self.index=index;self.name=f'L01_Skyline_{index:02d}_{name}';self.height=height
        self.root=bpy.data.objects.new(self.name,None);col.objects.link(self.root)
        self.root['environment_owner']=OWNER;self.root['archetype']=name
        self.root.location=(loc[0],-loc[2],loc[1]);self.root.rotation_euler.z=-math.radians(yaw)
        self.groups={};self.colliders=[];self.count=0;self.points=[]
        self.root['height_m']=height
        self.layout={'id':index,'name':name,'position_godot':loc,'height_m':height,'yaw_deg':yaw}

    def geometry(self,part,verts,faces,mat):
        key=(part,mat)
        vs,fs=self.groups.setdefault(key,([],[]));offset=len(vs)
        vs.extend(verts);fs.extend([tuple(offset+i for i in f) for f in faces]);self.points.extend(verts)

    def collider(self,label,verts,faces):
        self.count+=1;name=f'{self.name}_{label}_{self.count:02d}_COL-colonly'
        obj=self.object(name,verts,faces,None);obj['collision_role']='simplified primary volume'
        obj.display_type='WIRE';obj.hide_render=True
        # Godot imports visible=all; colonly removes the rendering representation.
        self.colliders.append(obj)

    def object(self,name,verts,faces,mat):
        mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(verts,[],faces);mesh.update()
        o=bpy.data.objects.new(name,mesh);col.objects.link(o);o.parent=self.root;o['environment_owner']=OWNER
        if mat:mesh.materials.append(M[mat])
        return o

    def box(self,part,center,size,mat='body',collision=False,rot=0):
        cx,cy,cz=center;sx,sy,sz=[v/2 for v in size];r=math.radians(rot)
        v=[(cx+x*math.cos(r)-y*math.sin(r),cy+x*math.sin(r)+y*math.cos(r),cz+z) for x,y,z in
           [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]]
        f=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        self.geometry(part,v,f,mat)
        if collision:self.collider(part,v,f)

    def tapered(self,part,levels,mat='glass',collision=True,n=8):
        # Each ring: z, radiusX, radiusY, centreX, centreY. Octagonal chamfered footprint.
        v=[]
        for z,rx,ry,cx,cy in levels:
            for i in range(n):
                a=math.tau*(i+.5)/n;v.append((cx+rx*math.cos(a),cy+ry*math.sin(a),z))
        f=[tuple(reversed(range(n))),tuple((len(levels)-1)*n+i for i in range(n))]
        for j in range(len(levels)-1):
            for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
        self.geometry(part,v,f,mat)
        if collision:self.collider(part,v,f)

    def beam(self,part,a,b,width,mat='metal',depth=None):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0)))
        if u.length<.01:u=axis.cross(Vector((1,0,0)))
        u.normalize();w=axis.cross(u).normalized();depth=width if depth is None else depth
        v=[p+u*x*width/2+w*y*depth/2 for p in [a,b] for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        f=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        self.geometry(part,v,f,mat)

    def cylinder(self,part,center,radius,height,mat='metal',n=12,collision=False):
        x,y,z=center;self.tapered(part,[(z-height/2,radius,radius,x,y),(z+height/2,radius,radius,x,y)],mat,collision,n)

    def facade(self,center,size,pitch=4.5,ratio=.40):
        # Batched window quads, a few shared meshes instead of thousands of objects.
        x,y,z=center;sx,sy,sz=size
        for side in range(4):
            width=sx if side<2 else sy
            for row in range(max(0,int(sz/pitch)-1)):
                zz=z-sz/2+(row+1)*pitch
                for cell in range(max(0,int(width/3.5)-1)):
                    xx=-width/2+(cell+1)*3.5
                    if random.random()>ratio:continue
                    color='window' if random.random()>.12 else 'warm'
                    if side<2:
                        yy=y+(-1 if side==0 else 1)*(sy/2+.045)
                        v=[(x+xx-.85,yy,zz-.45),(x+xx+.85,yy,zz-.45),(x+xx+.85,yy,zz+.45),(x+xx-.85,yy,zz+.45)]
                    else:
                        xxx=x+(-1 if side==2 else 1)*(sx/2+.045)
                        v=[(xxx,y+xx-.85,zz-.45),(xxx,y+xx+.85,zz-.45),(xxx,y+xx+.85,zz+.45),(xxx,y+xx-.85,zz+.45)]
                    if side in [1,2]:v.reverse()
                    self.geometry('WindowBands',v,[(0,1,2,3)],color)

    def volume(self,part,center,size,mat='body',windows=True,ratio=.35):
        self.box(part,center,size,mat,True)
        if windows:self.facade(center,size,ratio=ratio)

    def fins(self,width,depth,z0,z1,spacing=7):
        for x in [-width/2,width/2]:
            for y in [-depth/2,depth/2]:self.box('CornerPiers',(x,y,(z0+z1)/2),(1.2,1.2,z1-z0),'metal')
        for z in range(int(z0)+spacing,int(z1),spacing):
            self.box('ServiceBands',(0,0,z),(width+.6,depth+.6,.65),'metal')

    def podium(self,w,d,h=8):
        self.volume('Podium',(0,0,h/2),(w,d,h),'concrete',False)
        self.box('PodiumTerrace',(0,0,h),(w+3,d+3,1.5),'metal',True)

    def antenna(self,x,y,z,h=15):
        self.cylinder('Antenna',(x,y,z+h/2),.40,h,'metal',8)
        self.box('Beacon',(x,y,z+h),(.65,.65,.8),'warm')

    def finish(self):
        for (part,mat),(v,f) in self.groups.items():
            o=self.object(self.name+'_'+part+'_'+mat,v,f,mat)
            # Large repeated hardware stays coarse. Only structural faces receive a small edge break.
            if mat in ['body','metal','concrete'] and part not in ['WindowBands','Lattice']:
                b=o.modifiers.new('Architectural edge break','BEVEL');b.width=.18;b.segments=1
        self.root['collision_bodies']=len(self.colliders)
        self.layout['collision_bodies']=len(self.colliders)
        self.layout['modules']=len(self.groups)
        return self.layout

def make_kit():
    global col,M
    bpy.ops.wm.read_factory_settings(use_empty=True)
    col=bpy.data.collections.new(COL);bpy.context.scene.collection.children.link(col)
    M={
      'body':material('Graphite','26383F',.32,.68,.065),
      'metal':material('Exoframe','52696C',.48,.53,.065),
      'concrete':material('CeramicConcrete','687472',.10,.83),
      'glass':material('SmokedGlass','102C37',.48,.28),
      'dark':material('ServiceBlack','142028',.20,.78),
      'trim':material('PaleAlloy','A5B7B3',.55,.48),
      'accent':material('TealSignal','37A898',.15,.5,1.3),
      'window':material('OfficeWindows','7CA89C',.1,.5,.75),
      'warm':material('AmberService','C49251',.1,.6,.75),
    }
    towers=[]
    # Layout in Godot XYZ. The existing playable deck occupies approximately
    # [-172,+172] x [-176,+172]. All skyline volumes remain outside a wider buffer.
    specs=[
      (1,'Exoskeleton',[-242,-88,-105],232,-55),
      (2,'Needle',[-355,-88,-360],258,-8),
      (3,'CorporateMonolith',[130,-88,-298],217,0),
      (4,'SuspendedVolumes',[243,-88,-12],205,75),
      (5,'UtilitySpine',[315,-88,-230],189,45),
      (6,'Megablock',[-258,-88,115],174,-115),
      (7,'Skybridge',[30,-88,248],211,175),
      (8,'Commerce',[232,-88,196],188,130),
      (9,'CleanSplitSpire',[368,-88,80],248,100),
      (10,'OffsetHalo',[-80,-88,326],244,180),
    ]
    for spec in specs:
        t=Tower(*spec);i=t.index
        if i==1:
            t.podium(42,40)
            t.volume('InsetCore',(0,0,107),(26,28,192),'glass',True,.42)
            for x in [-19,19]:
                for y in [-18,18]:t.box('Exopiers',(x,y,110),(2.4,2.4,220),'metal',True)
            for z in [18,57,96,135,174,213]:
                t.box('OutriggerDeck',(0,0,z),(41,39,2.4),'metal',True)
            for y in [-19,19]:
                for j in range(5):
                    z=18+39*j
                    t.beam('Lattice',(-18,y,z),(18,y,z+39),1.25)
                    t.beam('Lattice',(18,y,z),(-18,y,z+39),1.25)
            for x in [-20,20]:
                for j in range(5):t.beam('SideLattice',(x,-18,18+j*39),(x,18,57+j*39),1.3)
            t.volume('SlantedCrown',(0,0,215),(24,27,13),'body',False)
            t.box('IdentityLine',(-12,-14.2,143),(.75,.3,102),'accent')
            t.antenna(-8,4,222,10);t.antenna(9,4,222,6)
        elif i==2:
            t.podium(36,33,10)
            t.tapered('NeedleShaft',[(10,19,16,0,0),(80,16,14,0,0),(186,11,10,0,0),(228,4,4,0,0),(254,.3,.3,0,0)])
            for a in range(4):
                angle=math.pi/4+a*math.pi/2
                path=[(r*math.cos(angle),r*math.sin(angle),z) for z,r in [(10,20),(80,17),(186,12),(228,4.7),(254,.4)]]
                for p,q in zip(path,path[1:]):t.beam('BladeRibs',p,q,.85,'trim')
            for z,r in [(45,18),(105,16),(151,14),(190,11)]:t.cylinder('TransferLevels',(0,0,z),r,2,'metal',8)
            t.beam('NeedleSignal',(0,-14,70),(0,-10,184),.60,'accent')
            t.antenna(0,0,254,4)
        elif i==3:
            t.podium(59,43,12)
            t.volume('MainSlab',(-9,0,105),(31,32,186),'glass',True,.36)
            t.volume('OffsetSlab',(13,4,99),(19,33,174),'body',True,.32)
            t.box('CentralReveal',(7,-17,107),(2,1,184),'dark')
            for x in [-24,-17,-10,-3]:t.box('FacadeFins',(x,-16.4,105),(.7,1,186),'metal')
            t.box('Capstone',(-6,0,201),(46,38,6),'concrete',True)
            t.volume('ExecutiveRoof',(-10,2,209),(21,23,10),'body',False)
            t.box('CorporateLine',(21,-13,115),(.6,.8,134),'accent')
            t.antenna(-16,6,214,3)
        elif i==4:
            t.podium(44,44,9)
            t.volume('SupportCore',(0,4,96),(15,20,184),'dark',False)
            for j,(x,y,z,w,d,h) in enumerate([(-9,0,42,52,38,28),(9,0,104,60,36,31),(-8,0,171,57,38,36)]):
                t.volume('SuspendedBlock'+str(j),(x,y,z),(w,d,h),'body',True,.46)
                t.box('TransferRaft',(x,y,z-h/2),(w+4,d+3,3),'concrete',True)
                t.box('CantileverEdge',(x,-d/2-.1,z-h/2+2),(w-3,.35,.75),'accent')
                for xx in [-w/2+5,w/2-5]:
                    t.beam('Hanger',(x+xx,y+12,z-h/2),(xx*.4,12,z+h/2+15),1.25,'metal')
            t.volume('TopPlant',(-8,3,194),(27,25,10),'dark',False)
            t.antenna(-13,7,199,6)
        elif i==5:
            t.podium(48,44,10)
            t.volume('UtilityCore',(0,0,85),(25,27,150),'body',False)
            for x,y,r,h in [(-19,0,4,160),(18,5,3.6,179),(2,19,3,163)]:
                t.cylinder('ExternalDuct',(x,y,h/2),r,h,'metal',16,True)
                for z in range(24,int(h),26):t.cylinder('DuctCouplings',(x,y,z),r+1.0,1.8,'dark',16)
            for z in [32,67,102,137,166]:
                t.box('ServiceDeck',(0,0,z),(45,43,2.2),'concrete',True)
                t.volume('PlantHousing',(-5,0,z+5),(18,23,8),'dark',False)
            for z in range(20,163,10):t.box('ServiceSpine',(0,-14.2,z),(7,1.1,3),'accent' if z%30==0 else 'metal')
            t.antenna(18,5,179,10)
        elif i==6:
            t.podium(80,52,13)
            t.volume('StructuralWall',(0,8,75),(58,29,124),'dark',False)
            for j in range(5):
                z=29+j*28;x=(-1 if j%2 else 1)*6
                t.volume('HabitatRaft'+str(j),(x,0,z),(70,44,23),'concrete',True,.29)
                t.box('RecessedGallery',(x,-22.2,z-5),(65,1.1,4),'dark')
                t.box('GalleryLight',(x+10,-22.9,z-5),(25,.3,.4),'accent')
                for xx in [-24,-7,11,29]:t.box('VerticalJoint',(x+xx,-22.3,z),(1.4,1,22),'body')
            t.volume('RooftopBlock',(-18,5,158),(33,30,11),'body',False)
            t.antenna(-20,10,164,10)
        elif i==7:
            t.podium(78,39,9)
            t.volume('WestTower',(-25,0,104),(23,29,190),'body',True,.36)
            t.volume('EastTower',(25,0,91),(23,29,165),'glass',True,.42)
            for x,h in [(-25,199),(25,174)]:
                for xx in [-11,11]:t.box('TowerRails',(x+xx,-15,h/2+5),(.9,1,h-10),'metal')
                t.box('RoofCanopy',(x,0,h),(29,35,3),'concrete',True)
            for z in [85,166]:
                t.volume('OccupiedSkybridge',(0,0,z),(29,18,10),'metal',True,.55)
                t.box('BridgeTerrace',(0,0,z+6),(34,23,1.6),'concrete',True)
                for y in [-12,12]:t.beam('BridgeBrace',(-16,y,z-9),(16,y,z-1),1.1,'metal')
                t.box('BridgeSignal',(0,-12.2,z+6),(32,.4,.5),'accent')
            t.antenna(-27,2,201,10)
        elif i==8:
            t.podium(48,44,15)
            t.volume('CommerceStack',(0,4,94),(31,31,158),'body',True,.26)
            for z in [22,56,93,133,174]:t.box('RetailTerrace',(0,0,z),(45,41,3),'metal',True)
            for x,z,h in [(-13,114,100),(9,74,57)]:
                t.box('BillboardFrame',(x,-20,z),(15,4,h),'metal')
                t.box('BillboardFace',(x,-22.1,z),(12,.3,h-4),'dark')
                for k in range(4):t.box('GraphicBars',(x,-22.4,z-h*.30+k*h*.16),(7-(k%2)*2,.18,1.1),'accent' if x<0 else 'warm')
                t.box('GraphicRail',(x-4,-22.4,z),(.6,.18,h*.8),'accent')
            t.volume('MediaCrown',(0,2,180),(24,23,8),'dark',False)
            t.antenna(6,5,184,4)
        elif i==9:
            t.podium(42,34,8)
            for s in [-1,1]:
                t.tapered('SplitBlade'+str(s),[(8,12,16,s*9,0),(110,10,14,s*10,0),(188,7,11,s*8,0),(232 if s==1 else 245,.5,1,s*5,0)],'glass',True,8)
                t.beam('BladeEdge',(s*18,-10,12),(s*14,-8,176),1.6,'trim')
                t.beam('CrownSweep',(s*14,-8,176),(s*5,0,232 if s==1 else 245),1.4,'trim')
                t.beam('FineSignal',(s*5,-14,34),(s*5,-11,180),.5,'accent')
            for z in [65,129]:t.box('LinkFloor',(0,0,z),(16,14,3),'metal',True)
            t.antenna(-5,0,245,3)
        elif i==10:
            t.podium(50,37,9)
            t.volume('LowerCore',(0,0,57),(24,25,96),'glass',True,.32)
            # A large offset open hexagonal frame, with real negative space.
            ring=[(-25,0,99),(-43,0,131),(-28,0,194),(3,0,234),(35,0,202),(38,0,140),(18,0,111)]
            for j,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
                t.beam('LandmarkFrame',a,b,9,'metal',17)
                # Simplified convex prism of the frame beam, leaving the opening empty.
                vs,fs=t.groups[('LandmarkFrame','metal')];t.collider('Frame',vs[-8:],[tuple(k-(len(vs)-8) for k in f) for f in fs[-6:]])
                aa=Vector(a)+Vector((0,-8.65,0));bb=Vector(b)+Vector((0,-8.65,0))
                t.beam('HaloSignal',aa,bb,.62,'accent')
            t.volume('SuspendedObservatory',(5,0,159),(46,24,13),'dark',True,.65)
            for x in [-12,19]:t.beam('ObservatoryHangers',(x,0,165),(x*.5,0,224),1.4,'metal')
            t.volume('OffsetTop',(1,0,237),(17,19,9),'body',False)
            t.antenna(1,0,241.5,2.5)
        # Composition iteration after the user allowed ceiling removal: the two
        # distant spires rise above the enclosing graybox horizon. Footprints and
        # every collision stay aligned; shorter masses retain their broad profiles.
        lift={1:1.30,2:1.60,3:1.40,4:1.18,5:1.18,6:1.10,7:1.32,8:1.18,9:1.50,10:1.40}[i]
        t.root.scale.z=lift;t.root['height_m']=round(t.height*lift,2)
        t.layout['height_m']=round(t.height*lift,2);t.layout['vertical_composition_scale']=lift
        towers.append(t.finish())
    sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc['environment_owner']=OWNER
    sc['scope']='10 modular skyline archetypes. No gameplay edits. Collision via simplified colonly geometry.'
    sc.world=bpy.data.worlds.new('Skyline preview world');sc.world.color=(.15,.15,.15)
    text=bpy.data.texts.new('README_SKYSCRAPER_KIT')
    text.write('Ten skyline archetypes; Blender metres, Z-up. Roots use level placements.\nSeparate base, body, crown, frame, windows and attachment meshes.\nCOL-colonly objects are simplified Godot colliders; hide_render is for Blender previews only.\nMaterials use transferable Principled inputs, no custom shader or texture dependencies.\nAuthoritative placed source is Level_01_Blockout.blend after integration. This file is the reusable kit.\n')
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(LIB))
    (ART/'layout.json').write_text(json.dumps({'owner':OWNER,'clear_playable_xz':[-192,192,-195,192],'towers':towers},indent=2))
    print('SKYSCRAPER_KIT_SAVED',len(towers),'towers',len(bpy.data.objects),'objects')

def integrate():
    source=ROOT/'Level_01_Blockout.blend';bpy.ops.wm.open_mainfile(filepath=str(source))
    original={o.name:signature(o) for o in bpy.context.scene.objects if o.get('environment_owner')!=OWNER}
    old=bpy.data.collections.get(COL)
    if old:
        assert all(o.get('environment_owner')==OWNER for o in old.all_objects),'Unowned object in skyline collection'
        for o in list(old.all_objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(old)
        # Only data from this generator namespace; prevent .001 material buildup
        # when iterating our own collection without touching existing level data.
        for mesh in list(bpy.data.meshes):
            if mesh.name.startswith('L01_Skyline_') and mesh.users==0:bpy.data.meshes.remove(mesh)
        for material in list(bpy.data.materials):
            if material.name.startswith('M_Level01_Skyline_') and material.users==0:bpy.data.materials.remove(material)
    with bpy.data.libraries.load(str(LIB),link=False) as (src,dst):dst.collections=[COL]
    c=dst.collections[0];bpy.context.scene.collection.children.link(c)
    bpy.context.view_layer.update()
    roots=[o for o in c.objects if o.type=='EMPTY'];assert len(roots)==10
    collisions=[]
    for o in c.objects:
        if o.type!='MESH':continue
        ps=[o.matrix_world@Vector(p) for p in o.bound_box]
        x0,x1=min(p.x for p in ps),max(p.x for p in ps);z0,z1=min(-p.y for p in ps),max(-p.y for p in ps)
        assert x1<-192 or x0>192 or z1<-195 or z0>192,('Inside protected route envelope',o.name)
        if o.name.endswith('-colonly'):collisions.append(o.name)
    for name,h in original.items():assert signature(bpy.data.objects[name])==h,('Existing source changed',name)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    result={'preserved_original_objects':len(original),'tower_roots':len(roots),'collision_bodies':len(collisions),
            'protected_route_envelope_clear':True,'new_objects':len(c.objects)}
    (ART/'source_validation.json').write_text(json.dumps(result,indent=2))
    print('SKYSCRAPER_INTEGRATED',json.dumps(result))

if '--library' in sys.argv:make_kit()
elif '--integrate' in sys.argv:integrate()
else:raise RuntimeError('Choose --library or --integrate; no implicit source overwrite.')
