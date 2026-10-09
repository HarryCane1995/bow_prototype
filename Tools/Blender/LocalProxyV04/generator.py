"""Native GN local surface patches and height lattices; no authoring-mesh writes.

Python constructs the graph once. Blender's depsgraph owns all subsequent edits.
The graph never computes a bounding box of the complete proxy.
"""
import math
import sys
from pathlib import Path
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'LevelBlockout'))
from nodes import Graph

NAME = 'GN_LevelProxyGenerator_v04'
CONTROLS = [
    ('Seed', 'NodeSocketInt', 17, 0, 1000000, 'Global seed; spatial local IDs do not use face indices.'),
    ('Density', 'NodeSocketFloat', .58, 0, 1, 'Optional obstacles, not the size of the proxy.'),
    ('Verticality', 'NodeSocketFloat', .72, 0, 1, 'Probability of intermediate floating landings.'),
    ('Openness', 'NodeSocketFloat', .7, 0, 1, 'Reduce wall clutter and leave open air.'),
    ('Route Complexity', 'NodeSocketFloat', .55, 0, 1, 'Secondary ledges and lateral transfers.'),
    ('Traversal Difficulty', 'NodeSocketFloat', .4, 0, 1, 'Gap and stagger within measured movement budgets.'),
    ('Wallrun Bias', 'NodeSocketFloat', .6, 0, 1, 'Local wall strips and wall-jump contacts.'),
    ('Slide Bias', 'NodeSocketFloat', .3, 0, 1, 'Short passages with 1.35 m clear headroom.'),
    ('Grapple Bias', 'NodeSocketFloat', .65, 0, 1, 'Procedural Blender helper candidates; not runtime anchors.'),
    ('Ramp Presence', 'NodeSocketFloat', .4, 0, 1, 'Optional local wedges with a recovery landing.'),
    ('Ramp Steepness', 'NodeSocketFloat', 55., 45, 70, 'Geometric slope in degrees; steep gameplay remains untested.'),
    ('Orientation Randomness', 'NodeSocketFloat', 8., 0, 25, 'Local obstacle yaw in degrees.'),
    ('Platform Density', 'NodeSocketFloat', .65, 0, 1, 'Vertical step spacing: 4.8 down to 3.1 m.'),
    ('Preview Quality', 'NodeSocketInt', 0, 0, 1, '0 Manifold intersection; 1 Exact intersection.'),
    ('Use Cutter', 'NodeSocketBool', False, None, None, 'Subtract LEVEL_CUTTER after containment.'),
]


