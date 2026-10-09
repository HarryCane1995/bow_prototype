"""Recipe-authored triangle meshes; no billboards, simulation or camera-dependent vertices."""
import math
import numpy as np


def axis_quaternion(axis, angle):
    axis = np.asarray(axis, dtype=float); axis /= max(np.linalg.norm(axis), 1e-8)
    return [*(axis * math.sin(angle / 2)), math.cos(angle / 2)]


def point_up(direction):
    v = np.asarray(direction, dtype=float); v /= np.linalg.norm(v)
    if v[1] < -.999999:
        return [1, 0, 0, 0]
    q = np.array([v[2], 0, -v[0], 1 + v[1]])
    return (q / np.linalg.norm(q)).tolist()


def triangulate(vertices, faces, uvs=None):
    positions, normals, texcoords = [], [], []
    v = np.asarray(vertices, dtype=float)
    for face in faces:
        a, b, c = v[list(face)]
        normal = np.cross(b-a, c-a); length = np.linalg.norm(normal)
        if length < 1e-9:
            continue
        normal /= length
        for i in face:
            positions.extend(v[i]); normals.extend(normal)
            texcoords.extend(uvs[i] if uvs is not None else [float(np.clip(v[i][1] * .5 + .5, 0, 1)), 0])
    return {key: np.round(values, 6).tolist() for key, values in
            [('positions', positions), ('normals', normals), ('uvs', texcoords)]}


