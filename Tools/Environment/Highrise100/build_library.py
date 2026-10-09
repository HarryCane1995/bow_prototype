"""Deterministic standalone asset library. Never edits a production level.
blender --background --factory-startup --python Tools/Environment/Highrise100/build_library.py -- --to 25
Subsequent --to 50/75/100 rebuild source deterministically; existing previews are reused.
"""
import bpy, math, json, random, hashlib, sys, shutil, argparse
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(HERE))
import architectures_a as A
try: import architectures_b as B
except ImportError: B=None
FAMILIES=list(A.NAMES)+(list(B.NAMES) if B else [])
NAMES={**A.NAMES,**(B.NAMES if B else {})}
RECIPES={r['key']:r for r in json.loads((OUT/'materials.json').read_text())}
M={}

def material(key):
    if key in M:return M[key]
    # UV role rules may have already made a shared original material on an
    # earlier asset (e.g. wall_maintenance for roof access). Reuse its identity.
    existing=bpy.data.materials.get('H100_'+key)
    if existing is not None:M[key]=existing;return existing
    mat=bpy.data.materials.new('H100_'+key);mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get('Principled BSDF');p.inputs['Roughness'].default_value=.7
    if key in ('signal','warm','glass'):
        rgb={'signal':(.09,.47,.53,1),'warm':(.70,.30,.065,1),'glass':(.035,.075,.095,1)}[key]
        p.inputs['Base Color'].default_value=rgb
        if key!='glass':p.inputs['Emission Color'].default_value=rgb;p.inputs['Emission Strength'].default_value=1.4
        else:p.inputs['Metallic'].default_value=.25;p.inputs['Roughness'].default_value=.28
        mat.diffuse_color=rgb
    else:
        mat['recipe']=RECIPES[key]['recipe'];mat['seed']=RECIPES[key]['seed']
        tex={}
        for i,ch in enumerate(('albedo','normal','orm','emission')):
            node=n.new('ShaderNodeTexImage');img=bpy.data.images.load(str(OUT/'Textures'/key/(ch+'.png')),check_existing=True)
            img.filepath=f'//Textures/{key}/{ch}.png'
            if ch in ('normal','orm'):img.colorspace_settings.name='Non-Color'
            node.image=img;node.interpolation='Linear';node.extension='EXTEND' if RECIPES[key]['mode'].startswith('UNIQUE') else 'REPEAT';node.location=(-600,-i*270);tex[ch]=node
        l.new(tex['albedo'].outputs['Color'],p.inputs['Base Color'])
        l.new(tex['emission'].outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.75
        normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.32;l.new(tex['normal'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
        sep=n.new('ShaderNodeSeparateColor');l.new(tex['orm'].outputs['Color'],sep.inputs['Color']);l.new(sep.outputs['Green'],p.inputs['Roughness']);l.new(sep.outputs['Blue'],p.inputs['Metallic'])
        # AO exported using glTF's documented custom node group; Blender lighting remains physical.
        ng=bpy.data.node_groups.get('glTF Material Output')
        if ng is None:
            ng=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree');ng.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
        ao=n.new('ShaderNodeGroup');ao.node_tree=ng;l.new(sep.outputs['Red'],ao.inputs['Occlusion'])
    M[key]=mat;return mat

def mapping(f,v):
    facade=[0,1,2,1,2,5,1,0,0,2,4,1,3,5,2,2,5,4,3,5][f]
    # Purpose-led, not arbitrary: residential/maintenance warm concrete; utility metal/vent.
    surfaces=['wall_corporate','wall_reinforced','wall_reactor_housing','wall_maintenance','wall_vent_bank','accent_billboard_support','wall_megablock','wall_corporate','wall_corporate','wall_reactor_housing',
              'wall_corporate','wall_maintenance','wall_reinforced','wall_tech_spine','wall_service_rack','accent_datacenter','wall_corporate','wall_maintenance','wall_reinforced','wall_tech_spine']
    service=surfaces[f]
    if service not in RECIPES:service='wall_reinforced'
    vi=(v+f//4)%4
    # Cleaner corporate, older maintenance: keep purposeful finish while varying rhythm.
    if f==0:vi=v%2
    if f==11:vi=2+v%2
    secondary=[4,1,2,4,2,4,0,5,4,2,0,4,4,2,4,2,0,1,3,0][f]
    return dict(facade=f'f{facade}_{vi}',secondary=f'f{secondary}_{(vi+1)%4}',concrete='wall_dark_concrete',
        metal='floor_metal_deck',service=service,roof='floor_rooftop',glass='glass',signal='signal',warm='warm',sign='accent_emissive_panel')

class Tower:
    def __init__(self,index,key,v,w,d,h):
        self.id=f'HR{index:03}';self.index=index;self.key=key;self.variant=v;self.w=w;self.d=d;self.h=h
        self.col=bpy.data.collections.new(self.id+'_'+NAMES[key][v].replace(' ','_'));self.col.use_fake_user=True
        self.root=bpy.data.objects.new(self.id,None);self.col.objects.link(self.root)
        self.maps=mapping(FAMILIES.index(key),v);self.groups={};self.tags=[];self.primitives=[]
        self.floor_pitch=[3.3,4.1,4.8,3.6,5.4][v]
    def tag(self,*values):self.tags.extend(values)
    def geom(self,part,verts,faces,mat,uv=None):
        key=(part,self.maps[mat]);vs,fs,us=self.groups.setdefault(key,([],[],[]));offset=len(vs)
        vs.extend([tuple(v) for v in verts]);fs.extend([tuple(offset+i for i in face) for face in faces])
        if uv is None:
            uv=[]
            for face in faces:
                pts=[Vector(verts[i]) for i in face];norm=(pts[1]-pts[0]).cross(pts[2]-pts[0]);axis=max(range(3),key=lambda i:abs(norm[i]));axes=[i for i in range(3) if i!=axis]
                uv.append([(p[axes[0]]/12,p[axes[1]]/12) for p in pts])
        us.extend(uv)
    def box(self,part,center,size,mat='facade',rot=0):
        if min(size)<=0:raise ValueError((part,size))
        cx,cy,cz=center;sx,sy,sz=[s/2 for s in size];r=math.radians(rot)
        local=[(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),(-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]
        verts=[(cx+x*math.cos(r)-y*math.sin(r),cy+x*math.sin(r)+y*math.cos(r),cz+z) for x,y,z in local]
        faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        if mat in ('facade','secondary'):
            self.geom(part+'_Caps',verts,faces[:2],'roof')
            rec=RECIPES[self.maps[mat]];tile_h=1024/rec['parameters']['floor_height']*self.floor_pitch
            uvs=[]
            for j,face in enumerate(faces[2:]):
                width=size[j%2];u=min(.96,width/42);v=min(.96,size[2]/tile_h)
                uvs.append([(.02,.02),(.02+u,.02),(.02+u,.02+v),(.02,.02+v)])
            self.geom(part,verts,faces[2:],mat,uvs)
        elif mat=='sign':self.geom(part,verts,faces,mat,[[(0,0),(1,0),(1,1),(0,1)]]*6)
        else:self.geom(part,verts,faces,mat)
        self.primitives.append(dict(type='box',part=part,center=list(center),size=list(size),material=mat,rotation=rot))
    def taper(self,part,levels,mat='facade',n=8):
        verts=[]
        for z,rx,ry,cx,cy in levels:
            verts.extend([(cx+rx*math.cos(math.tau*(i+.5)/n),cy+ry*math.sin(math.tau*(i+.5)/n),z) for i in range(n)])
        caps=[tuple(reversed(range(n))),tuple((len(levels)-1)*n+i for i in range(n))]
        self.geom(part+'_Caps',verts,caps,'roof' if mat in ('facade','secondary') else mat)
        faces=[];uvs=[];zmin=levels[0][0];zmax=levels[-1][0]
        for j in range(len(levels)-1):
            for i in range(n):
                faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
                width=(Vector(verts[j*n+i])-Vector(verts[j*n+(i+1)%n])).length
                u=min(.96,width/42);lo=.02+.96*(levels[j][0]-zmin)/(zmax-zmin);hi=.02+.96*(levels[j+1][0]-zmin)/(zmax-zmin)
                uvs.append([(.02,lo),(.02+u,lo),(.02+u,hi),(.02,hi)])
        self.geom(part,verts,faces,mat,uvs if mat in ('facade','secondary') else None)
        self.primitives.append(dict(type='taper',part=part,levels=levels,material=mat,sides=n))
    def cylinder(self,part,center,radius,height,mat='metal',n=12):
        x,y,z=center;self.taper(part,[(z-height/2,radius,radius,x,y),(z+height/2,radius,radius,x,y)],mat,n)
    def beam(self,part,a,b,width,mat='metal'):
        a,b=Vector(a),Vector(b);axis=(b-a).normalized();u=axis.cross(Vector((0,1,0)))
        if u.length<.01:u=axis.cross(Vector((1,0,0)))
        u.normalize();v=axis.cross(u).normalized()
        pts=[p+u*x*width/2+v*y*width/2 for p in (a,b) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        self.geom(part,pts,[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
        self.primitives.append(dict(type='beam',part=part,a=list(a),b=list(b),width=width,material=mat))
    def band(self,x,y,z,w,d,thickness=1.2,mat='metal'):self.box('Belts',(x,y,z),(w,d,thickness),mat)
    def podium(self,w,d,h=12):
        self.box('Podium',(0,0,h/2),(w,d,h),'concrete');self.band(0,0,h,w+2,d+2,1.5)
        self.box('LoadingEntry',(w*.22,-d/2-.1,h*.42),(w*.18,.4,h*.65),'service')
    def antenna(self,x,y,z,height=18):
        self.cylinder('Antenna',(x,y,z+height/2),.35,height,'metal',6);self.box('Beacon',(x,y,z+height),(.65,.65,.8),'warm')
    def screen(self,x,y,z,w,h,variant=0):
        self.maps['sign']='sign_'+str(variant%6)
        self.box('BillboardFrame',(x,y,z),(w+1.6,1.6,h+1.6),'metal')
        self.box('Display',(x,y-.86,z),(w,.14,h),'sign')
        color='signal' if variant%2==0 else 'warm'
        self.box('DisplayRail',(x-w*.44,y-1,z),(.7,.25,h*.88),color)
        # Independent mounting standoffs make the board read as a later addition.
        for xx in (-w*.38,w*.38):self.box('ScreenMount',(x+xx,y+1.7,z),(1.3,4.3,h*.87),'metal')
    def roof(self,x,y,z,w,d,style=0):
        style%=5;scale=min(w,d)
        self.box('RoofAccess',(x-w*.25,y+d*.19,z+2.2),(max(3,w*.2),max(3,d*.27),4.4),'service')
        if style==0:
            for i in range(2):
                self.box('HVAC',(x+w*(.05+i*.25),y,z+2),(w*.18,d*.32,4),'service')
                self.cylinder('HVACFan',(x+w*(.05+i*.25),y,z+4.2),scale*.07,.5,'metal')
        elif style==1:
            self.cylinder('WaterTank',(x+w*.17,y,z+4),scale*.18,8,'service',10)
            for xx in (-.2,.2):self.beam('TankFeet',(x+w*.17+xx*scale,y,z),(x+w*.17+xx*scale,y,z+2),.7)
        elif style==2:
            for i in range(3):self.cylinder('Exhaust',(x+(-.1+i*.22)*w,y-d*.08,z+3+i),scale*.065,6+2*i,'metal',8)
        elif style==3:
            self.box('RoofShed',(x+w*.1,y,z+3.7),(w*.42,d*.44,7.4),'concrete')
            self.box('ReplacementPanel',(x+w*.1,y-d*.23,z+3.7),(w*.30,.35,4.6),'service')
        else:
            self.box('CommsCabinet',(x+w*.18,y,z+2),(w*.18,d*.2,4),'service')
            self.antenna(x+w*.18,y,z+4,12)
        self.tag('roof_'+['paired_hvac','water_tank','exhaust_trio','retrofit_shed','comms'][style])
    def finish(self):
        pts=[];polygons=0;triangles=0;slots={}
        for (part,key),(vs,fs,uvs) in self.groups.items():
            mesh=bpy.data.meshes.new(self.id+'_'+part);mesh.from_pydata(vs,[],fs);mesh.update()
            obj=bpy.data.objects.new(self.id+'_'+part,mesh);self.col.objects.link(obj);obj.parent=self.root
            mesh.materials.append(material(key));uv=mesh.uv_layers.new(name='UVMap')
            for poly,coords in zip(mesh.polygons,uvs):
                for li,coord in zip(poly.loop_indices,coords):uv.data[li].uv=coord
            obj['part']=part;obj['recipe']=key;pts.extend(vs);polygons+=len(fs);triangles+=sum(len(f)-2 for f in fs);slots[part]=key
        pmin=[min(p[i] for p in pts) for i in range(3)];pmax=[max(p[i] for p in pts) for i in range(3)];bounds=[pmax[i]-pmin[i] for i in range(3)]
        family=FAMILIES.index(self.key)
        role='hero' if family in (18,19) or (family in (6,13) and self.variant==4) else 'background' if family in (0,3,7,10,11,15) else 'midground'
        rec=RECIPES[self.maps['facade']]
        surface_counts={s:sum(len(fs) for (part,k),(vs,fs,us) in self.groups.items() if k==s) for s in set(slots.values())}
        structural=sum(1 for p in self.primitives if p['type']=='beam')
        industrial=sum(1 for p in self.primitives if p['material'] in ('service','metal'))/max(1,len(self.primitives))
        axes=dict(verticality=round(min(1,bounds[2]/max(bounds[:2])/10),3),mass_complexity=round(min(1,len(self.primitives)/95),3),industrial_density=round(industrial,3),
            window_emission_density=rec['parameters']['emission_density'],signage_density=round(min(1,sum('Display' in p['part'] for p in self.primitives)/30),3),
            weathering=rec['parameters']['grime_amount'],structural_exposure=round(min(1,structural/28),3),cantilever_overhang=round(min(1,max(bounds[0]/self.w-1,0)+(.38 if any('offset' in t or 'cantilever' in t or 'suspend' in t for t in self.tags) else .06)),3),
            rooftop_complexity=round(min(1,sum(any(s in p['part'].lower() for s in ('roof','antenna','hvac','exhaust','tank','comms')) for p in self.primitives)/15),3),
            old_new=([.82,.38,.28,.32,.25,.70,.65,.90,.75,.28,.48,.16,.65,.72,.38,.80,.72,.46,.70,.82][family]))
        geom_hash=hashlib.sha256(json.dumps({str(k):(v,f) for k,(v,f,u) in self.groups.items()},sort_keys=True).encode()).hexdigest()
        canonical_faces=[]
        for vs,fs,us in self.groups.values():
            canonical_faces.extend(sorted(tuple(round(x,5) for x in vs[i]) for i in face) for face in fs)
        geometry_only=hashlib.sha256(json.dumps(sorted(canonical_faces)).encode()).hexdigest()
        self.root['id']=self.id;self.root['family']=self.key;self.root['seed']=925100+self.index*7919;self.root['role']=role
        self.col.asset_mark();self.col.asset_data.description=f'{self.id} | {NAMES[self.key][self.variant]} | {self.key} | {role}'
        for value in (self.key,role,'BowPrototype','Highrise100'):self.col.asset_data.tags.new(value)
        record=dict(id=self.id,name=NAMES[self.key][self.variant],category=self.key,subtype=self.variant,seed=self.root['seed'],role=role,collection=self.col.name,
            bounds_m=bounds,bounds_min=pmin,bounds_max=pmax,parameters=dict(width=self.w,depth=self.d,height=self.h,floor_pitch=self.floor_pitch),
            features=sorted(set(self.tags)),metrics=dict(meshes=len(self.groups),primitives=len(self.primitives),triangles=triangles,vertices=len(pts),polygons=polygons),
            geometry_sha256=geom_hash,geometry_only_sha256=geometry_only,geometry_method='authored deterministic subtype and explicit dimensions; seed is recipe identity, not random geometry sampling',axes=axes,axes_method='diagnostic proxies from geometry/material settings; old_new is authored intention, not a perceptual measurement',
            material_slots=slots,material_face_counts=surface_counts,recipes=[RECIPES[k]['recipe'] for k in sorted(set(slots.values())) if k in RECIPES],
            material_seeds={k:RECIPES[k]['seed'] for k in sorted(set(slots.values())) if k in RECIPES},previews=[f'Previews/{self.id}.png'],source='Highrise100.blend')
        # Shared non-geometric UV/material migration; also used on saved libraries.
        # Requires prepare_uv_tiles.py after the original materials are prepared.
        from uv_material_rules import apply_collection
        apply_collection(self.col,record)
        self.root['record_json']=json.dumps(record);self.col['id']=self.id
        return record

def aim(obj,point):obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
def stage():
    scene=bpy.data.scenes.new('Neutral_Preview');scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=16
    scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.65
    world=bpy.data.worlds.new('Neutral_Studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.22,.27,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;scene.world=world
    for name,energy,color,rotation in [('Key',2.8,(1,.86,.70),(28,-32,-35)),('Fill',1.0,(.63,.79,1),(50,20,130))]:
        data=bpy.data.lights.new(name,'SUN');data.energy=energy;data.angle=.1;data.color=color
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.rotation_euler=[math.radians(a) for a in rotation]
        if name=='Fill':data.use_shadow=False
    cam=bpy.data.objects.new('Preview_Camera',bpy.data.cameras.new('Preview_Camera'));scene.collection.objects.link(cam);cam.data.type='ORTHO';cam.data.clip_end=10000;cam.data.clip_start=.1;scene.camera=cam
    inst=bpy.data.objects.new('PREVIEW_INSTANCE',None);inst.instance_type='COLLECTION';scene.collection.objects.link(inst)
    # Ground communicates base contact; it is preview-only, never in an asset collection.
    mesh=bpy.data.meshes.new('Ground');mesh.from_pydata([(-2000,-2000,-.08),(2000,-2000,-.08),(2000,2000,-.08),(-2000,2000,-.08)],[],[(0,1,2,3)])
    obj=bpy.data.objects.new('Ground',mesh);scene.collection.objects.link(obj)
    m=bpy.data.materials.new('Preview_Ground');m.diffuse_color=(.105,.13,.155,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=m.diffuse_color;mesh.materials.append(m)
    return scene,cam,inst

def render(scene,cam,instance,tower,rec,azimuth=0,suffix=''):
    instance.instance_collection=tower.col
    pmin=Vector(rec['bounds_min']);pmax=Vector(rec['bounds_max']);target=(pmin+pmax)/2
    direction=Vector((.9,-1.6,.72));direction.rotate(__import__('mathutils').Matrix.Rotation(math.radians(azimuth),3,'Z'))
    direction.normalize();cam.location=target+direction*1800;aim(cam,target)
    inv=cam.rotation_euler.to_matrix().transposed()
    corners=[inv@(Vector((x,y,z))-target) for x in (pmin.x,pmax.x) for y in (pmin.y,pmax.y) for z in (pmin.z,pmax.z)]
    spanx=max(p.x for p in corners)-min(p.x for p in corners);spany=max(p.y for p in corners)-min(p.y for p in corners)
    cam.data.ortho_scale=max(spany,spanx/0.8)*1.15
    scene.render.filepath=str(OUT/'Previews'/(rec['id']+suffix+'.png'))
    bpy.context.window.scene=scene;bpy.ops.render.render(write_still=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--to',type=int,default=100);parser.add_argument('--render-from',type=int,default=1);parser.add_argument('--rerender',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.to>len(FAMILIES)*5:raise RuntimeError('Architecture module not ready')
    if shutil.disk_usage(ROOT).free<30*1024**3:raise RuntimeError('Disk reserve 30 GiB')
    # This is a dedicated background process; never factory-reset a connected user scene.
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    bpy.context.preferences.filepaths.save_version=0
    library=bpy.context.scene;library.name='Library_100';library.unit_settings.system='METRIC'
    preview,cam,inst=stage();records=[];towers=[]
    # Deterministic authored dimensions deliberately cover squat high-rises to very tall needles.
    ranges=[(38,34,280),(78,49,190),(54,40,235),(66,29,180),(44,42,225),(42,33,260),(90,66,265),(24,22,410),(64,31,270),(55,47,220),
            (52,40,230),(59,34,200),(54,44,315),(55,37,290),(95,43,205),(52,46,190),(80,44,230),(90,55,210),(63,43,310),(63,48,380)]
    for index in range(1,args.to+1):
        f=(index-1)//5;v=(index-1)%5;key=FAMILIES[f];bw,bd,bh=ranges[f]
        w=round(bw*[.90,1.06,.82,1.16,.98][v],2);d=round(bd*[1.07,.82,1.22,.91,1.0][v],2);h=round(bh*[.88,1.03,1.19,.95,1.10][v],2)
        tower=Tower(index,key,v,w,d,h);(A if key in A.NAMES else B).build(tower,key,v,w,d,h)
        rec=tower.finish();records.append(rec);towers.append(tower)
        instance=bpy.data.objects.new(rec['id']+' | '+rec['name'],None);instance.instance_type='COLLECTION';instance.instance_collection=tower.col;instance.location=((index-1)%10*190,(index-1)//10*190,0);library.collection.objects.link(instance)
    (OUT/'manifest.json').write_text(json.dumps(dict(schema='bow.highrise100.v1',count=len(records),seed=925100,units='meters',families=FAMILIES,buildings=records),indent=2))
    bpy.context.window.scene=library
    for area in bpy.context.screen.areas:
        if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=2400;area.spaces.active.region_3d.view_location=(850,850,180)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highrise100.blend'),compress=True)
    for tower,rec in zip(towers,records):
        index=int(rec['id'][2:])
        if index<args.render_from:continue
        if not args.rerender and (OUT/rec['previews'][0]).exists():continue
        if shutil.disk_usage(ROOT).free<30*1024**3:raise RuntimeError('Disk reserve')
        render(preview,cam,inst,tower,rec)
        print('BUILDING_PREVIEW',rec['id'],rec['category'],flush=True)
    print('HIGHRISE_BATCH_COMPLETE',len(records),flush=True)
if __name__=='__main__':main()