class LocalGraph(Graph):
    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def mul(self, a, b): return self.math('MULTIPLY', a, b)
    def div(self, a, b): return self.math('DIVIDE', a, b)
    def lo(self, a, b): return self.math('MINIMUM', a, b)
    def hi(self, a, b): return self.math('MAXIMUM', a, b)
    def gt(self, a, b): return self.math('GREATER_THAN', a, b)
    def lt(self, a, b): return self.math('LESS_THAN', a, b)
    def absolute(self, a): return self.math('ABSOLUTE', a)
    def both(self, a, b): return self.boolean('AND', a, b)
    def vscale(self, v, s):
        n = self.node('ShaderNodeVectorMath', operation='SCALE')
        self.set(n, 0, v); self.set(n, 'Scale', s)
        return n.outputs['Vector']
    def plus(self, *vs):
        result = vs[0]
        for v in vs[1:]: result = self.vector('ADD', result, v)
        return result
    def norm(self, v): return self.vector('NORMALIZE', v)
    def position(self): return self.node('GeometryNodeInputPosition').outputs[0]
    def named(self, name): return self.attr('lp_' + name, 'FLOAT_VECTOR' if name in ['forward','up','side','center'] else 'FLOAT')
    def spatial_id(self, p):
        # Hash a vector quantized to centimetres. No index or total-bounds input.
        # Round, rather than floor/snap: a -2e-7 ray/merge error at x=0 must
        # not select the adjacent centimetre cell and reroll the whole shaft.
        q = self.vector('FLOOR',self.plus(self.vscale(p,100),(.5,.5,.5)))
        n = self.node('FunctionNodeHashValue', 'Local spatial identity', data_type='VECTOR')
        self.set(n, 'Value', q)
        return n.outputs[0]
    def ray(self, geo, p, direction, distance=1000):
        n = self.node('GeometryNodeRaycast')
        for k,v in [('Target Geometry',geo),('Source Position',p),('Ray Direction',direction),('Ray Length',distance)]: self.set(n,k,v)
        return n
    def stamp(self, geo, values, domain='POINT'):
        for key,value in values.items():
            kind = 'FLOAT_VECTOR' if key in ['forward','up','side','center'] else 'FLOAT'
            geo = self.store(geo,'lp_'+key,value,kind,domain)
        return geo
    def setpos(self, geo, p=None, offset=None):
        n=self.node('GeometryNodeSetPosition');self.set(n,'Geometry',geo)
        if p is not None:self.set(n,'Position',p)
        if offset is not None:self.set(n,'Offset',offset)
        return n.outputs[0]
    def duplicate(self, geo, count):
        n=self.node('GeometryNodeDuplicateElements',domain='POINT');self.set(n,'Geometry',geo);self.set(n,'Amount',count)
        return self.store(n.outputs['Geometry'],'lp_duplicate',n.outputs['Duplicate Index'],'INT','POINT')
    def rotation(self, forward, up):
        n=self.node('FunctionNodeAxesToRotation',primary_axis='X',secondary_axis='Z')
        self.set(n,'Primary Axis',forward);self.set(n,'Secondary Axis',up)
        return n.outputs[0]
    def offset(self,x=0,y=0,z=0):
        return self.plus(self.vscale(self.named('forward'),x),self.vscale(self.named('side'),y),self.vscale(self.named('up'),z))
    def instance(self, points, shape, scale, offset=(0,0,0), selection=True, yaw=0, role=0, material=None):
        pts=self.setpos(points,offset=offset)
        n=self.node('GeometryNodeInstanceOnPoints',f'Surface role {role}')
        c=self.math('COSINE',yaw);s=self.math('SINE',yaw)
        f=self.plus(self.vscale(self.named('forward'),c),self.vscale(self.named('side'),s))
        for k,v in [('Points',pts),('Instance',shape),('Selection',selection),('Scale',scale),('Rotation',self.rotation(f,self.named('up')))]:self.set(n,k,v)
        real=self.node('GeometryNodeRealizeInstances');self.set(real,'Geometry',n.outputs[0]);geo=real.outputs[0]
        geo=self.store(geo,'surface_role',role,'INT','FACE')
        if material:
            mat=self.node('GeometryNodeSetMaterial');self.set(mat,'Geometry',geo);self.set(mat,'Material',material);geo=mat.outputs[0]
        return geo


def material(name, color):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.8
    return m


