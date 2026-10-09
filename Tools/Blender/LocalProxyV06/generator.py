"""V06 placement compositions, conservative occupancy and large arena masses."""
import bpy,importlib.util,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('v06_occupancy',HERE/'occupancy.py');occ=importlib.util.module_from_spec(sp);sp.loader.exec_module(occ)
Graph=occ.Graph;v05=occ.v05;NAME='GN_LevelProxyGenerator_v06'
CONTROLS=v05.CONTROLS+[('Debug Placement Volumes','NodeSocketBool',False,None,None,'Show accepted oriented placement boxes and required crossing keepout. Diagnostic only.')]
PATTERNS=['LONG_RUN','SINGLE_CENTER','LEFT_RIGHT_ALTERNATE','STAGGERED','SIDE_BIASED','WALL_AND_PLATFORM','OPEN_CENTER','EDGE_WALLS','SLIDE_DESCENT','GRAPPLE_CROSSING','ARENA_EDGE','VERTICAL_ZIGZAG']
ROLES={0:'run',1:'receiving_catch',2:'edge_wall',3:'raised_platform',4:'ramp',5:'bridge',6:'arena_floor',7:'vertical_pad',8:'vertical_wall',9:'required_helper',10:'optional_helper',90:'required_crossing_keepout'}


def build(metrics,manifest):
    g=Graph(NAME);proxy=g.input('Proxy','NodeSocketObject');cutter=g.input('Cutter','NodeSocketObject')
    q={n:g.input(n,k,v,lo,hi,desc) for n,k,v,lo,hi,desc in CONTROLS};g.controls=q
    mode=g.input('Output Mode','NodeSocketInt',0,0,9,'0 surfaces / 1 helpers / 2 spans / 3 envelope / 4 raw surfaces / 5 helper records / 6 accepted records / 7 placement wires / 8 rejected records / 9 candidates.')
    base=g.node('GeometryNodeGroup','Preserved V04 local frames',node_tree=bpy.data.node_groups['GN_V05_LocalSections_FromV04'])
    rhythm=g.node('GeometryNodeGroup','Preserved V05 length and gap grammar',node_tree=bpy.data.node_groups['GN_V06_Rhythm_FromV05'])
    for node in [base,rhythm]:
        g.set(node,'Proxy',proxy)
        if 'Cutter' in node.inputs:g.set(node,'Cutter',cutter)
        for n,val in q.items():
            if n in node.inputs:g.set(node,n,val)
    envelope=base.outputs['Envelope'];valid=base.outputs['Valid Volume'];hp=rhythm.outputs[0];vp=base.outputs['Vertical Levels']
    cinfo=g.node('GeometryNodeObjectInfo','Secondary authored cutter',transform_space='RELATIVE');g.set(cinfo,'Object',cutter);cutgeo=cinfo.outputs['Geometry']
    # Arena eligibility is local and based on run speed: width 1.5 s, floor
    # area 3 square run-seconds, aspect ratio <= 5. No whole-proxy bounds.
    speed=metrics['run_speed'];W=g.named('width');PL=g.named('length');H=g.named('height')
    def arena_score():
        width=g.div(W,speed*1.5);area=g.math('SQRT',g.div(g.mul(W,PL),speed*speed*3));aspect=g.mul(g.div(W,g.hi(PL,.01)),5)
        return g.lo(1,g.lo(width,g.lo(area,aspect)))
    hp=g.put(hp,'arena_score',arena_score());isarena=g.gt(g.attrf('arena_score'),.999)
    hp=g.filter(hp,g.OR(g.NOT(isarena),g.lt(g.attrf('sequence_start'),.01)))
    hp=g.put(hp,'section_length',g.switch(isarena,g.attrf('section_length'),PL,'FLOAT'))
    hp=g.put(hp,'span_class',g.switch(isarena,g.attri('span_class'),0,'INT'),'INT')
    hp=g.put(hp,'span_distance',g.switch(isarena,g.attrf('span_distance'),0,'FLOAT'))
    hp=g.put(hp,'catch_length',g.switch(isarena,g.attrf('catch_length'),0,'FLOAT'))
    hp=g.put(hp,'grapple_required',g.eqi(g.attri('span_class'),4),'BOOLEAN')
    pattern=g.rnd(600,0,8,'INT')
    pattern=g.switch(g.gt(g.rnd(601),g.mul(g.add(.15,g.mul(q['Density'],.8)),g.sub(1,g.mul(q['Openness'],.35)))),pattern,0,'INT')
    pattern=g.switch(g.eqi(g.attri('span_class'),4),pattern,9,'INT');pattern=g.switch(isarena,pattern,10,'INT')
    hp=g.put(hp,'pattern_id',pattern,'INT')
    budget=g.math('FLOOR',g.add(3,g.add(g.mul(q['Density'],3),g.lo(2,g.div(g.attrf('section_length'),35)))))
    hp=g.put(hp,'primitive_budget',g.switch(isarena,g.lo(8,budget),g.add(5,g.math('FLOOR',g.mul(q['Density'],4))),'INT'),'INT')

    def make(points,role,primitive,size,offset=(0,0,0),selection=True,yaw=0,ordinal=0,priority=5,scaleclass=1):
        points=g.filter(points,selection)
        points=g.put(points,'primitive_role',role,'INT');points=g.put(points,'primitive_id',primitive,'INT');points=g.put(points,'primitive_scale_class',scaleclass,'INT')
        ident=g.node('GeometryNodeInputNamedAttribute',data_type='INT');g.set(ident,'Name','variant_identity')
        stable_id=g.switch(ident.outputs['Exists'],g.attri('section_id'),ident.outputs['Attribute'],'INT')
        points=g.put(points,'placement_id',g.hash_id(stable_id,role*100+ordinal),'INT')
        points=g.put(points,'placement_priority',priority)
        points=g.put(points,'intentional_touch_group',g.attri('patch_id'),'INT')
        points=g.put(points,'occ_size',g.vec(*size),'FLOAT_VECTOR')
        f=g.plus(g.vscale(g.named('forward'),g.math('COSINE',yaw)),g.vscale(g.named('side'),g.math('SINE',yaw)))
        points=g.put(points,'occ_x',g.norm(f),'FLOAT_VECTOR');points=g.put(points,'occ_z',g.norm(g.named('up')),'FLOAT_VECTOR')
        points=g.put(points,'occ_y',g.norm(g.vector('CROSS_PRODUCT',g.attrv('occ_z'),g.attrv('occ_x'))),'FLOAT_VECTOR')
        return g.setpos(points,offset=offset)

    # Reserve a required span's approach, gap and receiving landing atomically.
    # This prevents a later wall from blocking the helper or eating the catch.
    L=g.attrf('section_length');D=g.attrf('span_distance');C=g.attrf('catch_length');required=g.attr('grapple_required','BOOLEAN')
    reserveheight=g.add(g.lo(8,g.sub(H,1.1)),1)
    reserves=make(hp,90,0,(g.add(L,g.add(D,C)),10,reserveheight),g.offset(g.mul(g.add(L,g.add(D,C)),.5),0,g.mul(reserveheight,.5)),required,priority=0,scaleclass=3)
    accepted_reserves,rejected_reserves=g.solve(reserves,label='Required crossing reservations')
    reservation_ok=g.has_id(accepted_reserves,g.position(),g.attri('section_id'))
    hp=g.put(hp,'occupancy_required_fallback',g.both(required,g.NOT(reservation_ok)),'BOOLEAN')
    fallback=g.attr('occupancy_required_fallback','BOOLEAN');newgap=g.switch(fallback,D,g.rnd(106,*v05.span_bands(metrics)['BASIC_JUMP']),'FLOAT')
    hp=g.put(hp,'catch_length',g.add(C,g.sub(D,newgap)));hp=g.put(hp,'span_distance',newgap)
    hp=g.put(hp,'span_class',g.switch(fallback,g.attri('span_class'),1,'INT'),'INT')
    hp=g.put(hp,'grapple_required',g.eqi(g.attri('span_class'),4),'BOOLEAN');hp=g.put(hp,'required_traversal',g.attri('span_class'),'INT')
    hp=g.put(hp,'pattern_id',g.switch(fallback,g.attri('pattern_id'),0,'INT'),'INT')
    L=g.attrf('section_length');D=g.attrf('span_distance');C=g.attrf('catch_length');P=g.attri('pattern_id')
    arena=g.gt(g.attrf('arena_score'),.999);lane=g.NOT(arena);gap=g.gt(g.attri('span_class'),0)
    floorwidth=g.lo(g.sub(W,.8),g.choose(g.math('MINIMUM',g.math('FLOOR',g.div(L,25)),2),[5.5,6.5,7.5]))
    catchwidth=g.lo(g.sub(W,.8),g.choose(g.attri('span_class'),[5.5,5.5,6.5,8,8]))
    candidates=[]
    candidates.append(make(hp,0,g.switch(g.gt(L,35),0,2,'INT'),(L,floorwidth,.5),g.offset(g.mul(L,.5),0,.25),lane,priority=0,scaleclass=g.switch(g.gt(L,25),1,2,'INT')))
    candidates.append(make(hp,1,g.switch(g.gt(g.attri('span_class'),2),0,1,'INT'),(C,catchwidth,.5),g.offset(g.add(g.add(L,D),g.mul(C,.5)),0,.25),g.both(lane,gap),priority=0,scaleclass=g.switch(g.gt(g.attri('span_class'),2),1,2,'INT')))
    candidates.append(make(hp,6,9,(g.sub(L,.8),g.sub(W,.8),.6),g.offset(g.mul(L,.5),0,.3),arena,priority=0,scaleclass=3))

    # Required and optional helper records, using the same V05 approach metric.
    helperheight=g.lo(8,g.sub(H,1.1));helperalong=g.add(L,g.mul(D,.57))
    approach=g.plus(g.position(),g.offset(g.sub(L,.8),0,.55))
    anchor=g.plus(g.position(),g.offset(helperalong,0,helperheight))
    helperbase=g.put(hp,'source_span',g.attri('section_id'),'INT')
    helperbase=g.put(helperbase,'anchor_distance_from_approach',g.vector('DISTANCE',approach,anchor))
    helperbase=g.put(helperbase,'anchor_height',helperheight)
    helperbase=g.put(helperbase,'landing_distance',g.vector('DISTANCE',anchor,g.plus(g.position(),g.offset(g.add(L,D),0,.5))))
    helperclear=g.both(g.inside(envelope,anchor,.85),g.switch(q['Use Cutter'],True,g.NOT(g.inside(cutgeo,anchor,-.85)),'BOOLEAN'))
    required=g.attr('grapple_required','BOOLEAN')
    candidates.append(make(helperbase,9,0,(1.04,1.04,1.04),g.offset(helperalong,0,helperheight),g.both(lane,required),priority=1,scaleclass=0))
    optional=g.both(lane,g.both(gap,g.both(g.NOT(required),g.both(g.lt(g.rnd(610),q['Grapple Bias']),helperclear))))
    candidates.append(make(helperbase,10,0,(.48,.48,.48),g.offset(helperalong,0,helperheight),optional,priority=2,scaleclass=0))

    # Sparse simple arrangements, never a slot at every available position.
    side=g.switch(g.lt(g.rnd(620),.5),-1,1,'FLOAT')
    yaw=g.mul(g.mul(q['Orientation Randomness'],math.pi/180),g.rnd(621,-1,1))
    wallpattern=g.OR(g.OR(g.eqi(P,4),g.eqi(P,5)),g.OR(g.OR(g.eqi(P,6),g.eqi(P,7)),g.eqi(P,9)))
    walllen=g.lo(g.sub(L,5),g.choose(g.rnd(622,0,2,'INT'),[6,12,metrics['wallrun']*.5]))
    wallheight=g.lo(g.sub(H,1.5),g.rnd(623,4,7))
    projection=g.add(g.mul(g.absolute(g.math('SINE',yaw)),g.mul(walllen,.5)),g.mul(g.absolute(g.math('COSINE',yaw)),.25))
    wallside=g.add(g.add(g.mul(floorwidth,.5),occ.CLEARANCE),projection)
    wallfits=g.both(g.gt(walllen,3),g.lt(g.add(wallside,projection),g.sub(g.mul(W,.5),.1)))
    wallselect=g.both(lane,g.both(wallpattern,g.both(wallfits,g.lt(g.rnd(624),q['Wallrun Bias']))))
    for i in range(2):
        sel=wallselect if i==0 else g.both(wallselect,g.OR(g.eqi(P,6),g.eqi(P,7)))
        wid=g.choose(g.rnd(622,0,2,'INT'),[5,3,4])
        candidates.append(make(hp,2,wid,(walllen,.5,wallheight),g.offset(g.mul(L,.48 if i==0 else .57),g.mul(g.mul(side,1 if i==0 else -1),wallside),g.add(.5,g.mul(wallheight,.5))),sel,g.mul(yaw,1 if i==0 else -1),i,4,1))
    padpattern=g.OR(g.OR(g.eqi(P,1),g.eqi(P,2)),g.OR(g.eqi(P,3),g.eqi(P,5)))
    for i in range(2):
        sel=g.both(lane,g.both(padpattern,g.both(g.gt(L,18),g.both(g.gt(H,6),g.lt(g.rnd(630+i),g.add(.2,g.mul(q['Verticality'],.65)))))))
        if i:sel=g.both(sel,g.OR(g.eqi(P,2),g.eqi(P,3)))
        pl=g.lo(g.mul(L,.24),g.choose(g.rnd(634,0,2,'INT'),[6,10,16]));pw=g.lo(g.mul(W,.36),g.rnd(635,4,7))
        lateral=g.mul(g.mul(side,1 if i==0 else -1),g.lo(g.mul(W,.20),3.5))
        lateral=g.switch(g.eqi(P,1),lateral,0,'FLOAT')
        height=g.lo(g.sub(H,2),g.add(g.rnd(636,3.2,5.4),i*2.2))
        candidates.append(make(hp,3,0,(pl,pw,.55),g.offset(g.mul(L,.30 if i==0 else .70),lateral,height),sel,g.mul(yaw,1 if i==0 else -.6),i,5,1))
    rise=g.lo(g.sub(H,2.5),g.add(5,g.mul(q['Verticality'],4)));ramplen=g.div(rise,g.math('TANGENT',g.mul(q['Ramp Steepness'],math.pi/180)))
    rampselect=g.both(lane,g.both(g.eqi(P,8),g.both(g.gt(L,g.add(ramplen,10)),g.both(g.gt(rise,3),g.lt(g.rnd(640),g.lo(1,g.add(q['Ramp Presence'],g.mul(q['Slide Bias'],.5))))))))
    candidates.append(make(hp,4,g.switch(g.gt(q['Ramp Steepness'],60),6,7,'INT'),(ramplen,g.lo(7,g.mul(W,.65)),rise),g.offset(g.mul(L,.42),0,g.add(.5,g.mul(rise,.5))),rampselect,0,0,4,2))
    bridgeselect=g.both(lane,g.both(g.eqi(P,4),g.both(g.gt(H,8),g.both(g.gt(L,35),g.lt(g.rnd(641),q['Route Complexity'])))))
    candidates.append(make(hp,5,8,(g.lo(g.mul(L,.5),26),3.5,.55),g.offset(g.mul(L,.55),g.mul(side,2),g.lo(g.mul(H,.5),7)),bridgeselect,g.mul(yaw,.4),0,6,2))

    # One arena floor and a bounded set of LARGE edge masses. The middle stays open.
    arena_count=g.add(1,g.math('FLOOR',g.mul(q['Density'],g.rnd(650,1,3.99))))
    for i in range(3):
        al=g.lo(g.mul(L,.32),speed*1.8);aw=g.lo(g.mul(W,.31),speed)
        ah=g.lo(g.sub(H,2),g.add(g.rnd(651,5,8),i*2.8))
        select=g.both(arena,g.both(g.gt(arena_count,i+.1),g.both(g.gt(H,8),g.lt(g.rnd(652+i),g.add(.35,g.mul(q['Verticality'],.6))))))
        x=[.24,.68,.5][i];s=[1,-1,1][i]
        candidates.append(make(hp,3,1,(al,aw,.65),g.offset(g.mul(L,x),g.mul(g.mul(W,.29),s),ah),select,g.mul(yaw,.4),10+i,4,2))
    for i in range(2):
        wh=g.lo(g.sub(H,1.4),g.rnd(660+i,5,9));wl=g.lo(g.mul(L,.36),metrics['wallrun']*.55)
        candidates.append(make(hp,2,4,(wl,.6,wh),g.offset(g.mul(L,.28 if i==0 else .74),g.mul(g.sub(g.mul(W,.5),1),1 if i==0 else -1),g.add(.6,g.mul(wh,.5))),g.both(arena,g.lt(g.rnd(662+i),q['Wallrun Bias'])),0,10+i,5,2))
    arena_rise=g.lo(g.sub(H,3),g.rnd(665,7,11));arena_run=g.div(arena_rise,g.math('TANGENT',g.mul(q['Ramp Steepness'],math.pi/180)))
    candidates.append(make(hp,4,7,(arena_run,g.lo(g.mul(W,.2),10),arena_rise),g.offset(g.mul(L,.78),g.mul(W,.25),g.add(.6,g.mul(arena_rise,.5))),g.both(arena,g.both(g.gt(H,10),g.lt(g.rnd(666),q['Ramp Presence']))),0,10,6,2))
    arena_anchor=g.plus(g.position(),g.offset(g.mul(L,.5),0,g.lo(g.sub(H,1),12)))
    ahp=g.put(hp,'grapple_required',False,'BOOLEAN')
    candidates.append(make(ahp,10,0,(.48,.48,.48),g.offset(g.mul(L,.5),0,g.lo(g.sub(H,1),12)),g.both(arena,g.both(g.lt(g.rnd(667),q['Grapple Bias']),g.inside(envelope,arena_anchor,.6))),0,10,3,0))

    # Fixed V04 elevation lattice, thinned to 3-level beats with side/height
    # variation and missing beats. Wide arenas do not get a second pad carpet.
    vp=g.put(vp,'section_id',g.spatial_id(g.vec(g.separate(g.position())[0],g.separate(g.position())[1],g.mul(g.math('FLOOR',g.div(g.separate(g.position())[2],24)),24))),'INT')
    vp=g.put(vp,'patch_id',g.attri('section_id'),'INT');vp=g.put(vp,'local_seed',g.hash_id(g.attri('section_id'),q['Seed']),'INT')
    vp=g.put(vp,'variant_identity',g.spatial_id(g.position()),'INT');vp=g.put(vp,'section_start',g.position(),'FLOAT_VECTOR');vp=g.put(vp,'local_forward',g.named('forward'),'FLOAT_VECTOR')
    vp=g.put(vp,'primitive_budget',3,'INT');vp=g.put(vp,'pattern_id',11,'INT');vp=g.put(vp,'arena_score',arena_score())
    tall=g.gt(H,g.hi(24,g.mul(g.lo(W,PL),1.7)))
    select=g.both(tall,g.both(g.lt(g.attrf('arena_score'),.999),g.both(g.lt(g.math('MODULO',g.attri('lp_duplicate'),3),.1),g.lt(g.rnd(670),g.add(.3,g.mul(g.mul(q['Density'],q['Verticality']),.65))))))
    vp=g.filter(vp,select)
    vsign=g.switch(g.lt(g.math('MODULO',g.math('FLOOR',g.div(g.attri('lp_duplicate'),3)),2),.5),-1,1,'FLOAT')
    pad=g.gt(g.rnd(671),.32);vside=g.mul(vsign,g.lo(g.mul(W,.23),4));vlen=g.lo(g.mul(g.named('beat'),.6),7)
    candidates.append(make(vp,7,10,(vlen,g.lo(g.mul(W,.40),6),.55),g.offset(g.rnd(672,-1.2,1.2),vside,g.rnd(673,0,.8)),pad,g.mul(yaw,.65),0,7,0))
    candidates.append(make(vp,8,3,(g.lo(g.named('beat'),8),.5,6.2),g.offset(0,g.mul(vsign,g.sub(g.mul(W,.5),.6)),2),g.both(g.NOT(pad),g.lt(g.rnd(674),q['Wallrun Bias'])),0,0,7,1))
    vhelper=g.put(vp,'grapple_required',False,'BOOLEAN');vhelper=g.put(vhelper,'source_span',g.attri('section_id'),'INT')
    vhpos=g.plus(g.position(),g.offset(0,0,3.8))
    candidates.append(make(vhelper,10,0,(.48,.48,.48),g.offset(0,0,3.8),g.both(g.lt(g.rnd(675),g.mul(q['Grapple Bias'],.6)),g.inside(envelope,vhpos,.6)),0,20,3,0))
    allcandidates=g.join(candidates)
    accepted,rejected=g.solve(allcandidates,accepted_reserves,'Composition occupancy')
    realpoints=g.filter(accepted,g.lt(g.attri('primitive_role'),90));surfacepoints=g.filter(realpoints,g.lt(g.attri('primitive_role'),9));helperpoints=g.filter(realpoints,g.gt(g.attri('primitive_role'),8))
    # Eleven simple prototypes. The V05 exotic library has no Object Info
    # dependency in V06's evaluation path.
    pack=g.node('GeometryNodeGeometryToInstance','Simple active primitives')
    # Blender multi-input insertions prepend; reverse construction preserves
    # the canonical primitive_id -> instance index order.
    for row in reversed(manifest):
        info=g.node('GeometryNodeObjectInfo',row['name'],transform_space='ORIGINAL');g.set(info,'Object',bpy.data.objects[row['object']]);g.set(info,'As Instance',False);g.set(pack,'Geometry',info.outputs['Geometry'])
    primitive=g.attri('primitive_id');reference=g.vec(*[g.choose(primitive,[r['dimensions'][k] for r in manifest]) for k in range(3)])
    inst=g.node('GeometryNodeInstanceOnPoints','Accepted gameplay primitives');g.set(inst,'Points',surfacepoints);g.set(inst,'Instance',pack.outputs[0]);g.set(inst,'Pick Instance',True);g.set(inst,'Instance Index',primitive)
    g.set(inst,'Rotation',g.rotation(g.attrv('occ_x'),g.attrv('occ_z')));g.set(inst,'Scale',g.vector('DIVIDE',g.attrv('occ_size'),reference))
    real=g.node('GeometryNodeRealizeInstances');g.set(real,'Geometry',inst.outputs[0]);raw=g.store(real.outputs[0],'surface_role',g.attri('primitive_role'),'INT','FACE')
    raw=g.store(raw,'primitive_id',g.attri('primitive_id'),'INT','FACE')
    mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',raw);g.set(mat,'Material',v05.v04.material('V06_NEUTRAL_BLOCKOUT',(.48,.53,.56)));raw=mat.outputs[0]
    debug=raw
    for cls,color in [(1,(.24,.49,.85)),(2,(.22,.72,.48)),(3,(.95,.52,.13)),(4,(.96,.12,.46))]:
        mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',debug);g.set(mat,'Selection',g.eqi(g.attri('span_class'),cls));g.set(mat,'Material',v05.v04.material('V06_SPAN_'+str(cls),color));debug=mat.outputs[0]
    raw=g.switch(q['Debug Span Colors'],raw,debug)
    sphere=g.node('GeometryNodeMeshIcoSphere');g.set(sphere,'Radius',.5);g.set(sphere,'Subdivisions',1)
    hi=g.node('GeometryNodeInstanceOnPoints','Clear procedural helper markers');g.set(hi,'Points',helperpoints);g.set(hi,'Instance',sphere.outputs[0]);g.set(hi,'Scale',g.attrv('occ_size'))
    hr=g.node('GeometryNodeRealizeInstances');g.set(hr,'Geometry',hi.outputs[0]);helpers=hr.outputs[0]
    for selection,name,color in [(True,'OPTIONAL_GRAPPLE',(.95,.68,.14)),(g.eqi(g.attri('primitive_role'),9),'REQUIRED_GRAPPLE',(1,.12,.45))]:
        mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',helpers);g.set(mat,'Selection',selection);g.set(mat,'Material',v05.v04.material('V06_'+name,color));helpers=mat.outputs[0]
    # Wire OBB diagnostics: accepted actual boxes plus reserved D corridor.
    cube=g.node('GeometryNodeMeshCube');g.set(cube,'Size',(1,1,1))
    wi=g.node('GeometryNodeInstanceOnPoints','Accepted OBB diagnostics');g.set(wi,'Points',accepted);g.set(wi,'Instance',cube.outputs[0]);g.set(wi,'Scale',g.attrv('occ_size'));g.set(wi,'Rotation',g.rotation(g.attrv('occ_x'),g.attrv('occ_z')))
    wr=g.node('GeometryNodeRealizeInstances');g.set(wr,'Geometry',wi.outputs[0]);edge=g.node('GeometryNodeMeshToCurve');g.set(edge,'Mesh',wr.outputs[0]);circle=g.node('GeometryNodeCurvePrimitiveCircle');g.set(circle,'Resolution',4);g.set(circle,'Radius',.025)
    wm=g.node('GeometryNodeCurveToMesh');g.set(wm,'Curve',edge.outputs[0]);g.set(wm,'Profile Curve',circle.outputs[0]);wires=wm.outputs[0]
    mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',wires);g.set(mat,'Material',v05.v04.material('V06_PLACEMENT_DEBUG',(.15,.9,.65)));wires=mat.outputs[0]
    chosen=g.switch(g.eqi(mode,1),raw,helpers)
    fast=g.mesh_boolean('INTERSECT',chosen,envelope,'MANIFOLD');exact=g.mesh_boolean('INTERSECT',chosen,envelope,'EXACT');clipped=g.switch(g.gt(q['Preview Quality'],.5),fast,exact)
    sizes=g.node('GeometryNodeAttributeDomainSize',component='MESH');g.set(sizes,'Geometry',chosen);clipped=g.switch(g.gt(sizes.outputs['Face Count'],0),None,clipped)
    sub=g.mesh_boolean('DIFFERENCE',clipped,cutgeo,'EXACT');clipped=g.switch(q['Use Cutter'],clipped,sub);clipped=g.switch(valid,None,clipped)
    result=g.switch(g.both(q['Debug Placement Volumes'],g.eqi(mode,0)),clipped,g.join([clipped,wires]))
    for value,geo in [(2,hp),(3,envelope),(4,raw),(5,helperpoints),(6,realpoints),(7,wires),(8,g.join([rejected,rejected_reserves])),(9,allcandidates)]:result=g.switch(g.eqi(mode,value),result,geo)
    g.output('Geometry',result);g.tree['active_primitives']=json.dumps([r['name'] for r in manifest]);g.tree['patterns']=json.dumps(PATTERNS);g.tree['primitive_roles']=json.dumps(ROLES);g.tree['primitive_clearance_m']=occ.CLEARANCE;g.tree['span_bands_m']=json.dumps(v05.span_bands(metrics));g.tree['occupancy']='Native Repeat Zone, greedy priority order, AABB broad phase and conservative six-face OBB test, wedge boxes, required corridor reservation.'
    g.arrange();return g.tree
