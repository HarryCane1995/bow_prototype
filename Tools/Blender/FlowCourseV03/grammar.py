"""Native Geometry Nodes segment grammar; no runtime Python topology updates."""
import bpy, math, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'LevelBlockoutV02'))
from geometry import SpatialGraph

KINDS=['ENTRY','GAP_JUMP','WALLRUN','WALL_JUMP_SHAFT','SLIDE_CHUTE','STEEP_DESCENT',
       'GRAPPLE_CATCH','MIXED_PLATFORMS','ARENA_POCKET','MULTI_ROUTE','RECOVERY','RAMP_ASCENT']
COLORS=[(.25,.43,.35),(.40,.47,.53),(.31,.42,.58),(.39,.38,.55),(.56,.44,.23),(.62,.36,.20),
        (.50,.34,.52),(.40,.48,.44),(.48,.49,.50),(.32,.49,.48),(.28,.42,.36),(.51,.45,.32)]

class FlowGraph(SpatialGraph):
    def slab(self,length,width,height,x,y=0,thickness=.7,angle=0,role=0):
        n=self.node('GeometryNodeMeshCube','Traversal surface')
        self.set(n,'Size',self.vec(self.high(.05,length),width,thickness))
        geo=self.transform(n.outputs['Mesh'],self.vec(x,y,self.sub(height,thickness*.5)),rotation=self.vec(0,0,angle))
        return self.store(geo,'flow_role',role)
    def wall(self,length,height,x,y,z,angle=0):
        n=self.node('GeometryNodeMeshCube','Movement wall')
        self.set(n,'Size',self.vec(length,.7,height))
        geo=self.transform(n.outputs['Mesh'],self.vec(x,y,self.add(z,self.mul(height,.5))),rotation=self.vec(0,0,angle))
        return self.store(geo,'flow_role',1)
    def ribbon(self,wedge,x0,x1,z0,z1,width):
        dx=self.sub(x1,x0);dz=self.sub(z1,z0)
        r=self.object(wedge).outputs['Geometry']
        geo=self.transform(r,self.vec(self.mul(self.add(x0,x1),.5),0,self.low(z0,z1)),
            self.vec(dx,width,self.high(.02,self.math('ABSOLUTE',dz))),self.vec(0,0,self.switch(self.lt(dz,0),0,math.pi,'FLOAT')))
        return self.store(geo,'flow_role',2)
    def choose(self,index,items,kind='GEOMETRY'):
        result=items[0]
        for i,value in enumerate(items[1:],1):result=self.switch(self.eq(index,i),result,value,kind)
        return result

