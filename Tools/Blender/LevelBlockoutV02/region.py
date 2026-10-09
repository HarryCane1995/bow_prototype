"""Gameplay surfaces inside the existing V02 spatial bands.

This is one shared construction grammar, not a palette of obstacle prefabs.
"""
import math
from geometry import SpatialGraph,stairs

def build_region(metrics,wedge):
    g=SpatialGraph('V02_SpatialBay')
    seed=g.input('Seed','NodeSocketInt',17);zone=g.input('Zone','NodeSocketInt',0)
    width=g.input('Width',value=70);length=g.input('Length',value=60)
    cx=g.input('Center X',value=0);cy=g.input('Center Y',value=0)
    bottom=g.input('Bottom',value=-8);top=g.input('Top',value=42)
    vertical=g.input('Verticality',value=.8);density=g.input('Density',value=.7)
    openness=g.input('Openness',value=.3);routes=g.input('Route Complexity',value=.65)
    difficulty=g.input('Traversal Difficulty',value=.45);grapple=g.input('Grapple Presence',value=.6)
    rise=g.input('Band Rise',value=7);major=g.input('Major','NodeSocketBool',False)
    side=g.input('Outer Side',value=-1)
    rnd=lambda stream,lo=0,hi=1:g.random(seed,zone,stream,lo,hi)
    factor=g.add(.52,g.mul(.38,difficulty))
    # Most bays use comfortable/challenging dimensions. Only a sparse seeded subset
    # can use the top difficulty band.
    factor=g.low(factor,g.switch(g.lt(rnd(206),.18),.82,.9,'FLOAT'))
    below=g.high(0,g.sub(g.neg(bottom),.8))
    lowered=g.boolean('AND',g.gt(vertical,.3),g.lt(rnd(201),.38))
    ground=g.switch(lowered,0,g.neg(g.mul(g.low(below,metrics['air_rise']*1.3),vertical)),'FLOAT')
    max_bands=g.low(6,g.high(0,g.math('FLOOR',g.div(g.sub(top,2.5),rise))))
    importance=g.switch(major,rnd(202,.48,.94),1,'FLOAT')
    layers=g.math('FLOOR',g.mul(max_bands,g.mul(vertical,g.mul(importance,g.add(.8,g.mul(density,.3))))))
    layers=g.low(max_bands,layers)
    # The major bay retains an upper route at medium verticality.
    layers=g.high(layers,g.switch(g.boolean('AND',major,g.gt(vertical,.3)),0,1,'FLOAT'))
    layers=g.low(max_bands,layers)
    inner_w=g.high(6,g.sub(width,6));inner_l=g.high(10,g.sub(length,6))
    xmin=g.sub(cx,g.mul(inner_w,.5));xmax=g.add(cx,g.mul(inner_w,.5))
    front=g.sub(cy,g.mul(inner_l,.5));back=g.add(cy,g.mul(inner_l,.5))
    floor=g.cube((inner_w,inner_l,.65),(cx,cy,g.sub(ground,.325)),0,zone,0,1,'Large lower floor region')
    solids=[floor];decks=[]
    shaft_w=g.low(g.mul(inner_w,.36),g.mul(g.sub(g.switch(g.lt(rnd(208),.5),metrics['running_jump'],metrics['air_jump'],'FLOAT'),metrics['diameter']),factor))
    shaft_l=g.low(g.mul(inner_l,.3),g.mul(metrics['slide_jump']-metrics['diameter'],factor))
    shaft_x=g.add(cx,g.mul(side,g.mul(inner_w,.08)))
    shaft_y=g.add(cy,g.mul(inner_l,.06))
    shaft=g.cube((shaft_w,shaft_l,g.add(g.sub(top,bottom),5)),(shaft_x,shaft_y,g.mul(g.add(top,bottom),.5)),5,zone,0,50,'Continuous open vertical void')
    pit_bottom=g.cube((shaft_w,shaft_l,.5),(shaft_x,shaft_y,g.add(bottom,.3)),0,zone,-1,51,'Shaft recovery floor')
    active_void=g.boolean('AND',g.gt(vertical,.23),g.gt(g.sub(ground,bottom),1))
    # Plates share metric bands, not a structural frame or mandatory access system.
    anchors=[]
    for band in range(1,7):
        z=g.mul(rise,band);active=g.gt(layers,band-.5)
        dw=g.high(8,g.mul(inner_w,g.mul(rnd(230+band,.50,.82),g.sub(1,g.mul(openness,.15)))))
        dl=g.high(8,g.mul(inner_l,g.mul(rnd(250+band,.45,.80),g.sub(1,g.mul(openness,.15)))))
        # Bounded shifts open vertical sightlines while keeping adjacent bands close.
        shift=g.mul(metrics['air_jump']-metrics['diameter'],g.mul(factor,.22))
        ax=g.add(cx,g.mul(rnd(270+band,-1,1),g.low(shift,g.mul(g.sub(inner_w,dw),.5))))
        ay=g.add(cy,g.mul(rnd(280+band,-1,1),g.low(shift,g.mul(g.sub(inner_l,dl),.5))))
        fy=g.sub(ay,g.mul(dl,.5))
        plate=g.cube((dw,dl,.7),(ax,ay,g.sub(z,.35)),2,zone,band,10,'Large usable elevated plate')
        deckparts=[plate]
        # An occasional lower access flight is one optional route. Higher plates
        # deliberately receive no automatic stairs, landings, columns or bases.
        if band==1:
            previous=ground;dr=g.sub(z,previous)
            run=g.low(g.high(8,g.sub(dw,8)),g.high(metrics['running_jump']*1.85,g.mul(dr,3.1)))
            ramp_y=g.sub(fy,2.5)
            ramp=g.ramp(wedge,run,4.8,dr,(ax,ramp_y,previous),0,zone,band)
            stair=stairs(g,run,4.8,dr,(ax,ramp_y,previous),zone,band)
            ramp=g.switch(g.boolean('AND',g.lt(rnd(211),.4),g.gt(routes,.45)),ramp,stair)
            flight=[ramp]
            for sign in (-1,1):
                x=g.add(ax,g.mul(run,sign*.5))
                height=z if sign>0 else previous
                flight.append(g.cube((6,8,.7),(x,fy,g.sub(height,.35)),3,zone,band,22 if sign>0 else 23,'Optional route landing'))
            optional=g.boolean('AND',g.lt(rnd(213),g.add(.10,g.mul(routes,.38))),g.lt(g.div(dr,run),.55))
            deckparts.append(g.keep(g.join(flight),optional))
        decks.append(g.keep(g.join(deckparts),active))
        anchors.append(g.vec(ax,g.add(fy,g.mul(dl,.28)),z))
    solids+=decks
    maxz=g.mul(layers,rise)
    # Isolated, sometimes suspended wall strips; their extent follows movement
    # distances instead of filling the facade from ground to the highest plate.
    wall_band=g.math('FLOOR',g.mul(layers,rnd(212,0,.78)))
    wall_bottom=g.add(g.mul(wall_band,rise),.8)
    wall_h=g.low(g.high(.5,g.sub(top,wall_bottom)),g.mul(metrics['wall_jump_rise'],g.add(.75,g.mul(vertical,.45))))
    wx=g.add(cx,g.mul(side,g.mul(inner_w,.24)))
    wall_length=g.low(g.mul(inner_l,.62),g.mul(metrics['wallrun'],factor))
    wall_start=g.sub(cy,g.mul(wall_length,.5))
    solids.append(g.cube((.9,wall_length,wall_h),(wx,cy,g.add(wall_bottom,g.mul(wall_h,.5))),1,zone,wall_band,31,'Isolated elevated wallrun plane'))
    back_w=g.low(g.mul(inner_w,rnd(214,.30,.50)),g.mul(metrics['wallrun'],factor))
    back_bottom=g.add(g.mul(g.high(0,g.sub(wall_band,1)),rise),1.2)
    solids.append(g.cube((back_w,.85,g.mul(wall_h,.65)),(cx,g.add(cy,g.mul(inner_l,.29)),g.add(back_bottom,g.mul(wall_h,.325))),1,zone,wall_band,32,'Suspended perpendicular traversal wall'))
    # Explicit movement surfaces, still the same wall/plate primitives.
    wr_len=g.low(g.sub(inner_w,7),g.mul(metrics['wallrun'],factor))
    solids.append(g.cube((wr_len,.75,3.8),(cx,g.add(front,10.5),g.add(ground,1.9)),1,zone,0,40,'Wallrun surface beside circulation lane'))
    pair_width=g.mul(metrics['wall_jump_lateral'],factor)
    pair_h=g.low(g.high(4.0,maxz),g.mul(metrics['wall_jump_rise'],factor))
    pair=[]
    # The pair occupies an edge of the shaft and has a landing at one band height.
    for sign in (-1,1):
        pair.append(g.cube((.7,g.low(12,g.mul(inner_l,.24)),pair_h),(g.add(shaft_x,g.mul(g.add(pair_width,.7),sign*.5)),shaft_y,g.add(ground,g.mul(pair_h,.5))),1,zone,0,41+int(sign>0),'Wall-jump pair'))
    pair.append(g.cube((g.add(pair_width,2.1),13,.65),(shaft_x,shaft_y,g.sub(ground,.325)),2,zone,0,43,'Wall-jump approach landing'))
    pair_landing_z=g.add(ground,g.low(rise,g.mul(metrics['wall_jump_rise'],factor)))
    pair.append(g.cube((g.add(pair_width,2.1),4,.7),(shaft_x,g.add(shaft_y,7),g.sub(pair_landing_z,.35)),2,zone,1,44,'Wall-jump upper landing'))
    pair_geometry=g.keep(g.join(pair),g.boolean('AND',g.gt(layers,.5),g.lt(rnd(219),g.add(.2,g.mul(routes,.6)))))
    # A playable high plate edge, not a decorative pin or prop, marks a grapple candidate.
    candidate_z=g.low(g.sub(top,1),g.add(maxz,rise))
    candidate_x=g.add(wx,g.mul(side,-4.2));candidate_y=g.add(wall_start,5)
    candidate=g.cube((8,10,.75),(candidate_x,candidate_y,g.sub(candidate_z,.375)),4,zone,g.add(layers,1),60,'High grapple landing surface')
    solids.append(g.keep(candidate,g.boolean('AND',g.gt(layers,1.5),g.lt(rnd(220),g.mul(grapple,.65)))))
    # Local slide access is a gameplay obstacle, never a global ceiling.
    lowgeo=g.cube((7,8,.7),(g.add(wx,g.mul(side,-4)),g.sub(back,6),g.add(ground,1.6)),3,zone,0,61,'Local 1.25m slide passage')
    solids.append(g.keep(lowgeo,g.boolean('AND',g.lt(rnd(221),.25),g.gt(density,.5))))
    joined=g.join(solids)
    cut=g.mesh_boolean('DIFFERENCE',joined,shaft)
    joined=g.switch(active_void,joined,g.join([cut,pit_bottom]))
    # Functional shaft access is added after the void subtraction.
    # Otherwise the boolean would erase the very walls intended to traverse it.
    joined=g.join([joined,pair_geometry])
    joined=g.store(joined,'v02_band_rise',rise,'FLOAT')
    g.output('Geometry',joined)
    g.output_value('Layers','NodeSocketInt',layers)
    g.output_value('Ground','NodeSocketFloat',ground)
    for band,a in enumerate(anchors,1):g.output_value('Anchor '+str(band),'NodeSocketVector',a)
    g.arrange();return g.tree
