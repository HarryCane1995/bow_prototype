"""V05 native variety grammar above the unchanged V04 local-section foundation."""
import bpy
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v04local_graph',HERE.parent/'LocalProxyV04/generator.py')
v04=importlib.util.module_from_spec(spec);spec.loader.exec_module(v04)
NAME='GN_LevelProxyGenerator_v05'
CONTROLS=v04.CONTROLS[:-2]+[
    ('Length Variation','NodeSocketFloat',.82,0,1,'Run length rhythm: regular at 0, short/medium/long/very long at 1. Independent from gap length.'),
    ('Debug Span Colors','NodeSocketBool',False,None,None,'Blue basic / green air / orange near-limit / magenta grapple-required.'),
]+v04.CONTROLS[-2:]
FAMILIES=['LANDING','PLATFORM','WALL','RAMP','BRIDGE','SPEED','VERTICAL']


class VarietyGraph(v04.LocalGraph):
    def attrf(self,n):return self.attr(n,'FLOAT')
    def attri(self,n):return self.attr(n,'INT')
    def attrv(self,n):return self.attr(n,'FLOAT_VECTOR')
    def put(self,geo,name,value,kind='FLOAT'):return self.store(geo,name,value,kind,'POINT')
    def equal(self,a,b):return self.lt(self.absolute(self.sub(a,b)),.1)
    def choose(self,which,values,kind='FLOAT'):
        result=values[0]
        for i,v in enumerate(values[1:],1):result=self.switch(self.gt(which,i-.5),result,v,kind)
        return result
    def rnd(self,stream,low=0,high=1,kind='FLOAT'):
        identity=self.node('GeometryNodeInputNamedAttribute',data_type='INT');self.set(identity,'Name','variant_identity')
        local_id=self.switch(identity.outputs['Exists'],self.attri('section_id'),identity.outputs['Attribute'],'INT')
        return self.random(self.controls['Seed'],local_id,stream,low,high,kind)
    def hash_id(self,value,seed):
        n=self.node('FunctionNodeHashValue',data_type='INT');self.set(n,'Value',value);self.set(n,'Seed',seed);return n.outputs[0]
    def points_mesh(self,geo):
        n=self.node('GeometryNodePointsToVertices');self.set(n,'Points',geo);return n.outputs[0]
    def filter(self,geo,selection):
        n=self.node('GeometryNodeSeparateGeometry',domain='POINT');self.set(n,'Geometry',geo);self.set(n,'Selection',selection);return n.outputs['Selection']
    def extent(self,which,values):return self.choose(which,values)
    def inside(self,geo,point,margin=.5):
        prox=self.node('GeometryNodeProximity');self.set(prox,'Geometry',geo);self.set(prox,'Sample Position',point)
        normal=self.node('GeometryNodeInputNormal').outputs['Normal']
        near=self.node('GeometryNodeSampleNearestSurface',data_type='FLOAT_VECTOR');self.set(near,'Mesh',geo);self.set(near,'Value',normal);self.set(near,'Sample Position',point)
        signed=self.vector('DOT_PRODUCT',self.vector('SUBTRACT',point,prox.outputs['Position']),near.outputs['Value'])
        return self.both(prox.outputs['Is Valid'],self.lt(signed,self.mul(margin,-1)))
    def stock(self,points,size,offset=(0,0,0),selection=True,role=0):
        geo=self.instance(points,self.cube,size,offset,selection,0,role)
        geo=self.store(geo,'variant_id',-1,'INT','FACE')
        return self.store(geo,'variant_family',-1,'INT','FACE')
    def variants(self,points,family,available,offset=(0,0,0),selection=True,yaw=0,stream=200):
        rows=self.library[family];dims=[max(r['dimensions'][i] for r in rows) for i in range(3)]
        cap=1.35 if family!='RAMP' else 1.0
        fit=self.lo(cap,self.lo(self.div(available[0],dims[0]),self.lo(self.div(available[1],dims[1]),self.div(available[2],dims[2]))))
        okay=self.both(selection,self.gt(fit,.6499))
        points=self.put(points,'variant_uniform_scale',fit)
        choice=self.rnd(stream,0,len(rows)-1,'INT')
        points=self.put(points,'variant_choice',choice,'INT')
        points=self.setpos(points,offset=offset)
        pack=self.node('GeometryNodeGeometryToInstance',family+' library')
        for row in rows:
            info=self.node('GeometryNodeObjectInfo',row['name'],transform_space='ORIGINAL');self.set(info,'Object',bpy.data.objects[row['object']]);self.set(info,'As Instance',False);self.set(pack,'Geometry',info.outputs['Geometry'])
        inst=self.node('GeometryNodeInstanceOnPoints',family+' seeded archetype')
        c=self.math('COSINE',yaw);s=self.math('SINE',yaw)
        f=self.plus(self.vscale(self.named('forward'),c),self.vscale(self.named('side'),s))
        sx=fit
        if family=='RAMP':sx=self.mul(fit,self.div(1,self.math('TANGENT',self.mul(self.controls['Ramp Steepness'],math.pi/180))))
        for k,v in [('Points',points),('Selection',okay),('Instance',pack.outputs[0]),('Pick Instance',True),('Instance Index',self.attri('variant_choice')),('Rotation',self.rotation(f,self.named('up'))),('Scale',self.vec(sx,fit,fit))]:self.set(inst,k,v)
        real=self.node('GeometryNodeRealizeInstances');self.set(real,'Geometry',inst.outputs[0])
        return self.store(real.outputs[0],'surface_role',FAMILIES.index(family),'INT','FACE')


