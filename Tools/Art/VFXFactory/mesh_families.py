"""Compact solid-mesh archetypes sharing the analytic mesh player contract."""
import math
import numpy as np
from mesh_geometry import triangulate, blob, axis_quaternion, point_up


def tube(points, width, sides=4, taper=True):
    """A capped polygonal tube around a 3D path, independent of any camera."""
    points = np.asarray(points, dtype=float)
    vertices, uvs, faces = [], [], []
    for index, point in enumerate(points):
        tangent = points[min(index+1,len(points)-1)] - points[max(0,index-1)]
        tangent /= max(np.linalg.norm(tangent), 1e-9)
        axis = np.array([0.,1.,0.]) if abs(tangent[1]) < .95 else np.array([1.,0.,0.])
        normal = np.cross(tangent, axis); normal /= max(np.linalg.norm(normal), 1e-9)
        binormal = np.cross(tangent, normal)
        t=index/(len(points)-1)
        radius=width*(1-.87*t if taper else 1)
        for j in range(sides):
            a=j/sides*math.tau
            vertices.append(point+radius*(normal*math.cos(a)+binormal*math.sin(a)))
            uvs.append([t,j/sides])
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=a+sides;d=b+sides
            faces.extend([(a,b,c),(b,d,c)])
    for j in range(1,sides-1):
        faces.extend([(0,j+1,j),((len(points)-1)*sides,(len(points)-1)*sides+j,(len(points)-1)*sides+j+1)])
    return triangulate(vertices,faces,uvs)


def band(width, segments=32, height=.045):
    vertices,uvs,faces=[],[],[]
    for j in range(segments):
        a=j/segments*math.tau
        for k,(r,y) in enumerate(((1-width,-height),(1,-height),(1,height),(1-width,height))):
            vertices.append([math.cos(a)*r,y,math.sin(a)*r]);uvs.append([k/3,j/segments])
    for j in range(segments):
        for k in range(4):
            a=j*4+k;b=j*4+(k+1)%4;c=((j+1)%segments)*4+k;d=((j+1)%segments)*4+(k+1)%4
            faces.extend([(a,c,b),(b,c,d)])
    return triangulate(vertices,faces,uvs)


