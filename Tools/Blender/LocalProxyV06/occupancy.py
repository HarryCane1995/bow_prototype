"""Native GN greedy occupancy. Conservative OBB SAT, no pairwise mesh booleans."""
import bpy,importlib.util
from pathlib import Path
sp=importlib.util.spec_from_file_location('v06_graph_base',Path(__file__).resolve().parent.parent/'LocalProxyV05/generator.py');v05=importlib.util.module_from_spec(sp);sp.loader.exec_module(v05)
CLEARANCE=.3
class Graph(v05.VarietyGraph):
    def eqi(self,a,b):
        n=self.node('FunctionNodeCompare',data_type='INT',operation='EQUAL');self.set(n,2,a);self.set(n,3,b);return n.outputs[0]
    def OR(self,a,b):return self.boolean('OR',a,b)
    def NOT(self,a):return self.boolean('NOT',a,False)
    def count(self,geo):
        n=self.node('GeometryNodeAttributeDomainSize',component='MESH');self.set(n,'Geometry',geo);return n.outputs['Point Count']
    def sample(self,geo,value,index,kind='FLOAT'):
        n=self.node('GeometryNodeSampleIndex',data_type=kind,domain='POINT');self.set(n,'Geometry',geo);self.set(n,'Value',value);self.set(n,'Index',index);return n.outputs[0]
    def sumfield(self,geo,field):
        n=self.node('GeometryNodeAttributeStatistic',data_type='FLOAT',domain='POINT');self.set(n,'Geometry',geo);self.set(n,'Attribute',field);return n.outputs['Sum']
    def overlap(self,center,axes,half,clearance):
        otheraxes=[self.attrv('occ_'+k) for k in ['x','y','z']];otherhalf=self.separate(self.vscale(self.attrv('occ_size'),.5))
        delta=self.vector('SUBTRACT',self.position(),center);separated=False
        # Six face normals give an oriented conservative test. Omitting the
        # nine edge-cross axes can only reject extra candidates, never accept
        # an intersection. Exact for shared-up/yaw boxes; cheaper for preview.
        # Independent QA uses all fifteen axes.
        tests=axes+otheraxes
        for axis in tests:
            length=self.vector('LENGTH',axis);unit=self.norm(axis)
            ra=0;rb=0
            for a,h in zip(axes,half):ra=self.add(ra,self.mul(self.absolute(self.vector('DOT_PRODUCT',unit,a)),h))
            for a,h in zip(otheraxes,otherhalf):rb=self.add(rb,self.mul(self.absolute(self.vector('DOT_PRODUCT',unit,a)),h))
            distance=self.absolute(self.vector('DOT_PRODUCT',delta,unit))
            sep=self.both(self.gt(length,1e-5),self.gt(distance,self.sub(self.add(self.add(ra,rb),clearance),.0002)))
            separated=self.OR(separated,sep)
        return self.NOT(separated)
    def solve(self,candidates,initial=None,label='Placement occupancy'):
        dims=self.separate(self.vscale(self.attrv('occ_size'),.5))
        aabb=self.plus(*[self.vscale(self.vector('ABSOLUTE',self.attrv('occ_'+k)),h) for k,h in zip(['x','y','z'],dims)])
        candidates=self.put(candidates,'occ_aabb',aabb,'FLOAT_VECTOR')
        sort=self.node('GeometryNodeSortElements',label+' priority',domain='POINT');self.set(sort,'Geometry',candidates);self.set(sort,'Sort Weight',self.attrf('placement_priority'));candidates=sort.outputs[0]
        ri=self.node('GeometryNodeRepeatInput',label+' input');ro=self.node('GeometryNodeRepeatOutput',label+' accepted')
        ro.repeat_items.clear();ro.repeat_items.new('GEOMETRY','Occupied');ro.repeat_items.new('GEOMETRY','Rejected');ri.pair_with_output(ro)
        self.set(ri,'Iterations',self.count(candidates))
        if initial is not None:self.set(ri,'Occupied',initial)
        index=ri.outputs['Iteration'];occupied=ri.outputs['Occupied']
        point=self.filter(candidates,self.eqi(self.node('GeometryNodeInputIndex').outputs[0],index))
        center=self.sample(candidates,self.position(),index,'FLOAT_VECTOR')
        axes=[self.sample(candidates,self.attrv('occ_'+k),index,'FLOAT_VECTOR') for k in ['x','y','z']]
        half=self.separate(self.vscale(self.sample(candidates,self.attrv('occ_size'),index,'FLOAT_VECTOR'),.5))
        role=self.sample(candidates,self.attri('primitive_role'),index,'INT');section=self.sample(candidates,self.attri('section_id'),index,'INT');patch=self.sample(candidates,self.attri('patch_id'),index,'INT')
        otherrole=self.attri('primitive_role');samesection=self.eqi(section,self.attri('section_id'));samepatch=self.eqi(patch,self.attri('patch_id'))
        floor=self.OR(self.eqi(role,0),self.OR(self.eqi(role,1),self.eqi(role,6)))
        otherfloor=self.OR(self.eqi(otherrole,0),self.OR(self.eqi(otherrole,1),self.eqi(otherrole,6)))
        grounding=self.OR(self.eqi(role,2),self.eqi(role,4));othergrounding=self.OR(self.eqi(otherrole,2),self.eqi(otherrole,4))
        flush=self.OR(self.both(floor,otherfloor),self.both(samepatch,self.OR(self.both(floor,othergrounding),self.both(otherfloor,grounding))))
        # Keepout already has generous margins. A neighboring runway may meet
        # its boundary; otherwise a flush tail would be rejected wholesale.
        flush=self.OR(flush,self.eqi(otherrole,90))
        clearance=self.switch(flush,CLEARANCE,0,'FLOAT')
        overlap=self.overlap(center,axes,half,clearance)
        # D keepout reserves the entire approach/crossing/catch. Only its own
        # mandatory surfaces/helper may enter it. Optional geometry may not.
        mandatory=self.OR(floor,self.eqi(role,9))
        ownreservation=self.both(self.eqi(otherrole,90),self.both(samesection,mandatory))
        overlap=self.both(overlap,self.NOT(ownreservation))
        # Broad phase restricts the expensive SAT field to nearby accepted
        # records, rather than evaluating it on the entire occupied domain.
        extent=self.sample(candidates,self.attrv('occ_aabb'),index,'FLOAT_VECTOR')
        broad_size=self.separate(self.plus(extent,self.attrv('occ_aabb'),(CLEARANCE,CLEARANCE,CLEARANCE)))
        delta=self.separate(self.vector('ABSOLUTE',self.vector('SUBTRACT',self.position(),center)))
        broad=True
        for distance,limit in zip(delta,broad_size):broad=self.both(broad,self.lt(distance,limit))
        nearby=self.filter(occupied,broad)
        blocked=self.gt(self.sumfield(nearby,overlap),.5)
        budget=self.sample(candidates,self.attri('primitive_budget'),index,'INT')
        used=self.sumfield(occupied,self.both(samesection,self.lt(otherrole,90)))
        blocked=self.OR(blocked,self.both(self.gt(role,1),self.both(self.lt(role,90),self.gt(used,self.sub(budget,.5)))))
        accepted=self.switch(blocked,point,None);rejected=self.switch(blocked,None,point)
        self.set(ro,'Occupied',self.join([occupied,accepted]));self.set(ro,'Rejected',self.join([ri.outputs['Rejected'],rejected]))
        final=self.put(ro.outputs['Occupied'],'overlap_rejected_count',self.count(ro.outputs['Rejected']),'INT')
        return final,ro.outputs['Rejected']
    def has_id(self,geo,positions,ids):
        atorigin=self.setpos(geo,self.attrv('section_start'))
        n=self.node('GeometryNodeSampleNearest',domain='POINT');self.set(n,'Geometry',atorigin);self.set(n,'Sample Position',positions)
        sid=self.sample(atorigin,self.attri('section_id'),n.outputs['Index'],'INT')
        return self.both(self.gt(self.count(geo),0),self.eqi(sid,ids))
