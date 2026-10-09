"""One-shot, original editable humanoid cages. Never rebuild over manual edits by default.

Execute in Blender via MCP, passing __file__, or blender --background --python this.py.
This is an authoring recipe, not a runtime/procedural dependency of the saved meshes.
"""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'Assets/Characters/BaseHumanoid'
SOURCE = BASE / 'Source/Humanoid_Base.blend'
if SOURCE.exists() and '--rebuild-humanoid' not in sys.argv:
    raise RuntimeError('Existing source protected. Edit the .blend manually; explicit rebuild flag required.')
if bpy.data.is_dirty and bpy.data.filepath and Path(bpy.data.filepath) != SOURCE:
    raise RuntimeError('Unsaved unrelated Blender file is protected.')

# Replace only an empty startup or our dedicated source, never an unrelated scene.
if bpy.data.filepath and Path(bpy.data.filepath) != SOURCE:
    raise RuntimeError('Use a separate Blender process for this build.')
if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
for col in list(bpy.data.collections): bpy.data.collections.remove(col)
sc = bpy.context.scene
sc.name = 'Humanoid_Base_Authoring'
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1
sc.unit_settings.length_unit = 'METERS'
sc['purpose'] = 'Original technical male/female mannequin; no animation set'
sc['axes'] = 'Blender +Z up, -Y front. glTF/Godot +Y up, +Z model front.'
sc['rig_standard'] = 'BH_01 / 53 bones / local Y head-to-tail / mirrored L-R'

def material(name, color):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color,1); m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color,1); bs.inputs['Roughness'].default_value = .78
    return m

def blend(a,b,t):
    t=max(0,min(1,t));t=t*t*(3-2*t)
    return {a:1-t,b:t}

class Cage:
    def __init__(self): self.v=[];self.f=[];self.w=[]
    def point(self,p,w):
        i=len(self.v);self.v.append(tuple(p));self.w.append({k:v for k,v in w.items() if v>1e-7});return i
    def ring(self,center,u,v,rx,ry,n,w,phase=0):
        c=Vector(center);u=Vector(u);v=Vector(v)
        return [self.point(c+u*rx*math.cos(phase+i*math.tau/n)+v*ry*math.sin(phase+i*math.tau/n),w) for i in range(n)]
    def bridge(self,a,b):
        assert len(a)==len(b),(len(a),len(b))
        for i in range(len(a)):
            j=(i+1)%len(a);self.f.append((a[i],a[j],b[j],b[i]))
    def match(self,a,b):
        # Align a branch's first ring by geometric distance, including winding.
        opts=[]
        for r in (b,list(reversed(b))):
            for k in range(len(r)):
                t=r[k:]+r[:k]
                opts.append((sum((Vector(self.v[x])-Vector(self.v[y])).length_squared for x,y in zip(a,t)),t))
        return min(opts,key=lambda t:t[0])[1]
    def cap(self,a,w):
        c=sum((Vector(self.v[i]) for i in a),Vector())/len(a);mid=self.point(c,w)
        for i in range(len(a)): self.f.append((a[i],a[(i+1)%len(a)],mid))

