"""Native GN traversal-region grammar. Dimensions derive from verified movement metrics."""
from nodes import Graph

CATEGORIES = ['OPEN_FLOW_AREA','JUMP_GAP','AIR_JUMP_GAP','SLIDE_JUMP_GAP',
              'SLIDE_CLEARANCE','WALLRUN_STRIP','WALL_JUMP_CHANNEL','WINDOW_OPENING',
              'RAMP_ASCENT','STEPPED_ASCENT','PILLAR_COURT','SHAFT_DROP','MULTI_LEVEL',
              'GRAPPLE_CROSSING','OVERHANG_PASSAGE']


def build_connections(g, points, seed, routes, vertical, height, wedge):
    """Optional elevated network over native candidate-grid edges, with access ramps."""
    index=g.node('GeometryNodeInputIndex').outputs[0]
    vertices=g.node('GeometryNodeInputMeshEdgeVertices','Neighbour-region endpoints')
    delta=g.vector('SUBTRACT',vertices.outputs['Position 2'],vertices.outputs['Position 1'])
    dx,dy,_=g.separate(delta)
    angle=g.math('ARCTAN2',dy,dx)
    edges=g.store(points,'bridge_angle',angle,'FLOAT','EDGE')
    probability=g.math('MULTIPLY',routes,.38)
    choose=g.math('LESS_THAN',g.random(seed,index,113),probability)
    choose=g.boolean('AND',choose,g.math('GREATER_THAN',routes,.3))
    choose=g.boolean('AND',choose,g.math('GREATER_THAN',vertical,.05))
    to_points=g.node('GeometryNodeMeshToPoints','Spatial network / selected neighbouring regions',mode='EDGES')
    g.set(to_points,'Mesh',edges);g.set(to_points,'Selection',choose)
    h=g.math('MINIMUM',height,g.math('MULTIPLY',vertical,5))
    pieces=[]
    for size,xyz in [((44,3,.55),(0,0,g.math('SUBTRACT',h,.275))),
                     ((6,6,.55),(-22,0,g.math('SUBTRACT',h,.275))),
                     ((6,6,.55),(22,0,g.math('SUBTRACT',h,.275)))]:
        n=g.node('GeometryNodeMeshCube','Network bridge / 3m clear width');g.set(n,'Size',size)
        pieces.append(g.transform(n.outputs[0],g.vec(*xyz)))
    for x in (-22,22):
        n=g.object(wedge)
        pieces.append(g.transform(n.outputs['Geometry'],(x,-11,0),g.vec(18,4,h),(0,0,1.5707963267948966)))
    geometry=g.store(g.store(g.join(pieces),'category_id',12),'part_id',100)
    instances=g.node('GeometryNodeInstanceOnPoints','Optional upper connections')
    g.set(instances,'Points',to_points.outputs['Points']);g.set(instances,'Instance',geometry)
    g.set(instances,'Rotation',g.vec(0,0,g.attr('bridge_angle','FLOAT')))
    realize=g.node('GeometryNodeRealizeInstances','Upper network geometry');g.set(realize,'Geometry',instances.outputs[0])
    return realize.outputs[0]