def chunk(rng, width, length):
    vertices=[]
    for x,y,z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)):
        vertices.append([x*width*rng.uniform(.65,1.3),y*length*.4*rng.uniform(.65,1.3),z*width*rng.uniform(.6,1.2)])
    return triangulate(vertices,[(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
                                 (3,7,6),(3,6,2),(0,4,7),(0,7,3),(1,2,6),(1,6,5)])


def generate_family(recipe):
    p,layers=recipe['parameters'],recipe['layers']; kind=recipe['effect']
    rng=np.random.default_rng(recipe['seed']);meshes={};parts=[]
    count=p['effect_count']; radius=p['effect_radius']; width=p['effect_width'];length=p['effect_length']
    segments=p['effect_segments'];life=p['effect_lifetime'];motion=p['effect_motion'];jitter=p['effect_jitter']
    subdivisions=0 if p['low_poly_amount']>.88 else 1 if p['low_poly_amount']>.35 else 2

    def add(name,layer,mesh,origin=(0,0,0),travel=(0,0,0),scale0=(1,1,1),scale1=(1,1,1),
            start=0,lifetime=None,speed=1,spin=0,rotation=(0,0,0,1),gravity=0,fade_start=.1):
        meshes[name]=mesh
        start=min(float(start),p['duration']-.02)
        duration=max(.01,min(float(life if lifetime is None else lifetime),p['duration']-start))
        parts.append(dict(name=name,layer=layer,mesh=name,origin=list(origin),travel=list(travel),scale0=list(scale0),
            scale1=list(scale1),start=start,life=duration,speed=speed,spin=spin,rotation=list(rotation),gravity=gravity,
            fade_start=fade_start,tint=float(rng.uniform(.05,.95))))

    def core(origin=(0,.3,0), size=.35, lifetime=.22):
        add('Core','core',blob(rng,subdivisions,.05,.2),origin=origin,scale0=(size*.25,)*3,
            scale1=(size,)*3,lifetime=lifetime,fade_start=0)

    def direction(up=False):
        v=rng.normal(size=3);v[1]=abs(v[1])+.1 if up else v[1]
        return v/np.linalg.norm(v)

    def rings(number=1,origin=(0,.08,0),rotation=(0,0,0,1),stretch=1):
        for i in range(number):
            r=radius*(1-i*.19)
            add(f'Band_{i:02}','ring',band(min(.8,width/r),24+int((1-p['low_poly_amount'])*24)),
                origin=origin,scale0=(r*.06,.25,r*.06),scale1=(r,stretch,r),rotation=rotation,
                start=i*p['effect_stagger'],lifetime=life,fade_start=.08)

    if kind=='SHOCK_RING':
        core(size=.4,lifetime=.22);rings(3)
        for i in range(count):
            a=i/count*math.tau+rng.uniform(-.02,.02)
            v=np.array([math.cos(a),.05,math.sin(a)])
            add(f'PressureTooth_{i:02}','shards',tube([[0,0,0],[0,.2,0],[0,.75,0]],width*.55),
                origin=(0,.08,0),travel=v*radius*.94,scale0=(.15,)*3,scale1=(1,1,1),
                rotation=point_up(v),lifetime=life*.75,start=.025,fade_start=.08)
    elif kind=='SPARK_BURST':
        core(size=.48)
        for i in range(count):
            v=direction();v[1]=abs(v[1])*.75;v/=np.linalg.norm(v)
            s=rng.uniform(.55,1.3)
            add(f'Spark_{i:02}','shards',tube([[0,0,0],[width*jitter, length*.3,0],[0,length,0]],width*.5),
                origin=(0,.45,0),travel=v*radius*s*motion,rotation=point_up(v),scale0=(.8,.25,.8),
                scale1=(1,s,1),lifetime=life*rng.uniform(.65,1.1),gravity=.12,fade_start=.15)
            if i%4==0:
                add(f'SparkTail_{i:02}','petals',tube([[0,0,0],[.15*jitter,length*.4,.08*jitter],[0,length*1.6,0]],width*.22),
                    origin=(0,.45,0),travel=v*radius*s*.72*motion,rotation=point_up(v),lifetime=life*.7,start=.025)
    elif kind=='DIRECTIONAL_LIGHTNING':
        origin=np.array([0.,.25,0.]);core(origin=origin,size=.65,lifetime=.3)
        points=[]
        for j in range(segments+1):
            t=j/segments;spread=math.sin(math.pi*t)*jitter
            points.append([rng.uniform(-spread,spread),length*(1-t),rng.uniform(-spread,spread)])
        add('MainStrike','petals',tube(points,width,taper=False),origin=origin,lifetime=life,fade_start=.1)
        for i in range(count):
            index=1+i*(segments-2)//count;anchor=np.asarray(points[index])
            sign=-1 if i%2 else 1;reach=rng.uniform(.4,1.3)
            fork=[anchor,anchor+np.array([reach*.35*sign,-reach*.4,.18*jitter]),
                  anchor+np.array([reach*.8*sign,-reach*.6,-.2*jitter]),anchor+np.array([reach*sign,-reach,-.12])]
            add(f'Fork_{i:02}','shards',tube(fork,width*.5),origin=origin,start=(i%3)*p['effect_stagger'],lifetime=life*.8)
        # Two temporal restrikes vary topology rather than a shader flicker.
        for i in range(2):
            alt=np.asarray(points).copy();alt[:,0]+=rng.uniform(-jitter*.25,jitter*.25,len(alt))
            add(f'Restrike_{i:02}','petals',tube(alt,width*.45),origin=origin,start=.12+i*.17,lifetime=life*.28)
        saved=radius;radius=min(radius,1.1);rings();radius=saved
    elif kind=='ARC_CLUSTER':
        core(origin=(0,.5,0),size=.4,lifetime=life)
        for i in range(count):
            a=i/count*math.tau+rng.uniform(-.12,.12)
            endpoint=np.array([math.cos(a)*radius,.12,math.sin(a)*radius]);points=[]
            for j in range(segments+1):
                t=j/segments;v=endpoint*t+np.array([0,.5*(1-t)+math.sin(math.pi*t)*p['effect_arc'],0])
                if 0<j<segments:v+=rng.normal(size=3)*jitter*.16
                points.append(v)
            add(f'Arc_{i:02}','petals',tube(points,width),start=(i%3)*p['effect_stagger'],lifetime=life)
            add(f'Terminal_{i:02}','shards',blob(rng,0,.1),origin=endpoint,scale0=(.03,)*3,
                scale1=(width*3,)*3,start=(i%3)*p['effect_stagger'],lifetime=life*.8)
    elif kind=='LASER_IMPACT':
        center=(0,1.15,0);core(center,.62,.25)
        add('IncomingBeam','petals',tube([[0,0,length],[0,0,length*.35],[0,0,0]],width,taper=False),
            origin=center,lifetime=life*.55,scale0=(.4,.4,1),fade_start=0)
        rings(2,center,axis_quaternion([1,0,0],math.pi*.5),.5)
        for i in range(count):
            a=i/count*math.tau;v=np.array([math.cos(a),math.sin(a),rng.uniform(-.15,.15)])
            size=radius*(1.2 if i%2==0 else .65)
            add(f'FlareRay_{i:02}','shards',tube([[0,0,0],[0,size*.25,0],[0,size,0]],width*.45),
                origin=center,rotation=point_up(v),scale0=(.15,)*3,lifetime=life*rng.uniform(.55,1),fade_start=.03)
    elif kind=='PROJECTILE_TRAIL':
        center=np.array([0.,1.1,0.]);core(center,.27,life)
        for i in range(3):
            points=[];phase=i/3*math.tau
            for j in range(segments+1):
                t=j/segments;envelope=math.sin(math.pi*t)*radius
                points.append([math.cos(phase+t*2)*envelope*.45,math.sin(phase+t*2)*envelope*.45+p['effect_arc']*t*t,
                               -length*t+rng.uniform(-.05,.05)*jitter])
            add(f'TrailFilament_{i:02}','petals',tube(points,width*(1-i*.2)),origin=center,
                travel=(0,0,length*.25*motion),lifetime=life,scale0=(.1,.1,.6),fade_start=.28)
        for i in range(count):
            t=(i+1)/(count+1);size=width*2*(1-t)+.02
            add(f'WakeBead_{i:02}','shards',blob(rng,0,.12),origin=center+np.array([rng.uniform(-1,1)*radius*.22,
                p['effect_arc']*t*t,-length*t]),travel=(0,.15,-.3*motion),scale0=(size,)*3,scale1=(size*.2,)*3,
                start=t*.2,lifetime=life*(1-.5*t),fade_start=.18)
    elif kind=='ENERGY_ORB':
        center=(0,1.35,0);core(center,p['core_size'],min(life,p['core_lifetime']+.5))
        for i,axis in enumerate(([1,0,0],[0,0,1],[1,0,1])):
            r=radius*(.65+i*.12)
            add(f'OrbitalBand_{i:02}','ring',band(min(.7,width/r),32,.016),origin=center,
                scale0=(r*.3,)*3,scale1=(r,)*3,rotation=axis_quaternion(axis,math.pi*(.22+i*.19)),
                spin=.5*(i-1),lifetime=life,fade_start=.3)
        for i in range(count):
            v=direction();size=rng.uniform(.06,.16)
            add(f'Satellite_{i:02}','shards',blob(rng,0,.1,.25),origin=center,travel=v*radius*motion,
                scale0=(size*.15,)*3,scale1=(size,)*3,lifetime=life*rng.uniform(.7,1),spin=rng.uniform(-2,2),fade_start=.3)
    elif kind=='SMOKE_BURST':
        for i in range(count):
            a=i/count*math.tau;spread=radius*rng.uniform(.1,.65);size=p['smoke_puff_size']*rng.uniform(.6,1.3)
            add(f'SmokeLobe_{i:02}','smoke',blob(rng,subdivisions,.12+p['chunkiness']*.12),
                origin=(math.cos(a)*spread,.25+rng.uniform(0,.4),math.sin(a)*spread),
                travel=(math.cos(a)*radius*.35*motion,p['effect_arc']*rng.uniform(.45,1)*motion,math.sin(a)*radius*.35*motion),
                scale0=(size*.18,)*3,scale1=(size*1.45,size*1.2,size*1.45),start=(i%5)*p['effect_stagger']*.4,
                lifetime=life,spin=rng.uniform(-.6,.6),rotation=axis_quaternion(direction(),rng.uniform(0,math.tau)),fade_start=.35)
        for i in range(6):
            a=i/6*math.tau;add(f'DustSkirt_{i:02}','dust',blob(rng,subdivisions,.16),origin=(0,.08,0),
                travel=(math.cos(a)*radius*.8,.04,math.sin(a)*radius*.8),scale0=(.1,.03,.1),scale1=(.85,.16,.85),lifetime=life*.7)
    elif kind=='DEBRIS_SCATTER':
        for i in range(count):
            v=direction(True);v[1]=rng.uniform(.4,1)
            travel=np.array([v[0]*radius*motion,v[1]*p['effect_arc'],v[2]*radius*motion]);size=rng.uniform(.5,1.3)
            add(f'MetalChunk_{i:02}','shards',chunk(rng,width,length),origin=(0,.3,0),travel=travel,
                scale0=(size*.4,)*3,scale1=(size,)*3,lifetime=life*rng.uniform(.75,1),
                rotation=axis_quaternion(direction(),rng.uniform(0,math.tau)),spin=rng.uniform(-7,7),gravity=p['effect_arc']*.9,fade_start=.65)
            if i%2==0:
                add(f'HotFragment_{i:02}','petals',tube([[0,0,0],[0,length*.4,0]],width*.18),origin=(0,.3,0),
                    travel=travel*1.2,rotation=point_up(travel),lifetime=life*.65,gravity=p['effect_arc']*.55)
        for i in range(4):
            a=i/4*math.tau;add(f'ImpactDust_{i:02}','dust',blob(rng,0,.2),origin=(0,.08,0),
                travel=(math.cos(a)*radius*.4,.08,math.sin(a)*radius*.4),scale0=(.05,)*3,scale1=(.6,.22,.6),lifetime=life*.8)
    else:
        raise ValueError('Unsupported effect family: '+kind)
    active=[part for part in parts if layers[part['layer']]['enabled']]
    return dict(recipe=recipe,meshes=meshes,parts=parts,duration=p['duration'],
        stats=dict(mesh_count=len(active),triangle_count=sum(len(meshes[part['mesh']]['positions'])//9 for part in active)),
        coordinate_system='right-handed, Y-up, metres; trail local -Z, laser incoming +Z, lightning from +Y',
        animation='analytic life curves, no billboards')