def blob(rng, subdivisions, irregularity, star=0):
    phi = (1 + math.sqrt(5)) / 2
    vertices = [(-1,phi,0),(1,phi,0),(-1,-phi,0),(1,-phi,0),(0,-1,phi),(0,1,phi),
                (0,-1,-phi),(0,1,-phi),(phi,0,-1),(phi,0,1),(-phi,0,-1),(-phi,0,1)]
    faces = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),
             (10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    vertices = [np.asarray(v)/np.linalg.norm(v) for v in vertices]
    for _ in range(subdivisions):
        cache = {}; new_faces = []
        def mid(a,b):
            key = tuple(sorted((a,b)))
            if key not in cache:
                x = vertices[a]+vertices[b]; x /= np.linalg.norm(x)
                cache[key] = len(vertices); vertices.append(x)
            return cache[key]
        for a,b,c in faces:
            ab,bc,ca = mid(a,b),mid(b,c),mid(c,a)
            new_faces.extend([(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)])
        faces = new_faces
    for i, vertex in enumerate(vertices):
        vertices[i] = vertex * (1 + rng.uniform(-1,1) * irregularity + (star if i % 3 == 0 else 0))
    return triangulate(vertices, faces)


def petal(p, rng):
    along = 3 + round((1-p['low_poly_amount']) * 6)
    across = 2 + 2 * round(1-p['low_poly_amount'])
    length = p['petal_length'] * (1 + rng.uniform(-.35,.35) * p['petal_irregularity'])
    width = p['petal_width'] * (1 + rng.uniform(-.45,.45) * p['petal_irregularity'])
    vertices, uv, faces = [], [], []
    for a in range(along+1):
        t = a/along
        spread = math.sin(math.pi * (t*.92+.035)) * width
        for b in range(across+1):
            s = b/across*2-1
            y = length * math.sin(t*math.pi*.78) * p['petal_curl'] * .65 + (1-s*s)*spread*.48
            z = length * (t - p['petal_curl']*.18*t*t)
            vertices.append([s*spread,y,z]); uv.append([t,(s+1)*.5])
    for a in range(along):
        for b in range(across):
            i=a*(across+1)+b; j=i+across+1
            faces.extend([(i,j,i+1),(i+1,j,j+1)])
    # A curved, double-sided shell with a real third dimension, rather than a quad.
    return triangulate(vertices,faces,uv)


def ring(p):
    segments = 16 + round((1-p['low_poly_amount'])*48)
    vertices,uv,faces=[],[],[]
    for j in range(segments):
        a=j/segments*math.tau
        for edge,r in enumerate([max(.05,1-p['ring_thickness']/p['ring_radius']),1]):
            vertices.append([math.cos(a)*r,0,math.sin(a)*r]);uv.append([edge,j/segments])
    for j in range(segments):
        i=j*2;next_i=((j+1)%segments)*2
        faces.extend([(i,i+1,next_i),(i+1,next_i+1,next_i)])
    return triangulate(vertices,faces,uv)


def spike(p):
    w=.055 + p['chunkiness']*.08
    return triangulate([[-w,0,-w],[w,0,-w],[0,0,w],[0,p['shard_length']*(1+p['silhouette_exaggeration']*.5),0]],
                       [(0,2,1),(0,1,3),(1,2,3),(2,0,3)])


def generate_explosion(recipe):
    p, layers = recipe['parameters'], recipe['layers']
    rng = np.random.default_rng(recipe['seed'])
    meshes, parts = {}, []
    subdivisions = 0 if p['low_poly_amount'] > .88 else 1 if p['low_poly_amount'] > .35 else 2
    def add(name,layer,mesh,origin=(0,0,0),travel=(0,0,0),scale0=(.1,.1,.1),scale1=(1,1,1),
            start=0,life=.8,speed=1,spin=0,rotation=(0,0,0,1),gravity=0,fade_start=.15):
        # Generate all descriptors even for disabled layers: toggles don't reshuffle seeds.
        meshes[name] = mesh
        life = max(.01, min(life, p['duration'] - start))
        parts.append(dict(name=name,layer=layer,mesh=name,origin=list(origin),travel=list(travel),
                          scale0=list(scale0),scale1=list(scale1),start=start,life=life,speed=speed,
                          spin=spin,rotation=list(rotation),gravity=gravity,fade_start=fade_start,
                          tint=float(rng.uniform(.05,.95))))
    core=p['core_size']
    add('Core','core',blob(rng,subdivisions,.04,.35*p['silhouette_exaggeration']),origin=(0,.65,0),
        scale0=(core*.25,)*3,scale1=(core*1.6,)*3,life=p['core_lifetime'],speed=2,spin=.5,fade_start=0)
    for i in range(p['petal_count']):
        angle=i/p['petal_count']*math.tau+rng.uniform(-.25,.25)*p['petal_irregularity']
        direction=np.array([math.sin(angle),0,math.cos(angle)])
        stretch=1+rng.uniform(-.18,.18)*p['petal_irregularity']
        add(f'Petal_{i:02}','petals',petal(p,rng),origin=(0,.18,0),travel=direction*p['petal_spread'],
            scale0=(.08,)*3,scale1=(stretch,stretch,stretch),rotation=axis_quaternion([0,1,0],angle),
            start=float(rng.uniform(0,.045)),life=p['petal_lifetime'],speed=1.3,spin=float(rng.uniform(-.4,.4)))
    r=p['ring_radius']
    add('ShockRing','ring',ring(p),origin=(0,p['ring_vertical_offset'],0),scale0=(.05,)*3,
        scale1=(r,1,r),life=min(1.05,p['duration']*.5),speed=p['ring_speed'],
        rotation=axis_quaternion([1,0,0],math.radians(p['ring_tilt'])),fade_start=.05)
    shard_mesh=spike(p)
    for i in range(p['shard_count']):
        angle=float(rng.uniform(0,math.tau));up=float(rng.uniform(.1,.9));r=math.sqrt(1-up*up)
        direction=np.array([math.cos(angle)*r,up,math.sin(angle)*r])
        s=float(rng.uniform(.5,1.25))
        add(f'Shard_{i:02}','shards',shard_mesh,origin=(0,.45,0),travel=direction*p['shard_spread'],
            scale0=(s,s*.2,s),scale1=(s,s,s),start=.035,life=.65,speed=p['shard_speed'],
            rotation=point_up(direction),spin=float(rng.uniform(-2,2)),gravity=.65,fade_start=.25)
    for i in range(p['smoke_count']):
        angle=float(rng.uniform(0,math.tau));radius=float(rng.uniform(.2,.85));size=p['smoke_puff_size']*float(rng.uniform(.7,1.25))
        start=min(p['smoke_delay']+float(rng.uniform(0,.16)),p['duration']*.55)
        add(f'Smoke_{i:02}','smoke',blob(rng,subdivisions,.13+p['chunkiness']*.12),
            origin=(math.sin(angle)*radius,.4+float(rng.uniform(0,.65)),math.cos(angle)*radius),
            travel=(math.sin(angle)*.8,1.0+float(rng.uniform(0,.8)),math.cos(angle)*.8),
            scale0=(size*.35,)*3,scale1=(size*1.4,size*1.2,size*1.4),start=start,life=p['smoke_linger'],
            speed=p['smoke_expansion_speed'],spin=float(rng.uniform(-.4,.4)),fade_start=.3,
            rotation=axis_quaternion([1,1,1],float(rng.uniform(0,math.tau))))
    for i in range(7):
        angle=i/7*math.tau
        add(f'Dust_{i:02}','dust',blob(rng,subdivisions,.15),origin=(0,.15,0),
            travel=(math.cos(angle)*p['dust_spread'],.1,math.sin(angle)*p['dust_spread']),
            scale0=(.1,.05,.1),scale1=(.85,.24,.85),start=.08,life=min(p['duration']*.8,1.5),speed=.7,fade_start=.1)
    enabled = [part for part in parts if layers[part['layer']]['enabled']]
    return dict(recipe=recipe,meshes=meshes,parts=parts,duration=p['duration'],
                stats=dict(mesh_count=len(enabled),triangle_count=sum(len(meshes[part['mesh']]['positions'])//9 for part in enabled)),
                coordinate_system='right-handed, Y-up, metres', animation='analytic life curves, no billboards')


def generate(recipe):
    if recipe['effect'] == 'MESH_EXPLOSION_3D':
        return generate_explosion(recipe)
    from mesh_families import generate_family
    return generate_family(recipe)


def write_obj(mesh,path):
    pos=np.asarray(mesh['positions']).reshape(-1,3);normal=np.asarray(mesh['normals']).reshape(-1,3);uv=np.asarray(mesh['uvs']).reshape(-1,2)
    lines=['# Procedural mesh VFX source: recipe + mesh_geometry.py; no Blender source.']
    lines += ['v '+' '.join(f'{v:.6f}' for v in row) for row in pos]
    lines += ['vt '+' '.join(f'{v:.6f}' for v in row) for row in uv]
    lines += ['vn '+' '.join(f'{v:.6f}' for v in row) for row in normal]
    lines += ['f '+' '.join(f'{j}/{j}/{j}' for j in range(i+1,i+4)) for i in range(0,len(pos),3)]
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