def build(metrics, wedge):
    g=LocalGraph(NAME)
    proxy=g.input('Proxy','NodeSocketObject')
    cutter=g.input('Cutter','NodeSocketObject')
    controls={name:g.input(name,kind,value,low,high,desc) for name,kind,value,low,high,desc in CONTROLS}
    mode=g.input('Output Mode','NodeSocketInt',0,0,4,'Internal: 0 surfaces, 1 helpers, 2 local samples, 3 clean envelope, 4 unclipped surfaces.')
    q=controls;seed=q['Seed'];rnd=lambda stream,a=0,b=1:g.random(seed,g.spatial_id(g.position()),stream,a,b)
    info=g.node('GeometryNodeObjectInfo','Actual authored volume',transform_space='RELATIVE');g.set(info,'Object',proxy);g.set(info,'As Instance',False)
    area=g.node('GeometryNodeInputMeshFaceArea').outputs[0]
    delete=g.node('GeometryNodeDeleteGeometry','Evaluation-only degenerate cleanup',domain='FACE',mode='ONLY_FACE')
    g.set(delete,'Geometry',info.outputs['Geometry']);g.set(delete,'Selection',g.lt(area,1e-7))
    merge=g.node('GeometryNodeMergeByDistance','Evaluation-only coincident rings');g.set(merge,'Geometry',delete.outputs[0]);g.set(merge,'Distance',.0001)
    clean=merge.outputs[0]
    edgecount=g.node('GeometryNodeInputMeshEdgeNeighbors').outputs[0]
    invalid=g.gt(g.absolute(g.sub(edgecount,2)),.1)
    stat=g.node('GeometryNodeAttributeStatistic','Closed-volume guard',data_type='FLOAT',domain='EDGE')
    g.set(stat,'Geometry',clean);g.set(stat,'Attribute',invalid)
    valid=g.lt(stat.outputs['Sum'],.5)

    # Local quad frame. Opposite edge pairs are averaged; no mesh-wide dimensions.
    faceindex=g.node('GeometryNodeInputIndex').outputs[0]
    corner=g.node('GeometryNodeCornersOfFace');g.set(corner,'Face Index',faceindex)
    vertices=[]
    for i in range(4):
        off=g.node('GeometryNodeOffsetCornerInFace');g.set(off,'Corner Index',corner.outputs['Corner Index']);g.set(off,'Offset',i)
        vertex=g.node('GeometryNodeVertexOfCorner');g.set(vertex,'Corner Index',off.outputs[0])
        sample=g.node('GeometryNodeSampleIndex',data_type='FLOAT_VECTOR',domain='POINT');g.set(sample,'Geometry',clean);g.set(sample,'Value',g.position());g.set(sample,'Index',vertex.outputs[0]);vertices.append(sample.outputs[0])
    edges=[g.vector('SUBTRACT',vertices[(i+1)%4],vertices[i]) for i in range(4)]
    lens=[g.vector('LENGTH',v) for v in edges]
    a=g.mul(g.add(lens[0],lens[2]),.5);b=g.mul(g.add(lens[1],lens[3]),.5)
    d0=g.vector('SUBTRACT',edges[0],edges[2]);d1=g.vector('SUBTRACT',edges[1],edges[3])
    forward=g.norm(g.switch(g.gt(b,a),d0,d1,'VECTOR'))
    fx,fy,fz=g.separate(forward)
    sign=g.switch(g.gt(g.absolute(fx),g.absolute(fy)),fy,fx,'FLOAT')
    forward=g.vscale(forward,g.switch(g.lt(sign,0),1,-1,'FLOAT'))
    normal=g.node('GeometryNodeInputNormal').outputs['Normal'];nx,ny,nz=g.separate(normal)
    up=g.vscale(normal,-1);side=g.norm(g.vector('CROSS_PRODUCT',up,forward))
    ceiling=g.ray(clean,g.plus(g.position(),g.vscale(up,.02)),up)
    height=g.add(ceiling.outputs['Hit Distance'],.02)
    horizontal=g.both(g.lt(nz,-.35),g.both(g.gt(g.lo(a,b),1.4),g.gt(height,2.1)))
    facegeo=g.stamp(clean,{'forward':forward,'up':up,'side':side,'center':g.position(),'length':g.hi(a,b),'width':g.lo(a,b),'height':height,'kind':0},'FACE')
    m=g.node('GeometryNodeMeshToPoints','Horizontal or inclined local patches',mode='FACES');g.set(m,'Mesh',facegeo);g.set(m,'Selection',horizontal)
    step=18.0
    count=g.hi(1,g.math('CEIL',g.div(g.named('length'),step)))
    hp=g.stamp(m.outputs[0],{'count':count,'beat':g.div(g.named('length'),count)})
    hp=g.duplicate(hp,g.named('count'))
    along=g.sub(g.mul(g.add(g.attr('lp_duplicate','INT'),.5),g.named('beat')),g.mul(g.named('length'),.5))
    hp=g.setpos(hp,offset=g.vscale(g.named('forward'),along))
    hp=g.stamp(hp,{'center':g.position()})

    # Tall side patches yield a fixed elevation lattice. A new cap does not
    # redistribute old landings. Downcasts reconnect split shaft wall patches.
    zcoords=[g.separate(v)[2] for v in vertices]
    bottom=zcoords[0];top=zcoords[0]
    for z in zcoords[1:]:bottom=g.lo(bottom,z);top=g.hi(top,z)
    h=g.sub(top,bottom)
    nxy=g.norm(g.vec(nx,ny,0));axis=g.norm(g.vector('CROSS_PRODUCT',(0,0,1),nxy))
    projections=[g.vector('DOT_PRODUCT',v,axis) for v in vertices]
    pmin=projections[0];pmax=projections[0]
    for p in projections[1:]:pmin=g.lo(pmin,p);pmax=g.hi(pmax,p)
    span=g.sub(pmax,pmin)
    across=g.ray(clean,g.plus(g.position(),g.vscale(normal,-.02)),g.vscale(normal,-1))
    depth=g.add(across.outputs['Hit Distance'],.02)
    mid=g.plus(g.position(),g.vscale(normal,g.mul(depth,-.5)))
    down=g.ray(clean,mid,(0,0,-1));base=g.separate(down.outputs['Hit Position'])[2]
    chosen=g.both(g.gt(nx,g.absolute(ny)),g.both(g.lt(g.absolute(nz),.15),g.both(g.gt(h,5),g.both(g.gt(depth,4),g.gt(span,4)))))
    chosen=g.both(chosen,g.both(across.outputs['Is Hit'],down.outputs['Is Hit']))
    vf=g.stamp(clean,{'center':mid,'forward':axis,'side':g.vscale(nxy,-1),'up':g.vec(0,0,1),'length':span,'width':depth,'height':h,'base':base,'top':top,'kind':1},'FACE')
    mp=g.node('GeometryNodeMeshToPoints','Shaft and upper-space patches',mode='FACES');g.set(mp,'Mesh',vf);g.set(mp,'Selection',chosen);g.set(mp,'Position',g.named('center'))
    vcount=g.hi(1,g.math('CEIL',g.div(g.named('length'),18)))
    vp=g.stamp(mp.outputs[0],{'count':vcount,'beat':g.div(g.named('length'),vcount)})
    vp=g.duplicate(vp,g.named('count'))
    along=g.sub(g.mul(g.add(g.attr('lp_duplicate','INT'),.5),g.named('beat')),g.mul(g.named('length'),.5))
    vp=g.setpos(vp,offset=g.vscale(g.named('forward'),along))
    spacing=g.sub(4.8,g.mul(q['Platform Density'],1.7))
    first=g.add(g.named('base'),spacing)
    levels=g.hi(0,g.add(1,g.math('FLOOR',g.div(g.sub(g.sub(g.named('top'),2.4),first),spacing))))
    vp=g.stamp(vp,{'first':first,'levels':levels})
    vp=g.duplicate(vp,g.named('levels'))
    vx,vy,vz=g.separate(g.position())
    vp=g.setpos(vp,g.vec(vx,vy,g.add(g.named('first'),g.mul(g.attr('lp_duplicate','INT'),spacing))))
    pv=g.node('GeometryNodePointsToVertices');g.set(pv,'Points',vp)
    mv=g.node('GeometryNodeMergeByDistance','Deduplicate overlapping shaft levels');g.set(mv,'Geometry',pv.outputs[0]);g.set(mv,'Distance',.002);vp=mv.outputs[0]
    # Stabilize sub-micron ray/merge drift without moving the authored proxy.
    rounded=g.vscale(g.vector('FLOOR',g.plus(g.vscale(g.position(),10000),(.5,.5,.5))),.0001)
    vp=g.setpos(vp,rounded)
    vp=g.stamp(vp,{'center':g.position()})
    allpoints=g.join([hp,vp])
    allpoints=g.store(allpoints,'segment_id',g.spatial_id(g.position()),'INT','POINT')

    cube=g.node('GeometryNodeMeshCube','One metre gameplay primitive');g.set(cube,'Size',(1,1,1));unit=cube.outputs['Mesh']
    wedgeinfo=g.node('GeometryNodeObjectInfo','Unit ramp only',transform_space='ORIGINAL');g.set(wedgeinfo,'Object',wedge);unitw=wedgeinfo.outputs['Geometry']
    mats=[material('V04L_Landing',(.39,.51,.59)),material('V04L_Wall',(.22,.36,.52)),material('V04L_Floating',(.28,.60,.53)),material('V04L_Ramp',(.78,.44,.22)),material('V04L_Slide',(.59,.45,.69)),material('V04L_Grapple',(.97,.68,.12))]
    W=g.named('width');B=g.named('beat');H=g.named('height')
    yaw=g.mul(g.mul(q['Orientation Randomness'],math.pi/180),rnd(15,-1,1))
    diff=q['Traversal Difficulty']
    gap=g.lo(g.mul(B,.42),g.mul(metrics['running_jump'],g.add(.28,g.mul(diff,.20))))
    floorld=g.hi(2,g.sub(B,gap));floorwd=g.hi(1,g.sub(W,.4))
    items=[]
    items.append(g.instance(hp,unit,g.vec(floorld,floorwd,.5),g.offset(0,0,.28),role=0,material=mats[0]))
    wallsel=g.lt(rnd(21),g.mul(q['Wallrun Bias'],g.sub(1,g.mul(q['Openness'],.45))))
    wallh=g.lo(g.sub(H,1.2),g.add(3,g.mul(q['Verticality'],3.5)))
    walllen=g.lo(g.mul(B,.88),metrics['wallrun']*.42)
    wallside=g.switch(g.lt(rnd(22),.5),-1,1,'FLOAT')
    walloff=g.mul(wallside,g.lo(g.mul(W,.35),3.8))
    items.append(g.instance(hp,unit,g.vec(walllen,.42,wallh),g.offset(0,walloff,g.add(.55,g.mul(wallh,.5))),wallsel,yaw,1,mats[1]))
    secondary=g.both(g.gt(W,16),g.lt(rnd(23),q['Route Complexity']))
    items.append(g.instance(hp,unit,g.vec(g.lo(7,g.mul(B,.4)),g.lo(6,g.mul(W,.24)),.45),g.offset(rnd(24,-2,2),g.mul(W,-.26),g.lo(g.mul(H,.35),4.2)),secondary,yaw,2,mats[2]))
    slide=g.both(g.lt(rnd(30),g.mul(q['Slide Bias'],q['Density'])),g.gt(H,3))
    items.append(g.instance(hp,unit,g.vec(g.lo(5,g.mul(floorld,.8)),g.lo(5.5,g.mul(W,.75)),.3),g.offset(0,0,2.03),slide,0,4,mats[4]))
    rise=g.lo(g.sub(H,2.7),g.add(2.2,g.mul(q['Verticality'],3)))
    run=g.div(rise,g.math('TANGENT',g.mul(q['Ramp Steepness'],math.pi/180)))
    rampsel=g.both(g.gt(rise,1),g.lt(rnd(41),g.mul(q['Ramp Presence'],g.add(.5,g.mul(q['Density'],.5)))))
    items.append(g.instance(hp,unitw,g.vec(run,g.lo(3.8,g.mul(W,.3)),rise),g.offset(g.mul(floorld,.1),g.mul(W,.20),.55),rampsel,0,3,mats[3]))
    # Local vertical movement: 3.1-4.8 m rises (< observed 5.6 m air rise),
    # <= 6.0 m paired-wall spacing (< observed 9.53 m lateral wall jump).
    stagger=g.mul(g.switch(g.lt(rnd(60),.5),-1,1,'FLOAT'),g.lo(g.mul(W,.22),g.add(1.4,g.mul(diff,1.3))))
    padlen=g.lo(6.8,g.mul(B,.68));padwd=g.lo(5.2,g.mul(W,.48))
    pads=g.lt(rnd(61),g.add(.35,g.mul(q['Verticality'],.65)))
    items.append(g.instance(vp,unit,g.vec(padlen,padwd,.42),g.offset(rnd(62,-.7,.7),stagger,0),pads,g.mul(yaw,.4),2,mats[2]))
    vwalls=g.lt(rnd(63),g.mul(q['Wallrun Bias'],q['Density']))
    for s in [-1,1]:
        items.append(g.instance(vp,unit,g.vec(g.lo(6.5,g.mul(B,.74)),.35,2.8),g.offset(s*.45,g.mul(g.lo(g.mul(W,.33),3.0),s),1.0),vwalls,g.mul(yaw,.3),1,mats[1]))
    raw=g.join(items)

    # Markers are candidate catches above a landing/gap, not permanent objects.
    ico=g.node('GeometryNodeMeshIcoSphere');g.set(ico,'Radius',.26);g.set(ico,'Subdivisions',1)
    hc=g.both(g.gt(H,6),g.lt(rnd(81),q['Grapple Bias']))
    vc=g.lt(rnd(82),q['Grapple Bias'])
    helpers=g.join([
        g.instance(hp,ico.outputs['Mesh'],(1,1,1),g.offset(g.lo(g.mul(B,.36),metrics['grapple_range']*.30),0,g.lo(g.sub(H,1),8)),hc,0,5,mats[5]),
        g.instance(vp,ico.outputs['Mesh'],(1,1,1),g.offset(0,stagger,1.7),vc,0,5,mats[5]),
    ])
    # Both rendering branches receive the same final authoritative envelope.
    chosenraw=g.switch(g.gt(mode,.5),raw,helpers)
    fast=g.mesh_boolean('INTERSECT',chosenraw,clean,'MANIFOLD')
    exact=g.mesh_boolean('INTERSECT',chosenraw,clean,'EXACT')
    clipped=g.switch(g.gt(q['Preview Quality'],.5),fast,exact)
    # A multi-input Boolean ignores an empty geometry input. Intersect(empty,
    # proxy) would otherwise return the entire proxy when all helpers are off.
    size=g.node('GeometryNodeAttributeDomainSize','Empty fill must stay empty',component='MESH');g.set(size,'Geometry',chosenraw)
    clipped=g.switch(g.gt(size.outputs['Face Count'],0),None,clipped)
    ci=g.node('GeometryNodeObjectInfo','Optional local cutter',transform_space='RELATIVE');g.set(ci,'Object',cutter)
    cut=g.mesh_boolean('DIFFERENCE',clipped,ci.outputs['Geometry'],'EXACT')
    clipped=g.switch(q['Use Cutter'],clipped,cut)
    clipped=g.switch(valid,None,clipped)
    result=g.switch(g.gt(mode,1.5),clipped,allpoints)
    result=g.switch(g.gt(mode,2.5),result,clean)
    result=g.switch(g.gt(mode,3.5),result,raw)
    result=g.store(result,'proxy_valid',valid,'BOOLEAN','POINT')
    g.output('Geometry',result)
    g.tree.description='Local topology patches and fixed shaft levels, spatial seed IDs, actual mesh intersection. No global layout bounds. Closed outward volume required.'
    g.tree['authoring_runtime']='Native Geometry Nodes only; no Python handler or mesh rewrite.'
    g.tree['exterior_tolerance_m']=0.0
    g.tree['cleanup_merge_m']=.0001
    g.tree['vertical_spacing_m']='3.1-4.8'
    g.arrange()
    return g.tree
