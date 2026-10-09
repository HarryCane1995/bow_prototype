"""Author one reusable GN modifier. Runtime generation is native and local to each proxy."""
import bpy,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'FlowCourseV03'))
from grammar import FlowGraph

NAME='GN_ProxyChunk_Generator_v04'
TYPES=['AUTO','WALLRUN','SLIDE','ARENA','DESCENT','VERTICAL','MIXED','GRAPPLE']
COLORS=[(.43,.47,.50),(.30,.43,.61),(.63,.49,.26),(.48,.51,.53),(.65,.34,.20),(.45,.36,.60),(.30,.51,.45),(.55,.32,.52)]

def build(metrics,wedge):
    g=FlowGraph(NAME)
    source=g.input('Geometry','NodeSocketGeometry')
    seed=g.input('Seed','NodeSocketInt',17,0,1000000)
    kind_input=g.input('Chunk Type','NodeSocketInt',0,0,7,'0 Auto / 1 Wallrun / 2 Slide / 3 Arena / 4 Descent / 5 Vertical / 6 Mixed / 7 Grapple')
    density=g.input('Density',value=.65,low=0,high=1)
    vertical=g.input('Verticality',value=.6,low=0,high=1)
    openness=g.input('Openness',value=.55,low=0,high=1)
    wallbias=g.input('Wallrun Bias',value=.6,low=0,high=1,description='Archetype selection weight in Auto mode.')
    slidebias=g.input('Slide Bias',value=.45,low=0,high=1,description='Slide/descent weight in Auto mode.')
    arenabias=g.input('Arena Bias',value=.45,low=0,high=1,description='Arena weight in Auto mode; wide proxies favour arenas.')
    grapplebias=g.input('Grapple Bias',value=.3,low=0,high=1,description='Grapple weight in Auto mode; needs at least 60 x 14 x 12 metres.')
    steep=g.input('Ramp Steepness',value=45,low=35,high=70,description='35-45 grounded descent. 55-70 airborne drop chute, with recovery.')
    spacing=g.input('Obstacle Spacing',value=12,low=6,high=24,description='Metres between optional beats; also controls primary runway/recovery proportions.')
    jitter=g.input('Orientation Randomness',value=12,low=0,high=30,description='Degrees of controlled local yaw; critical walls use a reduced fraction.')
    complexity=g.input('Complexity',value=.65,low=0,high=1)
    cut_enabled=g.input('Use Exclusion','NodeSocketBool',False)
    cutter=g.input('Exclusion Object','NodeSocketObject',description='Optional independent subtraction mesh. No global layout dependency.')
    guide=g.input('Show Direction','NodeSocketBool',True,description='Preview start/end path and arrow; excluded from export.')
    bb=g.node('GeometryNodeBoundBox','This proxy editable mesh bounds');g.set(bb,'Geometry',source)
    lo=g.separate(bb.outputs['Min']);hi=g.separate(bb.outputs['Max'])
    self_node=g.node('GeometryNodeSelfObject','This proxy only')
    info=g.node('GeometryNodeObjectInfo','Own transform scale',transform_space='ORIGINAL');g.set(info,'Object',self_node.outputs[0])
    scale=[g.high(.0001,g.math('ABSOLUTE',s)) for s in g.separate(info.outputs['Scale'])]
    # Construct in physical metres, then inverse-scale into the local mesh domain.
    W=g.mul(g.sub(hi[0],lo[0]),scale[0]);L=g.mul(g.sub(hi[1],lo[1]),scale[1]);H=g.mul(g.sub(hi[2],lo[2]),scale[2])
    rnd=lambda stream,a=0,b=1:g.random(seed,0,stream,a,b)
    both=lambda a,b:g.boolean('AND',a,b)
    enough=lambda l,w,h:both(both(g.gt(L,l-.01),g.gt(W,w-.01)),g.gt(H,h-.01))
    fits=[True,enough(24,7,7),enough(20,7,3),enough(16,12,4),enough(30,9,8),enough(28,8,10),enough(24,8,6),enough(60,14,12)]
    weights=[0,wallbias,slidebias,g.mul(arenabias,g.low(2,g.high(.4,g.div(W,L)))),g.mul(slidebias,.65),g.mul(vertical,.7),g.add(.15,g.mul(complexity,.7)),grapplebias]
    cumulative=0;thresholds=[]
    for k in range(1,8):
        cumulative=g.add(cumulative,g.switch(fits[k],0,weights[k],'FLOAT'));thresholds.append(cumulative)
    pick=g.mul(rnd(400),cumulative);auto=1
    for k,threshold in enumerate(thresholds[:-1],2):auto=g.switch(g.gt(pick,threshold),auto,k,'INT')
    auto=g.switch(g.gt(cumulative,.0001),0,auto,'INT')
    chosen=g.switch(g.eq(kind_input,0),kind_input,auto,'INT')
    valid=both(g.gt(chosen,0),g.choose(chosen,fits,'BOOLEAN'));kind=g.switch(valid,0,chosen,'INT')
    yaw=g.mul(g.mul(jitter,math.pi/180),rnd(11,-1,1))
    lane=g.low(g.sub(W,1.0),g.add(6,g.mul(openness,g.sub(W,7))))
    start_len=g.low(g.mul(L,.24),g.add(5,g.mul(spacing,.25)))
    rise=g.low(g.sub(H,4),g.mul(metrics['wall_jump_rise'],g.add(.4,g.mul(vertical,.35))))
    # Same observed carry budget as V03, scoped to this proxy only.
    ballistic=g.mul(metrics['gravity']*.5,g.math('POWER',g.div(g.high(0,g.sub(L,18)),40),2))
    drop=g.low(g.sub(H,3),g.low(g.add(6,g.mul(vertical,14)),ballistic))
    grapple_rise=g.low(g.sub(H,4),g.add(4,g.mul(vertical,5)))
    entry_z=g.switch(g.eq(kind,4),0,drop,'FLOAT')
    exit_z=g.choose(kind,[0,0,0,0,0,rise,g.mul(rise,.5),grapple_rise],'FLOAT')
    layouts=[]
    def floor(a,b,z=0,width=None,y=0,angle=0,role=0):
        return g.slab(g.sub(b,a),lane if width is None else width,z,g.mul(g.add(a,b),.5),y,angle=angle,role=role)
    def wedge_geo(x0,x1,z0,z1,width):
        n=g.node('GeometryNodeObjectInfo','Unit wedge only',transform_space='ORIGINAL');g.set(n,'Object',wedge)
        return g.store(g.transform(n.outputs['Geometry'],g.vec(g.mul(g.add(x0,x1),.5),0,g.low(z0,z1)),g.vec(g.sub(x1,x0),width,g.high(.02,g.math('ABSOLUTE',g.sub(z1,z0)))),g.vec(0,0,g.switch(g.lt(z1,z0),0,math.pi,'FLOAT'))),'flow_role',2)
    layouts.append(floor(0,L,0,g.high(.1,g.sub(W,.4))))
    # WALLRUN: bounded primary gap and staggered wall contacts.
    span=g.low(g.mul(metrics['wallrun'],.58),g.sub(L,g.mul(start_len,2)))
    mid=g.add(g.mul(L,.5),rnd(13,-1.2,1.2));a=g.sub(mid,g.mul(span,.5));b=g.add(mid,g.mul(span,.5))
    walls=[floor(0,a),floor(b,L)]
    for side in (-1,1):
        walls.append(g.wall(g.add(span,5),g.low(g.sub(H,1),g.add(5,g.mul(vertical,3))),g.add(mid,side*1.8),side*3.1,0,g.mul(yaw,side*.5)))
    layouts.append(g.join(walls))
    # SLIDE: fixed viable clearance, variable roof interval and optional side challenges.
    roof_a=g.add(start_len,rnd(21,-1,1));roof_b=g.high(g.add(roof_a,5),g.sub(L,start_len))
    slide=[floor(0,L),floor(roof_a,roof_b,1.95,g.low(lane,7),role=3)]
    for side in (-1,1):slide.append(g.wall(g.sub(roof_b,roof_a),2.4,g.mul(g.add(roof_a,roof_b),.5),side*3.65,0))
    layouts.append(g.join(slide))
    # ARENA: broad main pad, clear central entry/exit, seeded optional perimeter cover.
    arena=[floor(0,L,0,g.sub(W,.6))]
    for i in range(8):
        t=(i+.5)/8;x=g.add(g.mul(L,t),rnd(40+i,-1.2,1.2));side=-1 if i%2 else 1
        active=both(g.lt((i+1)/8,density),g.lt(i,g.div(L,g.mul(spacing,.5))))
        wall=g.wall(g.low(8,g.mul(spacing,.6)),g.add(2,g.mul(vertical,3)),x,g.mul(g.mul(W,.31),side),0,g.mul(yaw,side))
        pad=g.slab(6,6,g.mul(vertical,2.6),x,g.mul(g.mul(W,.31),-side),angle=g.mul(yaw,.7))
        arena.append(g.keep(g.join([wall,g.keep(pad,g.gt(complexity,.55))]),active))
    layouts.append(g.join(arena))
    # DESCENT: aggressive continuous wedge plus a physically useful recovery.
    lip=g.add(6,rnd(70,-.7,.7));foot=g.add(lip,g.div(drop,g.math('TANGENT',g.mul(steep,math.pi/180))))
    descent=[floor(0,lip,drop),wedge_geo(lip,foot,drop,0,lane),floor(foot,L,0,g.high(lane,g.low(g.sub(W,1),14)))]
    layouts.append(g.join(descent))
    # VERTICAL: wall-jump chain and intermediate catch, no automatic staircase.
    pair_gap=g.low(g.sub(W,2),metrics['wall_jump_lateral']*.62)
    shaft=[floor(0,g.mul(L,.27)),floor(g.mul(L,.71),L,rise),floor(g.mul(L,.44),g.mul(L,.58),g.mul(rise,.5),angle=g.mul(yaw,.3))]
    for side in (-1,1):shaft.append(g.wall(g.mul(L,.58),g.add(rise,2.5),g.mul(L,.5),g.mul(g.add(pair_gap,.7),side*.5),0,g.mul(yaw,side*.2)))
    layouts.append(g.join(shaft))
    # MIXED: authored local lane with variable beat count and seeded stagger/rotation.
    count=g.low(7,g.high(2,g.math('FLOOR',g.div(g.mul(L,.62),spacing))))
    step=g.div(g.mul(L,.62),count)
    island_length=g.high(4,g.sub(step,g.low(5,g.mul(spacing,.25))))
    mixed=[floor(0,g.mul(L,.19)),floor(g.mul(L,.81),L,g.mul(rise,.5))]
    for i in range(7):
        x=g.add(g.mul(L,.19),g.mul(step,i+.5));z=g.mul(g.mul(rise,.5),g.div(i+.5,count))
        island=g.slab(island_length,g.high(6,g.mul(lane,.8)),z,x,g.mul(rnd(100+i,-1,1),g.mul(g.sub(W,lane),.32)),angle=g.mul(yaw,.7 if i%2 else -.7))
        mixed.append(g.keep(island,g.lt(i,count)))
    layouts.append(g.join(mixed))
    # GRAPPLE: real export marker, launch pad and large elevated landing catch.
    anchor_x=g.low(32,g.add(g.mul(L,.38),rnd(180,-1,1)));anchor_z=10
    grapple=[floor(0,g.add(g.mul(L,.16),rnd(181,-.8,.8)),0,g.high(lane,12)),floor(g.add(g.mul(L,.48),rnd(182,-1.2,1.2)),L,grapple_rise,g.sub(W,.8))]
    layouts.append(g.join(grapple))
    geo=g.choose(kind,layouts)
    # Density/spacing/complexity add optional movement surfaces without changing core access.
    extras=[]
    for i in range(4):
        x=g.add(g.mul(L,(i+1)/5),rnd(150+i,-1,1));side=-1 if i%2 else 1
        z=g.add(g.mul(entry_z,g.sub(1,(i+1)/5)),g.mul(exit_z,(i+1)/5))
        extra=g.wall(g.low(6,g.mul(spacing,.45)),g.add(2,g.mul(vertical,2)),x,g.mul(g.sub(W,2),side*.5),z,g.mul(yaw,side))
        enabled=both(both(g.gt(W,12),g.gt(density,(i+1)/6)),both(g.gt(complexity,.3),g.lt(i,g.div(L,spacing))))
        extras.append(g.keep(extra,enabled))
    geo=g.join([geo]+extras)
    # Map physical frame X-forward into authored local +Y; all translations remain local.
    offset=g.vec(g.mul(g.add(lo[0],hi[0]),.5),lo[1],g.add(lo[2],g.div(.7,scale[2])))
    inv=g.vec(*[g.div(1,s) for s in scale])
    def local(geometry):
        return g.transform(g.transform(geometry,rotation=(0,0,math.pi/2)),offset,inv)
    geo=local(geo);geo=g.mesh_boolean('INTERSECT',geo,bb.outputs['Bounding Box'])
    exclusion=g.object(None);g.set(exclusion,'Object',cutter)
    size=g.node('GeometryNodeAttributeDomainSize',component='MESH');g.set(size,'Geometry',exclusion.outputs['Geometry'])
    active_cut=both(cut_enabled,g.gt(size.outputs['Face Count'],0))
    geo=g.switch(active_cut,geo,g.mesh_boolean('DIFFERENCE',geo,exclusion.outputs['Geometry']))
    for k,color in enumerate(COLORS):
        mat=bpy.data.materials.new('M_V04_'+TYPES[k]);mat.diffuse_color=(*color,1)
        n=g.node('GeometryNodeSetMaterial');g.set(n,'Geometry',geo);g.set(n,'Material',mat);g.set(n,'Selection',g.eq(kind,k));geo=n.outputs[0]
    # Direction arrow and anchor marker are preview-only, tagged for export filtering.
    line=g.node('GeometryNodeCurvePrimitiveLine');g.set(line,'Start',g.vec(0,0,g.add(entry_z,.1)));g.set(line,'End',g.vec(L,0,g.add(exit_z,.1)))
    circle=g.node('GeometryNodeCurvePrimitiveCircle');g.set(circle,'Resolution',4);g.set(circle,'Radius',.065)
    tube=g.node('GeometryNodeCurveToMesh');g.set(tube,'Curve',line.outputs[0]);g.set(tube,'Profile Curve',circle.outputs[0]);g.set(tube,'Fill Caps',True)
    arrows=[tube.outputs[0]]
    for side in (-1,1):arrows.append(g.slab(2,.2,g.add(exit_z,.13),g.sub(L,1.0),side*.55,thickness=.12,angle=side*math.pi/4))
    marker=g.node('GeometryNodeMeshIcoSphere');g.set(marker,'Radius',.65);g.set(marker,'Subdivisions',1)
    arrows.append(g.keep(g.transform(marker.outputs[0],g.vec(anchor_x,0,anchor_z)),g.eq(kind,7)))
    guides=g.store(local(g.join(arrows)),'flow_role',99)
    mat=bpy.data.materials.new('M_V04_DIRECTION');mat.diffuse_color=(.12,.85,.9,1)
    n=g.node('GeometryNodeSetMaterial');g.set(n,'Geometry',guides);g.set(n,'Material',mat)
    geo=g.join([geo,g.keep(n.outputs[0],guide)])
    entry=g.vec(g.mul(g.add(lo[0],hi[0]),.5),lo[1],g.add(lo[2],g.div(g.add(.7,entry_z),scale[2])))
    exit=g.vec(g.mul(g.add(lo[0],hi[0]),.5),hi[1],g.add(lo[2],g.div(g.add(.7,exit_z),scale[2])))
    anchor=g.vec(g.mul(g.add(lo[0],hi[0]),.5),g.add(lo[1],g.div(anchor_x,scale[1])),g.add(lo[2],g.div(10.7,scale[2])))
    for name,value,datatype in [('chunk_type',kind,'INT'),('chunk_valid',valid,'BOOLEAN'),('chunk_seed',seed,'INT'),('chunk_entry',entry,'FLOAT_VECTOR'),('chunk_exit',exit,'FLOAT_VECTOR'),('chunk_anchor',anchor,'FLOAT_VECTOR'),('chunk_length',L,'FLOAT'),('chunk_width',W,'FLOAT'),('chunk_wall_yaw',yaw,'FLOAT'),('chunk_wall_pair_gap',pair_gap,'FLOAT'),('chunk_steepness',steep,'FLOAT')]:geo=g.store(geo,name,value,datatype)
    g.output('Geometry',geo);g.arrange();g.tree['workflow']='One authored mesh -> one independent chunk; local +Y; no global layout driver'
    return g.tree
