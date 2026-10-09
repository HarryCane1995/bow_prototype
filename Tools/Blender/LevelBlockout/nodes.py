"""Small construction helpers. All resulting evaluation runs in native Geometry Nodes."""
import bpy


class Graph:
    def __init__(self, name):
        self.tree = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        self.tree.is_modifier = True
        self.i = self.node('NodeGroupInput', 'Controls')
        self.o = self.node('NodeGroupOutput', 'Result')

    def node(self, kind, label='', **props):
        n = self.tree.nodes.new(kind)
        if label: n.name = n.label = label
        for k,v in props.items(): setattr(n,k,v)
        return n

    def input(self, name, kind='NodeSocketFloat', value=None, low=None, high=None, description=''):
        s=self.tree.interface.new_socket(name=name, in_out='INPUT', socket_type=kind)
        if value is not None: s.default_value=value
        if low is not None: s.min_value=low
        if high is not None: s.max_value=high
        s.description=description
        return self.i.outputs[name]

    def output(self, name, geometry):
        self.tree.interface.new_socket(name=name, in_out='OUTPUT', socket_type='NodeSocketGeometry')
        self.set(self.o,name,geometry)

    def set(self, n, slot, value):
        s=n.inputs[slot]
        if isinstance(value,bpy.types.NodeSocket): self.tree.links.new(value,s)
        else: s.default_value=value
        return n

    def math(self, op, *args):
        n=self.node('ShaderNodeMath',op,operation=op)
        for i,v in enumerate(args): self.set(n,i,v)
        return n.outputs[0]

    def vec(self, x=0,y=0,z=0):
        n=self.node('ShaderNodeCombineXYZ')
        for i,v in enumerate((x,y,z)): self.set(n,i,v)
        return n.outputs[0]

    def vector(self,op,*args):
        n=self.node('ShaderNodeVectorMath',op,operation=op)
        for i,v in enumerate(args): self.set(n,i,v)
        return n.outputs['Value' if op in ('LENGTH','DISTANCE','DOT_PRODUCT') else 'Vector']

    def separate(self, v):
        n=self.node('ShaderNodeSeparateXYZ');self.set(n,0,v)
        return tuple(n.outputs)

    def switch(self, condition, false, true, kind='GEOMETRY'):
        n=self.node('GeometryNodeSwitch',input_type=kind)
        for k,v in [('Switch',condition),('False',false),('True',true)]:
            if v is not None:self.set(n,k,v)
        return n.outputs['Output']

    def boolean(self,op,a,b):
        n=self.node('FunctionNodeBooleanMath',op,operation=op)
        self.set(n,0,a);self.set(n,1,b)
        return n.outputs[0]

    def join(self, items):
        n=self.node('GeometryNodeJoinGeometry')
        for geo in items:self.set(n,'Geometry',geo)
        return n.outputs[0]

    def transform(self,geo,translation=(0,0,0),scale=(1,1,1),rotation=(0,0,0)):
        n=self.node('GeometryNodeTransform')
        for k,v in [('Geometry',geo),('Translation',translation),('Scale',scale),('Rotation',rotation)]:self.set(n,k,v)
        return n.outputs[0]

    def store(self,geo,name,value,kind='INT',domain='FACE'):
        n=self.node('GeometryNodeStoreNamedAttribute',name,data_type=kind,domain=domain)
        self.set(n,'Geometry',geo);self.set(n,'Name',name);self.set(n,'Value',value)
        return n.outputs['Geometry']

    def attr(self,name,kind='INT'):
        n=self.node('GeometryNodeInputNamedAttribute',name,data_type=kind);self.set(n,'Name',name)
        return n.outputs['Attribute']

    def object(self,obj):
        n=self.node('GeometryNodeObjectInfo',obj.name if obj else 'Object input',transform_space='RELATIVE')
        if obj:self.set(n,'Object',obj)
        self.set(n,'As Instance',False)
        return n

    def random(self,seed,identifier,stream,low=0,high=1,kind='FLOAT'):
        n=self.node('FunctionNodeRandomValue',f'Random stream {stream}',data_type=kind)
        self.set(n,'Min',low);self.set(n,'Max',high);self.set(n,'ID',identifier)
        self.set(n,'Seed',self.math('ADD',seed,stream))
        return n.outputs['Value']

    def mesh_boolean(self, op,a,b,solver='MANIFOLD'):
        n=self.node('GeometryNodeMeshBoolean',op,operation=op,solver=solver)
        if op=='DIFFERENCE':self.set(n,'Mesh 1',a);self.set(n,'Mesh 2',b)
        else:self.set(n,'Mesh',a);self.set(n,'Mesh',b)
        if solver=='EXACT':self.set(n,'Self Intersection',True);self.set(n,'Hole Tolerant',True)
        return n.outputs['Mesh']

    def arrange(self):
        # Readable breadth-first columns, with exact dependencies laid out left to right.
        depth={n:0 for n in self.tree.nodes}
        for _ in range(30):
            changed=False
            for l in self.tree.links:
                d=depth[l.from_node]+1
                if depth[l.to_node]<d:depth[l.to_node]=d;changed=True
            if not changed:break
        rows={}
        for n in self.tree.nodes:
            d=depth[n];r=rows.get(d,0);rows[d]=r+1
            n.location=(d*235,-r*210);n.width=205
