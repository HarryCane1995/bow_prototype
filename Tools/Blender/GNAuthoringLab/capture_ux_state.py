"""Read-only evidence capture after real GUI actions; no mesh/depsgraph refresh writes."""
import bpy,bmesh,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def capture(label):
    records={}
    for name in ('LEVEL_AUTHORING_SOURCE','LEVEL_ENVELOPE','LEVEL_GENERATED_OUTPUT'):
        obj=bpy.data.objects[name]
        if obj.mode=='EDIT':
            bm=bmesh.from_edit_mesh(obj.data)
            vertices=[list(v.co) for v in bm.verts]
            counts=[len(bm.verts),len(bm.faces)]
        else:
            vertices=[list(v.co) for v in obj.data.vertices]
            counts=[len(obj.data.vertices),len(obj.data.polygons)]
        record={'mode':obj.mode,'base_vertices_faces':counts,'base_coordinates':vertices}
        if name=='LEVEL_GENERATED_OUTPUT':
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
            record['evaluated_vertices_faces']=[len(mesh.vertices),len(mesh.polygons)]
            record['bounds']=[[min(v.co[i] for v in mesh.vertices),max(v.co[i] for v in mesh.vertices)] for i in range(3)] if mesh.vertices else []
            record['node_warnings']=[str(w.message) for w in evaluated.modifiers[0].node_warnings]
            evaluated.to_mesh_clear()
        records[name]=record
    path=ROOT/'Docs/Reviews/GNAuthoringLab/ux_states.json'
    data=json.loads(path.read_text()) if path.exists() else {}
    data[label]={'time':time.strftime('%Y-%m-%d %H:%M:%S'),'objects':records}
    path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(label,json.dumps({k:{p:v[p] for p in v if p!='base_coordinates'} for k,v in records.items()}))
if __name__=='__main__':capture('capture')