def span_bands(metrics):
    return {'BASIC_JUMP':[metrics['running_jump']*.45,metrics['running_jump']*.70],
            'AIR_JUMP':[metrics['air_jump']*.58,metrics['air_jump']*.78],
            'NEAR_LIMIT':[metrics['air_jump']*.84,metrics['air_jump']*.94],
            'GRAPPLE_REQUIRED':[metrics['air_jump']*1.10,metrics['air_jump']*1.45]}


def build(metrics,manifest):
    g=VarietyGraph(NAME);g.library={f:[r for r in manifest if r['family']==f] for f in FAMILIES}
    proxy=g.input('Proxy','NodeSocketObject');cutter=g.input('Cutter','NodeSocketObject')
    q={name:g.input(name,kind,value,low,high,desc) for name,kind,value,low,high,desc in CONTROLS};g.controls=q
    mode=g.input('Output Mode','NodeSocketInt',0,0,6,'Internal: 0 surfaces / 1 helpers / 2 span diagnostic points / 3 envelope / 4 raw / 5 helper points / 6 rhythm points.')
    foundation=g.node('GeometryNodeGroup','V04 local sections preserved',node_tree=bpy.data.node_groups['GN_V05_LocalSections_FromV04'])
    g.set(foundation,'Proxy',proxy)
    for name in q:
        if name in foundation.inputs:g.set(foundation,name,q[name])
    envelope=foundation.outputs['Envelope'];valid=foundation.outputs['Valid Volume'];hp=foundation.outputs['Horizontal Patches'];vp=foundation.outputs['Vertical Levels']
    cutterinfo=g.node('GeometryNodeObjectInfo','Secondary cutter',transform_space='RELATIVE');g.set(cutterinfo,'Object',cutter);cutgeo=cutterinfo.outputs['Geometry']
    g.cube=g.node('GeometryNodeMeshCube','Neutral metric connector').outputs['Mesh']
    g.set(g.cube.node,'Size',(1,1,1))
    # Keep parent patch identity before duplicating. Sequence IDs are derived
    # from this spatial identity plus the local ordinal, never global point index.
    hp=g.put(hp,'patch_id',g.spatial_id(g.position()),'INT')
    count=g.add(g.math('CEIL',g.div(g.named('length'),10)),1)
    hp=g.duplicate(hp,count)
    hashnode=g.node('FunctionNodeHashValue','Stable section identity',data_type='INT');g.set(hashnode,'Value',g.attri('patch_id'));g.set(hashnode,'Seed',g.attri('lp_duplicate'))
    hp=g.put(hp,'section_id',hashnode.outputs[0],'INT')
    hp=g.put(hp,'local_seed',g.hash_id(g.attri('section_id'),q['Seed']),'INT')
    hp=g.put(hp,'local_forward',g.named('forward'),'FLOAT_VECTOR')
    # 0.55 / 1.2 / 2.4 / 4.4 seconds at current run speed: meaningful rhythm.
    rhythmclass=g.switch(g.gt(g.rnd(101),.38),0,1,'INT')
    rhythmclass=g.switch(g.gt(g.rnd(101),.70),rhythmclass,2,'INT')
    rhythmclass=g.switch(g.gt(g.rnd(101),.91),rhythmclass,3,'INT')
    lengths=[metrics['run_speed']*t for t in [.55,1.2,2.4,4.4]]
    desired=g.mul(g.choose(rhythmclass,lengths),g.rnd(102,.90,1.10))
    run=g.add(metrics['run_speed']*1.2,g.mul(q['Length Variation'],g.sub(desired,metrics['run_speed']*1.2)))
    pick=g.rnd(103);spanclass=g.switch(g.gt(pick,.52),1,2,'INT')
    spanclass=g.switch(g.gt(pick,.84),spanclass,3,'INT');spanclass=g.switch(g.gt(pick,.92),spanclass,4,'INT')
    # Small authored patches gracefully use a run or basic span; class D needs
    # a real runway, catch, headroom and width before its marker guard is tested.
    spanclass=g.switch(g.lt(g.named('length'),45),spanclass,g.lo(spanclass,2),'INT')
    spanclass=g.switch(g.lt(g.named('length'),30),spanclass,1,'INT')
    # The verified jump reach is horizontal, at the measured launch/landing
    # heights. Inclined patches keep continuous speed/descent fill instead of
    # presenting an uphill diagonal distance as a validated horizontal jump.
    forward_z=g.separate(g.named('forward'))[2]
    spanclass=g.switch(g.gt(g.absolute(forward_z),.02),spanclass,0,'INT')
    bands=span_bands(metrics);lo=[0]+[v[0] for v in bands.values()];hi=[0]+[v[1] for v in bands.values()]
    gap_t=g.hi(0,g.lo(1,g.add(g.rnd(104),g.mul(g.sub(q['Traversal Difficulty'],.4),.3))))
    gap=g.add(g.choose(spanclass,lo),g.mul(gap_t,g.sub(g.choose(spanclass,hi),g.choose(spanclass,lo))))
    catch=g.choose(spanclass,[0,5.5,7.5,10,12])
    # Cap the initial run to allow the selected span in a sufficiently long
    # patch. Extremely short tails have no forced oversized traversal gap.
    run=g.lo(run,g.hi(7,g.sub(g.named('length'),g.add(gap,catch))))
    hp=g.put(hp,'desired_run',run);hp=g.put(hp,'desired_gap',gap);hp=g.put(hp,'desired_class',spanclass,'INT');hp=g.put(hp,'catch_length',catch)
    cost=g.add(g.attrf('desired_run'),g.add(g.attrf('desired_gap'),g.attrf('catch_length')))
    acc=g.node('GeometryNodeAccumulateField','Irregular sequence prefix sums',data_type='FLOAT',domain='POINT')
    g.set(acc,'Value',cost);g.set(acc,'Group ID',g.attri('patch_id'))
    hp=g.put(hp,'sequence_start',acc.outputs['Trailing'])
    remain=g.sub(g.named('length'),g.attrf('sequence_start'))
    hp=g.filter(hp,g.gt(remain,1))
    remaining=g.sub(g.named('length'),g.attrf('sequence_start'))
    complete=g.gt(remaining,g.sub(cost,.001))
    hp=g.put(hp,'complete_span',complete,'BOOLEAN')
    hp=g.put(hp,'section_length',g.switch(complete,remaining,g.attrf('desired_run'),'FLOAT'))
    hp=g.put(hp,'span_class',g.switch(complete,0,g.attri('desired_class'),'INT'),'INT')
    hp=g.put(hp,'span_distance',g.switch(complete,0,g.attrf('desired_gap'),'FLOAT'))
    # Point becomes beginning of its own authored local sequence.
    shift=g.sub(g.attrf('sequence_start'),g.mul(g.named('length'),.5))
    hp=g.setpos(hp,offset=g.vscale(g.named('forward'),shift))
    hp=g.put(hp,'section_start',g.position(),'FLOAT_VECTOR')
    # Required marker and guaranteed catch clearance, checked before emitting D.
    dist=g.attrf('span_distance');run=g.attrf('section_length')
    approach=g.plus(g.position(),g.offset(g.sub(run,.8),0,.55))
    anchorheight=g.lo(8,g.sub(g.named('height'),1.1))
    anchor=g.plus(g.position(),g.offset(g.add(run,g.mul(dist,.57)),0,anchorheight))
    catchstart=g.add(run,dist);catchmid=g.add(catchstart,g.mul(g.attrf('catch_length'),.5))
    clear=g.both(g.gt(g.named('width'),7.5),g.gt(g.named('height'),5))
    clear=g.both(clear,g.inside(envelope,anchor,.7))
    clear=g.both(clear,g.lt(g.vector('DISTANCE',approach,anchor),metrics['grapple_range']*.92))
    # Four catch corners and two approach corners protect useful surface area.
    for x,y in [(g.add(catchstart,1),-3),(g.add(catchstart,1),3),(g.add(catchstart,10),-3),(g.add(catchstart,10),3),(g.add(catchstart,5),0),(g.sub(run,1),-2),(g.sub(run,1),2),(g.sub(run,2),0)]:
        p=g.plus(g.position(),g.offset(x,y,.7));clear=g.both(clear,g.inside(envelope,p,.1))
        clear=g.both(clear,g.switch(q['Use Cutter'],True,g.boolean('NOT',g.inside(cutgeo,p,-.5),False),'BOOLEAN'))
    clear=g.both(clear,g.switch(q['Use Cutter'],True,g.boolean('NOT',g.inside(cutgeo,anchor,-.7),False),'BOOLEAN'))
    required=g.equal(g.attri('span_class'),4)
    fallback=g.both(required,g.boolean('NOT',clear,False))
    hp=g.put(hp,'required_fallback',fallback,'BOOLEAN')
    fallback=g.attr('required_fallback','BOOLEAN')
    actualgap=g.switch(fallback,dist,g.rnd(106,bands['BASIC_JUMP'][0],bands['BASIC_JUMP'][1]),'FLOAT')
    hp=g.put(hp,'catch_length',g.add(g.attrf('catch_length'),g.sub(dist,actualgap)))
    hp=g.put(hp,'span_distance',actualgap)
    hp=g.put(hp,'span_class',g.switch(fallback,g.attri('span_class'),1,'INT'),'INT')
    hp=g.put(hp,'grapple_required',g.equal(g.attri('span_class'),4),'BOOLEAN')
    hp=g.put(hp,'required_traversal',g.attri('span_class'),'INT')
    hp=g.put(hp,'rhythm_class',rhythmclass,'INT')
    hp=g.put(hp,'lp_center',g.position(),'FLOAT_VECTOR')
    diag=g.points_mesh(hp)
    # Runway shape units are repeated at controlled scale. Long speed portions
    # retain a continuous neutral spine, instead of a periodic row of gaps.
    units=g.hi(1,g.math('CEIL',g.div(g.attrf('section_length'),13.5)))
    tiles=g.put(hp,'unit_count',units);tiles=g.put(tiles,'unit_length',g.div(g.attrf('section_length'),units));tiles=g.duplicate(tiles,g.attrf('unit_count'))
    along=g.mul(g.add(g.attri('lp_duplicate'),.5),g.attrf('unit_length'))
    tiles=g.setpos(tiles,offset=g.offset(along,0,.08))
    tiles=g.put(tiles,'variant_identity',g.hash_id(g.attri('section_id'),g.attri('lp_duplicate')),'INT')
    width=g.hi(1,g.sub(g.named('width'),.7));L=g.attrf('section_length')
    items=[g.variants(tiles,'LANDING',(g.attrf('unit_length'),width,1),stream=211)]
    items.append(g.stock(hp,g.vec(L,g.lo(4.2,width),.45),g.offset(g.mul(L,.5),0,.265),role=0))
    # Approach lip and receiving catch are neutral metric surfaces; library
    # ornaments cannot silently shorten or lengthen the diagnosed gap.
    hasgap=g.gt(g.attri('span_class'),0)
    items.append(g.stock(hp,g.vec(g.lo(2.5,L),g.lo(width,6),.5),g.offset(g.sub(L,g.mul(g.lo(2.5,L),.5)),0,.25),hasgap,0))
    catchlen=g.attrf('catch_length');catchx=g.add(g.add(L,g.attrf('span_distance')),g.mul(catchlen,.5))
    catchwidth=g.lo(width,g.choose(g.attri('span_class'),[4,5.5,6.5,8,8]))
    items.append(g.stock(hp,g.vec(catchlen,catchwidth,.5),g.offset(catchx,0,.25),hasgap,0))
    catches=g.setpos(hp,offset=g.offset(catchx,0,.02))
    items.append(g.variants(catches,'PLATFORM',(catchlen,catchwidth,1.1),selection=hasgap,stream=221))
    # Wall compositions preserve authored forward but include actual kinks,
    # converging pairs, broken strips and unequal wall heights in the library.
    wallsel=g.lt(g.rnd(230),g.mul(g.mul(q['Wallrun Bias'],g.sub(1,g.mul(q['Openness'],.3))),g.add(.5,g.mul(q['Density'],.5))))
    side=g.switch(g.lt(g.rnd(231),.5),-1,1,'FLOAT')
    yaw=g.mul(g.mul(q['Orientation Randomness'],math.pi/180),g.rnd(232,-1,1))
    wallpts=g.setpos(hp,offset=g.offset(g.mul(L,.47),g.mul(side,g.lo(1,g.mul(width,.08))),.55))
    items.append(g.variants(wallpts,'WALL',(g.hi(1,g.sub(L,3)),g.mul(width,.83),g.hi(1,g.sub(g.named('height'),1.5))),selection=wallsel,yaw=yaw,stream=233))
    rampsel=g.both(g.lt(g.rnd(240),g.mul(q['Ramp Presence'],g.add(.35,g.mul(q['Density'],.65)))),g.gt(L,10))
    ramppts=g.setpos(hp,offset=g.offset(g.mul(L,.42),g.mul(side,g.lo(1.6,g.mul(width,.15))),.52))
    items.append(g.variants(ramppts,'RAMP',(g.lo(12,g.mul(L,.65)),g.mul(width,.74),g.hi(1,g.sub(g.named('height'),2.1))),selection=rampsel,stream=241))
    bridgepts=g.setpos(hp,offset=g.offset(g.mul(L,.5),0,g.lo(2.8,g.mul(g.named('height'),.19))))
    items.append(g.variants(bridgepts,'BRIDGE',(g.mul(L,.8),g.mul(width,.87),g.hi(1,g.sub(g.named('height'),3))),selection=g.both(g.gt(L,17),g.lt(g.rnd(250),g.mul(q['Route Complexity'],.55))),yaw=g.mul(yaw,.45),stream=251))
    speedpts=g.setpos(hp,offset=g.offset(g.mul(L,.6),0,.02))
    items.append(g.variants(speedpts,'SPEED',(g.mul(L,.75),width,g.hi(1,g.sub(g.named('height'),2))),selection=g.both(g.gt(L,25),g.lt(g.rnd(260),g.add(.3,q['Slide Bias']))),stream=261))
    # True upper/shaft geometry uses the preserved V04 lattice. Space complete
    # structural motifs every third level, not one tall motif on every pad.
    vp=g.put(vp,'section_id',g.spatial_id(g.position()),'INT');vp=g.put(vp,'local_seed',g.hash_id(g.attri('section_id'),q['Seed']),'INT');vp=g.put(vp,'local_forward',g.named('forward'),'FLOAT_VECTOR')
    level=g.attri('lp_duplicate');verticalsel=g.both(g.lt(g.math('MODULO',level,3),.1),g.gt(g.named('height'),13))
    verticalsel=g.both(verticalsel,g.lt(g.rnd(270),g.add(.4,g.mul(q['Verticality'],.6))))
    vp=g.filter(vp,verticalsel)
    items.append(g.variants(vp,'VERTICAL',(g.lo(13,g.named('beat')),g.sub(g.named('width'),.8),12),stream=271))
    # A few low isolated pads in ordinary-height sections still vary by topology.
    padsel=g.both(g.lt(g.rnd(280),g.mul(q['Verticality'],q['Route Complexity'])),g.gt(L,16))
    padpts=g.setpos(hp,offset=g.offset(g.mul(L,.22),g.mul(side,g.lo(g.mul(width,.25),3)),g.lo(g.mul(g.named('height'),.35),4)))
    items.append(g.variants(padpts,'PLATFORM',(g.lo(12,g.mul(L,.5)),g.mul(width,.78),2),selection=padsel,yaw=g.mul(yaw,1.25),stream=281))
    raw=g.join(items)
    # Both required and optional candidates use the actual span approach/catch.
    candidatepos=g.plus(g.position(),g.offset(g.add(g.attrf('section_length'),g.mul(g.attrf('span_distance'),.57)),0,g.lo(8,g.sub(g.named('height'),1.1))))
    required=g.attr('grapple_required','BOOLEAN')
    opt=g.both(g.gt(g.attrf('span_distance'),0),g.lt(g.rnd(301),q['Grapple Bias']))
    selection=g.boolean('OR',required,opt)
    hphelp=g.put(hp,'source_span',g.attri('section_id'),'INT')
    hphelp=g.put(hphelp,'anchor_distance_from_approach',g.vector('DISTANCE',approach,candidatepos))
    hphelp=g.put(hphelp,'anchor_height',g.lo(8,g.sub(g.named('height'),1.1)))
    landpoint=g.plus(g.position(),g.offset(g.add(g.attrf('section_length'),g.attrf('span_distance')),0,.5))
    hphelp=g.put(hphelp,'landing_distance',g.vector('DISTANCE',candidatepos,landpoint))
    hphelp=g.setpos(hphelp,candidatepos)
    hphelp=g.filter(hphelp,g.both(selection,g.inside(envelope,g.position(),.65)))
    # Optional upper catches are separate from mandatory span compensation.
    vh=g.put(vp,'grapple_required',False,'BOOLEAN');vh=g.put(vh,'source_span',g.attri('section_id'),'INT');vh=g.put(vh,'anchor_height',5.4)
    vh=g.setpos(vh,offset=g.offset(0,0,5.4));vh=g.filter(vh,g.both(g.lt(g.rnd(302),q['Grapple Bias']),g.inside(envelope,g.position(),.6)))
    helperpoints=g.join([hphelp,vh])
    sphere=g.node('GeometryNodeMeshIcoSphere');g.set(sphere,'Radius',1);g.set(sphere,'Subdivisions',1)
    size=g.switch(g.attr('grapple_required','BOOLEAN'),.24,.52,'FLOAT')
    inst=g.node('GeometryNodeInstanceOnPoints','Optional / required grapple candidates');g.set(inst,'Points',helperpoints);g.set(inst,'Instance',sphere.outputs[0]);g.set(inst,'Scale',g.vec(size,size,size))
    real=g.node('GeometryNodeRealizeInstances');g.set(real,'Geometry',inst.outputs[0]);helpers=real.outputs[0]
    optmat=v04.material('V05_OPTIONAL_GRAPPLE',(.93,.68,.16));reqmat=v04.material('V05_REQUIRED_GRAPPLE',(1,.12,.45))
    mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',helpers);g.set(mat,'Material',optmat)
    mat2=g.node('GeometryNodeSetMaterial');g.set(mat2,'Geometry',mat.outputs[0]);g.set(mat2,'Selection',g.attr('grapple_required','BOOLEAN'));g.set(mat2,'Material',reqmat);helpers=mat2.outputs[0]
    neutral=v04.material('V05_NEUTRAL_BLOCKOUT',(.48,.53,.56));mat=g.node('GeometryNodeSetMaterial');g.set(mat,'Geometry',raw);g.set(mat,'Material',neutral);raw=mat.outputs[0]
    debug=raw
    for cls,color in [(1,(.24,.49,.85)),(2,(.22,.72,.48)),(3,(.95,.52,.13)),(4,(.96,.12,.46))]:
        n=g.node('GeometryNodeSetMaterial');g.set(n,'Geometry',debug);g.set(n,'Selection',g.equal(g.attri('span_class'),cls));g.set(n,'Material',v04.material('V05_SPAN_'+str(cls),color));debug=n.outputs[0]
    raw=g.switch(q['Debug Span Colors'],raw,debug)
    chosen=g.switch(g.equal(mode,1),raw,helpers)
    fast=g.mesh_boolean('INTERSECT',chosen,envelope,'MANIFOLD');exact=g.mesh_boolean('INTERSECT',chosen,envelope,'EXACT')
    clipped=g.switch(g.gt(q['Preview Quality'],.5),fast,exact)
    size=g.node('GeometryNodeAttributeDomainSize',component='MESH');g.set(size,'Geometry',chosen);clipped=g.switch(g.gt(size.outputs['Face Count'],0),None,clipped)
    sub=g.mesh_boolean('DIFFERENCE',clipped,cutgeo,'EXACT');clipped=g.switch(q['Use Cutter'],clipped,sub);clipped=g.switch(valid,None,clipped)
    # Both point clouds and mesh points become one inspectable mesh for QA.
    helperdiag=g.join([g.points_mesh(hphelp),vh])
    result=clipped
    for value,geo in [(2,diag),(3,envelope),(4,raw),(5,helperdiag),(6,diag)]:result=g.switch(g.equal(mode,value),result,geo)
    g.output('Geometry',result);g.tree['span_bands_m']=json.dumps(bands);g.tree['movement_snapshot']='2026-09-20; source hashes reverified for V05';g.tree['authoring_runtime']='Native Geometry Nodes; no handlers or source rewrite';g.tree['library_count']=len(manifest)
    g.arrange();return g.tree