def build(kind, female=False):
    # Different anthropometric profiles, sharing joint hierarchy and mesh topology.
    h=.9444444444 if female else 1.0
    col=bpy.data.collections.new('10_'+kind);sc.collection.children.link(col)
    g=Cage(); bones={}
    def bone(n,a,b,parent=None): bones[n]=(Vector(a),Vector(b),parent)
    pelvis_z=1.00 if female else 1.00
    bone('root',(0,0,0),(0,0,.14))
    bone('pelvis',(0,0,pelvis_z),(0,0,1.09),'root')
    bone('spine_01',(0,0,1.09),(0,0,1.21),'pelvis')
    bone('spine_02',(0,0,1.21),(0,0,1.34),'spine_01')
    bone('chest',(0,0,1.34),(0,0,1.46),'spine_02')
    bone('neck',(0,0,1.46),(0,0,1.59),'chest')
    bone('head',(0,0,1.59),(0,0,1.76),'neck')
    def torso_w(z):
        if z<1.04:return {'pelvis':1}
        if z<1.15:return blend('pelvis','spine_01',(z-1.04)/.11)
        if z<1.27:return blend('spine_01','spine_02',(z-1.15)/.12)
        if z<1.40:return blend('spine_02','chest',(z-1.27)/.13)
        if z<1.49:return {'chest':1}
        if z<1.57:return blend('chest','neck',(z-1.49)/.06)
        return blend('neck','head',(z-1.57)/.055)
    # z, half width, front depth, rear depth. Shoulder ports occupy rows 12..16.
    profile=[(.93,.173,.107,.125),(.98,.181,.113,.134),(1.025,.174,.116,.132),
      (1.075,.151,.109,.113),(1.12,.132,.102,.10),(1.17,.133,.103,.10),
      (1.22,.146,.111,.105),(1.27,.158,.117,.11),(1.31,.169,.120,.114),
      (1.34,.176,.119,.112),(1.36,.181,.116,.108),(1.38,.185,.112,.103),
      (1.40,.187,.107,.099),(1.425,.188,.102,.094),(1.45,.185,.093,.087),
      (1.475,.170,.083,.080),(1.49,.143,.073,.075),(1.515,.092,.057,.059),
      (1.54,.054,.049,.051),(1.565,.048,.046,.047),
      (1.585,.048,.046,.048),(1.605,.055,.061,.056),(1.625,.068,.077,.063),
      (1.65,.080,.086,.071),(1.68,.085,.088,.080),(1.715,.083,.087,.086),
      (1.75,.074,.077,.078),(1.778,.055,.057,.059),(1.794,.030,.032,.033),
      (1.800,.004,.004,.004)]
    # Female is not a scaled male: wider pelvis/thighs, narrower rib cage/shoulders,
    # shorter arms, smaller hands/feet; smooth chest with no secondary detail.
    def width_factor(z):
        if not female:return 1
        keys=[(.93,1.10),(1.025,1.105),(1.075,1.035),(1.12,.945),(1.17,.92),(1.27,.90),(1.45,.89),(1.49,.91),(1.54,.98),(1.8,.98)]
        for (za,fa),(zb,fb) in zip(keys,keys[1:]):
            if za<=z<=zb:
                t=(z-za)/(zb-za);t=t*t*(3-2*t);return fa+(fb-fa)*t
        return keys[-1][1]
    rings=[]
    for row,(z,rx,front,back) in enumerate(profile):
        rx*=width_factor(z)
        if female and z<1.49: front*=.94;back*=1.02 if z<1.075 else .94
        ids=[]
        for j in range(32):
            t=j*math.tau/32;sn=math.sin(t);cs=math.cos(t)
            zz=z-(.062*abs(sn) if row==0 else 0)
            yy=sn*(front if sn<0 else back)
            # Subtle abdominal plane and thoracic volume, no sculpted muscle cuts.
            if 1.2<z<1.44 and sn<0: yy-=.006*(math.sin(math.pi*(z-1.2)/.24))*abs(cs)
            weights=torso_w(z)
            if zz<1.065:
                t=max(0,min(1,(1.065-zz)/.225));t=t*t*(3-2*t)
                side_mix=max(0,min(1,(rx*cs+.04)/.08))
                weights={'pelvis':1-t,'thigh.L':t*side_mix,'thigh.R':t*(1-side_mix)}
            ids.append(g.point((rx*cs,yy,zz),weights))
        rings.append(ids)
    # Two rectangular shoulder ports: 6 circumference edges x 4 vertical edges.
    lo,hi=12,16
    for r in range(len(rings)-1):
        for j in range(32):
            is_port=lo<=r<hi and (j in [29,30,31,0,1,2] or 13<=j<19)
            if not is_port: g.f.append((rings[r][j],rings[r][(j+1)%32],rings[r+1][(j+1)%32],rings[r+1][j]))
    g.cap(rings[-1],{'head':1})
    # Shared crotch bridge makes torso and both legs one continuous closed surface.
    crotch=[g.point((0,y,.866),{'pelvis':.10,'thigh.L':.45,'thigh.R':.45}) for y in [-.052,0,.058]]
    for side,sign in [('L',1),('R',-1)]:
        suffix='.'+side
        hipx=.099 if female else .093
        sx=.181*(.89 if female else 1)
        shoulder=Vector((sx,0,1.444));elbow=Vector((sx+.199*(.96 if female else 1),-.015,1.215))
        wrist=Vector((sx+.354*(.96 if female else 1),-.045,1.030))
        # Mild elbow flex in front of body, no locked joints.
        hip=Vector((hipx,0,1.00));knee=Vector((.106,-.024,.535));ankle=Vector((.11,.005,.105))
        for n,a,b,p in [('clavicle',(0,0,1.45),shoulder,'chest'),('upper_arm',shoulder,elbow,'clavicle'+suffix),
                       ('forearm',elbow,wrist,'upper_arm'+suffix)]:
            bone(n+suffix,(a[0]*sign,a[1],a[2]),(b[0]*sign,b[1],b[2]),p if p=='chest' else p)
        bone('thigh'+suffix,(hip.x*sign,hip.y,hip.z),(knee.x*sign,knee.y,knee.z),'pelvis')
        bone('calf'+suffix,(knee.x*sign,knee.y,knee.z),(ankle.x*sign,ankle.y,ankle.z),'thigh'+suffix)
        ball=Vector((.11,-.142,.043));toe=Vector((.11,-.235,.034))
        bone('foot'+suffix,(ankle.x*sign,ankle.y,ankle.z),(ball.x*sign,ball.y,ball.z),'calf'+suffix)
        bone('toes'+suffix,(ball.x*sign,ball.y,ball.z),(toe.x*sign,toe.y,toe.z),'foot'+suffix)
        # Shoulder port around side theta 0 or pi.
        start=29 if sign==1 else 13
        js=[(start+i)%32 for i in range(7)]
        port=[rings[lo][j] for j in js]
        port += [rings[r][js[-1]] for r in range(lo+1,hi+1)]
        port += [rings[hi][j] for j in reversed(js[:-1])]
        port += [rings[r][js[0]] for r in range(hi-1,lo,-1)]
        for i in port:
            z=g.v[i][2];g.w[i]=blend('chest','clavicle'+suffix,.35 if z>1.455 else .18)
        # Arm ring paths, additional loops around elbow/wrist; no capsule overlaps.
        arm_specs=[(0.04,.060,.065),(.12,.066,.064),(.25,.064,.059),(.42,.059,.053),
          (.63,.049,.046),(.79,.041,.040),(.90,.037,.038),(.98,.037,.039),
          (1.05,.039,.040),(1.14,.042,.042),(1.30,.045,.043),(1.48,.041,.038),
          (1.67,.033,.030),(1.83,.027,.023),(1.94,.025,.021),(2.0,.026,.021)]
        last=port
        d=(wrist-elbow).normalized();u=Vector((-d.z,0,d.x)).normalized();v=Vector((0,1,0))
        for t,rx,ry in arm_specs:
            c=shoulder.lerp(elbow,t) if t<=1 else elbow.lerp(wrist,t-1)
            if female:rx*=.86;ry*=.87
            if t<.30:w=blend('clavicle'+suffix,'upper_arm'+suffix,t/.30)
            elif t<.79:w={'upper_arm'+suffix:1}
            elif t<1.19:w=blend('upper_arm'+suffix,'forearm'+suffix,(t-.79)/.40)
            elif t<1.83:w={'forearm'+suffix:1}
            else:w=blend('forearm'+suffix,'hand'+suffix,(t-1.83)/.28)
            c.x*=sign;uu=Vector((u.x*sign,u.y,u.z))
            rr=g.ring(c,uu,v,rx,ry,20,w)
            rr=g.match(last,rr);g.bridge(last,rr);last=rr
        # Palm as a structured front/back grid. Split fingertip boundary into four
        # true fingers; thumb branches from an open side port. All welded topology.
        hs=.90 if female else 1;plen=.09*hs;pwidth=.079*hs;pth=.019*hs
        def hp(x,y,z):
            p=wrist+u*x+v*y+d*z;p.x*=sign;return p
        bone('hand'+suffix,hp(0,0,0),hp(0,0,plen),'forearm'+suffix)
        ys=[0,.014,.033,.053,.073,.09]
        grids={};mids={}
        for face in [-1,1]:
            grids[face]=[]
            for ri,zz in enumerate(ys):
                frac=zz/.09;half=(.025*hs*(1-frac)+pwidth/2*frac)
                row=[]
                for j in range(9):
                    x=(j/8*2-1)*half
                    depth=pth*(1-.17*abs(j/4-1))*(1-.2*frac)
                    row.append(g.point(hp(x,face*depth,zz*hs),blend('forearm'+suffix,'hand'+suffix,.70+frac*1.5)))
                grids[face].append(row)
            for r in range(5):
                for j in range(8):g.f.append((grids[face][r][j],grids[face][r][j+1],grids[face][r+1][j+1],grids[face][r+1][j]))
        for j in [0,8]:
            mids[j]=[g.point((Vector(g.v[grids[-1][r][j]])+Vector(g.v[grids[1][r][j]]))/2,{'hand'+suffix:1}) for r in range(6)]
            for r in range(5):
                if j==8 and r in [1,2]:continue
                for f in [-1,1]:g.f.append((grids[f][r][j],grids[f][r+1][j],mids[j][r+1],mids[j][r]))
        bottom=grids[-1][0]+[mids[8][0]]+list(reversed(grids[1][0]))+[mids[0][0]]
        bottom=g.match(last,bottom);g.bridge(last,bottom)
        # Knuckle boundary: 3 front, side mid, 3 back, side mid => octagonal digit.
        topmid={0:mids[0][-1],8:mids[8][-1]}
        for j in [2,4,6]:topmid[j]=g.point(hp((j/8*2-1)*pwidth/2,0,plen),{'hand'+suffix:1})
        for fi,(fn,flen) in enumerate([('pinky',.060),('ring',.080),('middle',.086),('index',.078)]):
            j=fi*2;cx=((j+1)/8*2-1)*pwidth/2
            rootring=grids[-1][-1][j:j+3]+[topmid[j+2]]+list(reversed(grids[1][-1][j:j+3]))+[topmid[j]]
            flen*=hs
            starts=[0,.44,.76,1.0]
            for bi in range(3):bone(fn+'_'+str(bi+1).zfill(2)+suffix,hp(cx,0,plen+flen*starts[bi]),hp(cx,0,plen+flen*starts[bi+1]),'hand'+suffix if bi==0 else fn+'_'+str(bi).zfill(2)+suffix)
            prev=rootring
            for t in [.08,.21,.36,.43,.49,.61,.70,.76,.82,.92,.98,1.0]:
                rad=(.0094 if fi<3 else .0098)*hs*(1-.28*t)
                if fi==0:rad*=.88
                w={'hand'+suffix:1} if t<0 else {fn+'_01'+suffix:1}
                if t<.20:w=blend('hand'+suffix,fn+'_01'+suffix,t/.20)
                elif .34<t<.54:w=blend(fn+'_01'+suffix,fn+'_02'+suffix,(t-.34)/.20)
                elif t>=.54:w=blend(fn+'_02'+suffix,fn+'_03'+suffix,(t-.66)/.20)
                if t>=.98:rad*=.75 if t<1 else .3
                center=hp(cx+(fi-1.5)*.003*t, -.006*t*t,plen+flen*t)
                rr=g.ring(center,(u.x*sign,u.y,u.z),v,rad,rad*.85,8,w)
                rr=g.match(prev,rr);g.bridge(prev,rr);prev=rr
            g.cap(prev,{fn+'_03'+suffix:1})
        # Thumb: 3 useful segments including metacarpal opposition at palm.
        port=[grids[-1][r][8] for r in [1,2,3]]+[mids[8][3]]+[grids[1][r][8] for r in [3,2,1]]+[mids[8][1]]
        thumb_pts=[Vector((.028*hs,0,.022*hs)),Vector((.049*hs,-.009,.044*hs)),Vector((.063*hs,-.012,.069*hs)),Vector((.073*hs,-.014,.091*hs))]
        for bi in range(3):bone('thumb_'+str(bi+1).zfill(2)+suffix,hp(*thumb_pts[bi]),hp(*thumb_pts[bi+1]),'hand'+suffix if bi==0 else 'thumb_'+str(bi).zfill(2)+suffix)
        prev=port
        for t in [.18,.42,.70,.90,1.05,1.3,1.65,1.85,2.04,2.3,2.65,2.9,3.0]:
            seg=min(2,int(t));p=thumb_pts[seg].lerp(thumb_pts[seg+1],t-seg)
            axis=(hp(*thumb_pts[seg+1])-hp(*thumb_pts[seg])).normalized();ru=axis.cross(Vector((0,1,0))).normalized()
            rad=.012*hs*(1-.30*t/3)*(1 if t<2.9 else (.8 if t<3 else .3))
            if t<.6:w=blend('hand'+suffix,'thumb_01'+suffix,t/.6)
            elif t<1.3:w=blend('thumb_01'+suffix,'thumb_02'+suffix,(t-.8)/.5)
            else:w=blend('thumb_02'+suffix,'thumb_03'+suffix,(t-1.8)/.5)
            rr=g.ring(hp(*p),ru,(0,1,0),rad,rad*.9,8,w);rr=g.match(prev,rr);g.bridge(prev,rr);prev=rr
        g.cap(prev,{'thumb_03'+suffix:1})
        # Pelvis bifurcation, thighs, knee support loops, calf, ankle, then foot.
        last=([rings[0][j%32] for j in range(24,41)]+list(reversed(crotch))) if sign==1 else ([rings[0][j] for j in range(8,25)]+crotch)
        legs=[(.868,.091,.097),(.82,.086,.093),(.76,.079,.088),(.69,.069,.078),(.62,.056,.064),
              (.575,.049,.052),(.55,.047,.048),(.535,.047,.047),(.516,.045,.047),(.49,.044,.048),
              (.453,.048,.057),(.407,.051,.063),(.353,.047,.060),(.29,.039,.05),(.23,.031,.040),
              (.173,.026,.031),(.135,.026,.027),(.11,.027,.027)]
        for z,rx,ry in legs:
            t=(1-z)/(1-.535) if z>=.535 else (.535-z)/(.535-.105)
            c=hip.lerp(knee,t) if z>=.535 else knee.lerp(ankle,t)
            c.z=z
            if female and z>.60:rx*=1.12;ry*=1.07
            if z>.82:w=blend('pelvis','thigh'+suffix,(.945-z)/.12)
            elif z>.575:w={'thigh'+suffix:1}
            elif z>.49:w=blend('thigh'+suffix,'calf'+suffix,(.575-z)/.085)
            elif z>.155:w={'calf'+suffix:1}
            else:w=blend('calf'+suffix,'foot'+suffix,(.155-z)/.075)
            c.x*=sign
            rr=g.ring(c,(1,0,0),(0,1,0),rx,ry,20,w);rr=g.match(last,rr);g.bridge(last,rr);last=rr
        # Foot is a bent continuation of ankle, not an intersecting shoe primitive.
        fs=.93 if female else 1
        foot_specs=[(.068,-.008,.035,.055),(.038,-.038,.041,.095),(.025,-.075,.046,.130),(.010,-.079,.046,.135),(0,-.079,.042,.131)]
        for z,y,rx,ry in foot_specs:
            rr=[]
            for j in range(20):
                a=j*math.tau/20;xx=(.11+rx*math.cos(a))*sign;yy=(y+ry*math.sin(a))*fs
                w=blend('foot'+suffix,'toes'+suffix,(-yy-.11)/.07)
                rr.append(g.point((xx,yy,z),w))
            rr=g.match(last,rr);g.bridge(last,rr);last=rr
        g.cap(last,{'foot'+suffix:1})
    # Single watertight body; remove unused interior vertices of the shoulder holes.
    mesh=bpy.data.meshes.new(kind+'_Body_QuadCage');mesh.from_pydata([(x*h,y*h,z*h) for x,y,z in g.v],[],g.f);mesh.update()
    obj=bpy.data.objects.new(kind+'_Body',mesh);col.objects.link(obj)
    arm=bpy.data.armatures.new(kind+'_BH01_Skeleton');rig=bpy.data.objects.new(kind+'_Rig',arm);col.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for n,(a,b,p) in bones.items():
        eb=arm.edit_bones.new(n);eb.head=a*h;eb.tail=b*h
        if p:eb.parent=arm.edit_bones[p];eb.use_connect=(eb.head-eb.parent.tail).length<1e-6
        eb.align_roll(Vector((0,1,0)))
        eb.use_deform=True
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;arm.display_type='OCTAHEDRAL'
    # A few local averaging passes remove hard region boundaries at shoulder ports,
    # crotch and wrist. Still ordinary editable vertex groups; at most four weights.
    neighbors=[set() for _ in g.v]
    for face in g.f:
        for a,b in zip(face,face[1:]+face[:1]):neighbors[a].add(b);neighbors[b].add(a)
    for _ in range(5):
        new=[]
        for i,w in enumerate(g.w):
            ns=neighbors[i]
            if not ns:new.append(w);continue
            out={k:v*.65 for k,v in w.items()}
            for j in ns:
                for k,v in g.w[j].items():out[k]=out.get(k,0)+.35*v/len(ns)
            ranked=sorted(out.items(),key=lambda p:p[1],reverse=True)[:4];total=sum(v for k,v in ranked)
            new.append({k:v/total for k,v in ranked if v/total>1e-8})
        g.w=new
    for bn in bones:
        group=obj.vertex_groups.new(name=bn)
        for i,w in enumerate(g.w):
            if bn in w:group.add([i],w[bn],'REPLACE')
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for p in mesh.polygons:p.use_smooth=True
    # Subdivision before armature keeps source cage editable and exported weights smooth.
    sub=obj.modifiers.new('Editable surface refinement','SUBSURF');sub.levels=1;sub.render_levels=1
    deform=obj.modifiers.new('BH01 linear skin - glTF parity','ARMATURE');deform.object=rig;deform.use_deform_preserve_volume=False
    obj.parent=rig
    obj.data.materials.append(material('M_Base_'+kind,(.42,.44,.46) if not female else (.47,.445,.415)))
    obj['edit_note']='Real mesh cage. Tab Edit Mode; one subdivision level then linear armature. No geometry nodes.'
    rig['standard']='BH_01';rig['height_m']=round(1.8*h,3);rig['forward']='-Y Blender / +Z glTF model front'
    rig['pose_note']='FK deform bones only. Clear transforms to return to neutral A-pose. No Actions.'
    for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.lock_scale=(True,True,True)
    for name in ['Core','Arm.L','Arm.R','Leg.L','Leg.R','Fingers.L','Fingers.R']:
        bc=arm.collections.new(name)
        for b in arm.bones:
            finger=any(b.name.startswith(f) for f in ['thumb','index','middle','ring','pinky'])
            target=('Fingers.'+b.name[-1]) if finger else (('Leg.'+b.name[-1]) if b.name.startswith(('thigh','calf','foot','toes')) else (('Arm.'+b.name[-1]) if b.name.endswith(('.L','.R')) else 'Core'))
            if target==name:bc.assign(b)
    rig.location.x=-.68 if not female else .68
    return obj,rig