def segment_group(metrics,wedge):
    g=FlowGraph('V03_TraversalSegment')
    kind=g.input('Kind','NodeSocketInt',0);sid=g.input('Section','NodeSocketInt',0)
    seed=g.input('Seed','NodeSocketInt',17);L=g.input('Length',value=40);w=g.input('Lane Width',value=9)
    dz=g.input('Height Change',value=0);difficulty=g.input('Difficulty',value=.45)
    jitter=g.input('Wall Jitter',value=12);angle=g.input('Steep Angle',value=45)
    safe=g.input('Spawn Radius',value=8);density=g.input('Density',value=.7)
    routes=g.input('Complexity',value=.65)
    random=lambda stream,a=0,b=1:g.random(seed,sid,stream,a,b)
    factor=g.add(.5,g.mul(difficulty,.3))
    yaw=g.mul(g.mul(jitter,math.pi/180),random(12,-1,1))
    def floor(a,b,z=0,width=None,y=0,rot=0,role=0):
        return g.slab(g.sub(b,a),w if width is None else width,z,g.mul(g.add(a,b),.5),y,angle=rot,role=role)
    layouts=[]
    # 0. Spawn starts the route. Its protected pad is added later after all cutters.
    start=g.switch(g.eq(sid,0),0,safe,'FLOAT')
    layouts.append(floor(start,L))
    # 1. A measured running jump with real takeoff and landing runways.
    gap=g.low(g.mul(metrics['running_jump']-.9,factor),g.high(2,g.sub(L,16)))
    takeoff=g.mul(g.sub(L,gap),.5)
    layouts.append(g.join([floor(0,takeoff),floor(g.add(takeoff,gap),L)]))
    # 2. Two alternating wall contacts over a gap, with large endpoint pads.
    end=g.sub(L,9);wall_run=g.low(g.mul(metrics['wallrun'],factor),g.sub(L,8))
    wall_parts=[floor(0,9),floor(end,L)]
    for side in (-1,1):
        x=g.mul(L,.42 if side<0 else .65)
        wall_parts.append(g.wall(wall_run,7,x,side*3.1,-1,g.mul(yaw,side*.65)))
    layouts.append(g.join(wall_parts))
    # 3. Diagonal climb: intermediate catch platform plus a wall-jump pair.
    pair_gap=g.mul(metrics['wall_jump_lateral'],factor)
    shaft=[floor(0,g.mul(L,.27)),floor(g.mul(L,.71),L,dz),
           floor(g.mul(L,.44),g.mul(L,.58),g.mul(dz,.5),g.high(w,8),rot=g.mul(yaw,.35))]
    for side in (-1,1):
        shaft.append(g.wall(g.mul(L,.58),g.add(dz,3),g.mul(L,.5),g.mul(g.add(pair_gap,.7),side*.5),-.5,g.mul(yaw,side*.22)))
    layouts.append(g.join(shaft))
    # 4. Long slide lane: 1.25m clearance and a 6m-wide bottleneck, no global roof.
    low=[floor(0,L),floor(g.mul(L,.25),g.mul(L,.67),1.95,7,role=3)]
    for side in (-1,1):low.append(g.wall(g.mul(L,.50),2.3,g.mul(L,.47),side*3.6,0))
    layouts.append(g.join(low))
    # 5. A steep descent plus a long catch, dimensioned for the current speed carry.
    run=g.div(g.neg(dz),g.math('TANGENT',g.mul(angle,math.pi/180)))
    lip=7;foot=g.add(lip,run)
    descent=[floor(0,lip),g.ribbon(wedge,lip,foot,0,dz,g.add(w,2)),floor(foot,L,dz,g.high(14,g.add(w,4)))]
    layouts.append(g.join(descent))
    # 6. A real grapple break: long recovery platform and exported canonical anchor.
    layouts.append(g.join([floor(0,g.mul(L,.16),0,g.high(12,w)),floor(g.mul(L,.48),L,dz,g.high(18,g.mul(w,1.7)))]))
    # 7. Staggered, mildly rotated stepping islands on a rising directed lane.
    mixed=[floor(0,g.mul(L,.2)),floor(g.mul(L,.83),L,dz)]
    for i in range(3):
        t=.32+i*.19
        mixed.append(g.slab(g.low(10,g.mul(L,.17)),g.high(8,g.mul(w,.85)),g.mul(dz,(i+1)/4),
            g.mul(L,t),g.mul(random(30+i,-1,1),g.mul(w,.36)),angle=g.mul(yaw,(-1 if i%2 else 1)*.55)))
    layouts.append(g.join(mixed))
    # 8. A widening pocket punctuates the narrow route. Only gameplay cover walls.
    arena=[floor(0,L),g.slab(g.low(30,g.mul(L,.72)),g.add(22,g.mul(w,.65)),0,g.mul(L,.5))]
    for side in (-1,1):arena.append(g.keep(g.wall(7,3.2,g.mul(L,.5+side*.12),side*8,0,g.add(g.mul(yaw,side),side*.28)),g.gt(density,.15 if side<0 else .5)))
    layouts.append(g.join(arena))
    # 9. Split/rejoin: centre lane plus up to two short air-jump side routes.
    multi=[floor(0,L,0,6)]
    for side in (-1,1):
        branch=[]
        for i in range(3):branch.append(g.slab(9,7,2 if i!=1 else 3.8,g.mul(L,.2+i*.3),side*(7 if i!=1 else 10),angle=g.mul(yaw,.5)))
        branch.append(g.keep(g.wall(15,4.2,g.mul(L,.5),side*13,2.8,g.mul(yaw,side)),g.gt(density,.4)))
        multi.append(g.keep(g.join(branch),g.gt(routes,.3 if side<0 else .65)))
    layouts.append(g.join(multi))
    # 10. Finish/recovery bridge, deliberately broad and unobstructed.
    layouts.append(floor(0,L,0,16))
    # 11. Speed-biased ascent creates height for a later strong descent.
    layouts.append(g.join([floor(0,6),g.ribbon(wedge,6,g.sub(L,6),0,dz,w),floor(g.sub(L,6),L,dz)]))
    geometry=g.choose(kind,layouts)
    geometry=g.store(geometry,'flow_gap',g.switch(g.eq(kind,1),0,gap,'FLOAT'),'FLOAT')
    geometry=g.store(geometry,'flow_wall_pair_gap',pair_gap,'FLOAT')
    geometry=g.store(geometry,'flow_wall_yaw',yaw,'FLOAT')
    g.output('Geometry',geometry);g.arrange()
    return g.tree
