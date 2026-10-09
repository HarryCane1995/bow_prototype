"""Read-only observer for real UI smoke tests; never tags, updates or edits meshes."""
import bpy,bmesh,json,hashlib
from pathlib import Path
REPORT=Path(__file__).resolve().parents[3]/'Docs/Reviews/GNLevelBlockout/ux_states.json'
def capture(label):
    record={'label':label,'mode':bpy.context.mode,'selected':[o.name for o in bpy.context.selected_objects]}
    for name in ('LEVEL_FIELD','LEVEL_CUTTER'):
        obj=bpy.data.objects[name]
        if obj.mode=='EDIT':
            bm=bmesh.from_edit_mesh(obj.data)
            vertices=[list(v.co) for v in bm.verts]
            faces=len(bm.faces)
        else:
            vertices=[list(v.co) for v in obj.data.vertices]
            faces=len(obj.data.polygons)
        record[name]={'vertices':vertices,'faces':faces,'matrix':[list(r) for r in obj.matrix_world]}
    obj=bpy.data.objects['LEVEL_GENERATED_OUTPUT']
    mod=obj.modifiers[0]
    ids={s.name:s.identifier for s in mod.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT'}
    record['seed']=mod[ids['Seed']]
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    data={'v':[list(v.co) for v in mesh.vertices],'f':[list(p.vertices) for p in mesh.polygons]}
    record['output']={'vertices':len(data['v']),'faces':len(data['f']),
        'hash':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),
        'bounds':[[min(v[i] for v in data['v']),max(v[i] for v in data['v'])] for i in range(3)],
        'warnings':[w.message for w in ev.modifiers[0].node_warnings]}
    ev.to_mesh_clear()
    records=json.loads(REPORT.read_text()) if REPORT.exists() else []
    records.append(record);REPORT.write_text(json.dumps(records,indent=2))
    print(json.dumps({k:v for k,v in record.items() if not k.startswith('LEVEL_')}))
bpy.app.driver_namespace['blk_capture']=capture