male=build('Male');female=build('Female',True)
for o in bpy.context.selected_objects:o.select_set(False)
male[1].select_set(True);bpy.context.view_layer.objects.active=male[1]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active;s.shading.type='SOLID';s.shading.color_type='MATERIAL';s.shading.light='STUDIO'
            s.overlay.show_floor=True;s.region_3d.view_perspective='ORTHO';s.region_3d.view_distance=3.9
            s.region_3d.view_location=(0,0,.95);s.region_3d.view_rotation=Vector((.2,-1,.10)).to_track_quat('Z','Y')
for folder in ['Source','Exports','Review']: (BASE/folder).mkdir(parents=True,exist_ok=True)
text=bpy.data.texts.new('README_Humanoid_Base')
text.write('BH_01 original mannequin source\nTwo editable, continuous quad cages and two identical 53-bone hierarchies.\nBlender meters, +Z up, -Y front. Display offsets: +/- 0.68m; export resets rig location.\nSubdivision 1 BEFORE linear armature for matching glTF skinning.\nAll bones FK; .L and .R are character sides. No facial rig, IK, Actions or NLA.\nEdit cages manually; generator is only an optional authoring recipe.\nSee ../README.md and ../Review/ for tests and known rough areas.\n')
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE),check_existing=False)
print('HUMANOID_BASE_BUILT',str(SOURCE))
