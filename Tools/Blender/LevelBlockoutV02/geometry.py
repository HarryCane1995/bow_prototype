"""Native GN construction helpers. Python is used only to author the node graph."""
import bpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'LevelBlockout'))
from nodes import Graph

ROLES=['FLOOR','WALL','PLATFORM','TRAVERSAL_CONNECTION','GRAPPLE_CANDIDATE','VOID_EDGE']

class SpatialGraph(Graph):
    def random(self,seed,identifier,stream,low=0,high=1,kind='FLOAT'):
        # Random Value is a field even for a constant ID. Primitive Size and
        # scalar group construction inputs need a SINGLE value, not a field.
        value=super().random(seed,identifier,stream,low,high,kind)
        if not hasattr(self,'sample_point'):
            p=self.node('GeometryNodeMeshLine','One point / scalar random evaluation',mode='OFFSET')
            self.set(p,'Count',1);self.sample_point=p.outputs['Mesh']
        n=self.node('GeometryNodeAttributeStatistic','Seeded scalar '+str(stream),data_type='FLOAT',domain='POINT')
        self.set(n,'Geometry',self.sample_point);self.set(n,'Attribute',value)
        return n.outputs['Mean']
    def add(self,a,b):return self.math('ADD',a,b)
    def sub(self,a,b):return self.math('SUBTRACT',a,b)
    def mul(self,a,b):return self.math('MULTIPLY',a,b)
    def div(self,a,b):return self.math('DIVIDE',a,b)
    def low(self,a,b):return self.math('MINIMUM',a,b)
    def high(self,a,b):return self.math('MAXIMUM',a,b)
    def neg(self,a):return self.mul(a,-1)
    def gt(self,a,b):return self.math('GREATER_THAN',a,b)
    def lt(self,a,b):return self.math('LESS_THAN',a,b)
    def eq(self,a,b):return self.math('COMPARE',a,b,.01)
    def output_value(self,name,kind,value):
        self.tree.interface.new_socket(name=name,in_out='OUTPUT',socket_type=kind)
        self.set(self.o,name,value)
    def tag(self,geo,role,zone=-1,band=0,part=0):
        for name,val in [('v02_role',role),('v02_zone',zone),('v02_band',band),('v02_part',part)]:geo=self.store(geo,name,val)
        return geo
    def cube(self,size,center,role,zone=-1,band=0,part=0,label='Structural solid'):
        n=self.node('GeometryNodeMeshCube',label);self.set(n,'Size',self.vec(*size))
        return self.tag(self.transform(n.outputs['Mesh'],self.vec(*center)),role,zone,band,part)
    def ramp(self,wedge,length,width,rise,center,angle,zone,band):
        n=self.object(wedge)
        geo=self.transform(n.outputs['Geometry'],self.vec(*center),self.vec(length,width,self.high(.02,rise)),self.vec(0,0,angle))
        return self.tag(geo,3,zone,band,20)
    def keep(self,geo,condition):return self.switch(condition,None,geo)
    def cylinder(self,radius,depth,center):
        n=self.node('GeometryNodeMeshCylinder');self.set(n,'Vertices',64);self.set(n,'Radius',radius);self.set(n,'Depth',depth)
        return self.transform(n.outputs['Mesh'],self.vec(*center))

def stairs(g,length,width,rise,base,zone,band):
    """18 genuinely stepped treads, rising at most ~0.75 m in the largest tested bay."""
    line=g.node('GeometryNodeMeshLine','Structural stair flight',mode='OFFSET')
    g.set(line,'Count',18);g.set(line,'Offset',(0,0,0))
    i=g.node('GeometryNodeInputIndex').outputs[0]
    step=g.div(length,18);h=g.div(rise,18)
    x=g.add(g.sub(base[0],g.mul(length,.5)),g.mul(g.add(i,.5),step))
    z=g.add(base[2],g.mul(g.mul(g.add(i,1),h),.5))
    pos=g.node('GeometryNodeSetPosition');g.set(pos,'Geometry',line.outputs['Mesh']);g.set(pos,'Position',g.vec(x,base[1],z))
    cube=g.node('GeometryNodeMeshCube');g.set(cube,'Size',(1,1,1))
    inst=g.node('GeometryNodeInstanceOnPoints');g.set(inst,'Points',pos.outputs[0]);g.set(inst,'Instance',cube.outputs[0])
    g.set(inst,'Scale',g.vec(step,width,g.mul(g.add(i,1),h)))
    real=g.node('GeometryNodeRealizeInstances');g.set(real,'Geometry',inst.outputs[0])
    return g.tag(real.outputs[0],3,zone,band,21)