def build_category(index, metrics, wedge):
    g=Graph('BLK_'+CATEGORIES[index])
    factor=g.input('Difficulty factor',value=.69)
    vertical=g.input('Verticality',value=.65)
    height=g.input('Height Range',value=12)
    routes=g.input('Route Complexity',value=.6)
    solid=[];holes=[]
    def add(a,b):return g.math('ADD',a,b)
    def sub(a,b):return g.math('SUBTRACT',a,b)
    def mul(a,b):return g.math('MULTIPLY',a,b)
    def neg(a):return mul(a,-1)
    def cap(a,b):return g.math('MINIMUM',a,b)
    def rise(top):return cap(height,mul(vertical,top))
    def tag(geo,part):
        return g.store(g.store(geo,'part_id',part),'category_id',index)
    def box(part,sz,pos=(0,0,0),hole=False,conditional=None):
        n=g.node('GeometryNodeMeshCube',f'{CATEGORIES[index]} / part {part}')
        g.set(n,'Size',g.vec(*sz));geo=g.transform(n.outputs['Mesh'],g.vec(*pos))
        geo=tag(geo,part)
        if conditional is not None:geo=g.switch(conditional,None,geo)
        (holes if hole else solid).append(geo)
        return geo
    def column(part,r,h,x,y,z=0):
        n=g.node('GeometryNodeMeshCylinder',f'Column {part}')
        g.set(n,'Vertices',12);g.set(n,'Radius',r);g.set(n,'Depth',h)
        solid.append(tag(g.transform(n.outputs['Mesh'],g.vec(x,y,add(z,mul(h,.5)))),part))
    def ramp(part,length,width,h,x=0,y=0,z=0,angle=0):
        n=g.object(wedge)
        solid.append(tag(g.transform(n.outputs['Geometry'],g.vec(x,y,z),g.vec(length,width,g.math('MAXIMUM',.03,h)),(0,0,angle)),part))
    def platform(part,x,y,sx,sy,top,thickness=.55):
        box(part,(sx,sy,thickness),(x,y,sub(top,thickness/2)))
    def gap(metric):
        # Centre travel observations reserve a capsule diameter before difficulty scaling.
        return mul(factor,metrics[metric]-metrics['diameter'])
    more=g.math('GREATER_THAN',routes,.45)
    raised=rise(metrics['air_rise']*.72)
    lowrise=rise(metrics['jump_rise']*.65)
    pit=add(.5,rise(metrics['air_rise']*.8))

    if index==0:
        # Large quiet floor is provided by the parent Field. Low ledges remain optional.
        box(1,(12,2,add(.25,lowrise)),(-5,12,mul(add(.25,lowrise),.5)),conditional=more)
        box(2,(5,5,add(.2,lowrise)),(10,-12,mul(add(.2,lowrise),.5)),conditional=more)
    elif index in (1,2,3):
        metric={1:'running_jump',2:'air_jump',3:'slide_jump'}[index]
        distance=gap(metric)
        # Gap cut stops short of the region perimeter, leaving broad alternate routes.
        box(90,(distance,20,add(pit,2)),(0,0,neg(mul(pit,.5))),hole=True)
        platform(12,0,0,distance,20,neg(pit))
        # Separate launch/landing ledges have explicit part ids for geometric QA.
        x=add(mul(distance,.5),4)
        platform(10,neg(x),0,8,20,lowrise)
        platform(11,x,0,8,20,lowrise)
        # Side ledge at pit floor gives a route back in two jumpable steps.
        step=mul(pit,.5)
        platform(13,0,-8,distance,3,neg(step))
    elif index==4:
        clearance=add(metrics['slide_height'],.15)
        box(30,(12,5,.7),(0,0,add(clearance,.35)))
        box(31,(12,.8,add(clearance,.7)),(0,-2.9,mul(add(clearance,.7),.5)))
        box(32,(12,.8,add(clearance,.7)),(0,2.9,mul(add(clearance,.7),.5)))
        platform(33,12,0,7,10,lowrise)
    elif index==5:
        length=cap(39,mul(factor,metrics['wallrun']))
        distance=sub(length,8)
        box(90,(distance,9,add(pit,2)),(0,-.5,neg(mul(pit,.5))),hole=True)
        platform(12,0,-.5,distance,9,neg(pit))
        wallheight=add(metrics['standing_height']+1,rise(metrics['wallrun_rise']+1))
        box(20,(length,.9,wallheight),(0,4.5,mul(wallheight,.5)))
        platform(10,neg(add(mul(distance,.5),3.5)),0,7,7,0)
        platform(11,add(mul(distance,.5),3.5),0,7,7,0)
        box(23,(length,2.7,.55),(0,-8,lowrise),conditional=more)
    elif index==6:
        channel=gap('wall_jump_lateral')
        wallheight=add(3,rise(metrics['wall_jump_rise']*.65))
        y=add(mul(channel,.5),.5)
        box(21,(23,1,wallheight),(0,neg(y),mul(wallheight,.5)))
        box(22,(23,1,wallheight),(0,y,mul(wallheight,.5)))
        platform(24,-8,0,6,channel,lowrise)
        platform(25,8,0,6,channel,raised)
        platform(26,0,neg(add(y,2)),8,3,rise(metrics['air_rise']*.8))
    elif index==7:
        sill=mul(factor,metrics['jump_rise']*.55)
        clear=metrics['standing_height']+.3
        heightwall=add(sill,clear+2)
        box(27,(1,14,sill),(0,0,mul(sill,.5)))
        for y in (-8,8):box(28,(1,5,heightwall),(0,y,mul(heightwall,.5)))
        box(29,(1,11,2),(0,0,add(sill,clear+1)))
        platform(1,9,0,10,14,lowrise)
    elif index==8:
        h=rise(metrics['air_rise']*.7)
        platform(50,7,0,12,15,h)
        ramp(51,18,7,h,-8,0)
        platform(52,7,13,8,3,h)
    elif index==9:
        h=rise(metrics['air_rise']*.9)
        for step in range(7):
            top=mul(h,(step+1)/7)
            box(60+step,(3,8,add(top,.3)),(-12+step*3,0,sub(mul(top,.5),.15)))
        platform(67,12,0,9,15,h)
        ramp(68,20,4,h,1,12)
    elif index==10:
        for i,(x,y) in enumerate([(-12,-9),(-12,9),(0,0),(12,-9),(12,9)]):
            h=add(.5,rise(metrics['air_rise']*(.38+.1*(i%3))))
            column(70+i,1.8 if i%2 else 2.5,h,x,y)
        box(76,(25,2.8,.55),(0,12,lowrise),conditional=more)
        box(77,(6,5,add(.3,lowrise)),(0,-13,mul(add(.3,lowrise),.5)))
    elif index==11:
        d=add(1,rise(metrics['wall_jump_rise']*.65))
        box(90,(14,14,add(d,2)),(0,0,neg(mul(d,.5))),hole=True)
        platform(80,0,0,14,14,neg(d))
        # A staircase of broad ledges, each well below observed single-jump rise.
        for i,(x,y) in enumerate([(-5,-5),(5,-5),(5,5),(-5,5)]):
            platform(81+i,x,y,4,4,neg(mul(d,(4-i)/5)))
        box(85,(20,2.7,.55),(0,0,.4),conditional=more)
        box(86,(1,15,add(d,4)),(-7.5,0,sub(2,mul(d,.5))))
    elif index==12:
        h=rise(metrics['jump_rise']*.95)
        platform(50,-9,0,14,14,h)
        platform(51,9,0,14,14,mul(h,2))
        # Upper hop is limited to single-jump rise and four metres laterally.
        platform(52,0,0,4,4,add(h,cap(h,metrics['jump_rise']*.55)))
        ramp(53,20,6,h,-8,-14)
        box(54,(24,3,.55),(0,12,h),conditional=more)
    elif index==13:
        h=add(3,rise(metrics['wall_air_rise']*.62))
        box(90,(18,22,add(pit,2)),(0,0,neg(mul(pit,.5))),hole=True)
        platform(12,0,0,18,22,neg(pit))
        platform(40,-15,0,10,20,.4)
        platform(42,15,0,10,20,.4)
        column(43,.9,h,10,0)
        column(41,1.8,.5,10,0,h)
        platform(44,-3,13,15,4,raised)
    elif index==14:
        clear=metrics['standing_height']+.5
        box(30,(20,12,.8),(0,0,clear+.4))
        for y in (-6.5,6.5):box(31,(20,1,clear+.8),(0,y,(clear+.8)/2))
        ramp(32,15,5,clear+.8,-2,12)
        platform(33,13,0,5,10,lowrise)

    g.output('Solid',g.join(solid))
    g.output('Voids',g.join(holes))
    g.arrange()
    g.tree['category']=CATEGORIES[index]
    return g.tree
