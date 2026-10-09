"""Independent closed-volume winding check, including exact planar-boundary samples."""
import bpy,bmesh,math
from mathutils.bvhtree import BVHTree


def check(q,obj,source):
    cleanhost=q.host(source,3);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    ce=cleanhost.evaluated_get(dg);cm=ce.to_mesh();cm.calc_loop_triangles()
    triangles=[[tuple(cm.vertices[i].co) for i in t.vertices] for t in cm.loop_triangles]
    bm=bmesh.new();bm.from_mesh(cm);bv=BVHTree.FromBMesh(bm,epsilon=0)
    cleanmesh=bpy.data.meshes.new_from_object(ce);ce.to_mesh_clear()
    env=bpy.data.objects.new(q.PREFIX+'Envelope',cleanmesh);q.collection().objects.link(env)
    dot=lambda a,b:sum(a[i]*b[i] for i in range(3))
    sub=lambda a,b:[a[i]-b[i] for i in range(3)]
    cross=lambda a,b:[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
    prepared=[]
    for a,b,c in triangles:
        u=sub(b,a);v=sub(c,a);n=cross(u,v);nn=dot(n,n)
        if nn<1e-20:continue
        uu=dot(u,u);uv=dot(u,v);vv=dot(v,v);prepared.append((a,u,v,n,nn,uu,uv,vv,uu*vv-uv*uv))
    def inside(p):
        nearest=bv.find_nearest(p)
        if nearest[0] is not None and nearest[3]<.0003:return True
        # Blender float BVH nearest points can drift on a 480 m face.
        # Plane distance + barycentric test in Python doubles resolves boundary.
        for a,u,v,n,nn,uu,uv,vv,den in prepared:
            w=sub(p,a);wn=dot(w,n)
            if wn*wn>nn*.0003**2 or abs(den)<1e-20:continue
            wu=dot(w,u);wv=dot(w,v);b=(wu*vv-wv*uv)/den;c=(wv*uu-wu*uv)/den
            if b>=-1e-7 and c>=-1e-7 and b+c<=1.0000001:return True
        angle=0.
        for tri in triangles:
            a,b,c=[sub(v,p) for v in tri];la,lb,lc=[math.sqrt(dot(v,v)) for v in [a,b,c]]
            angle+=2*math.atan2(dot(a,cross(b,c)),la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb)
        return abs(angle)>2*math.pi
    e=obj.evaluated_get(dg);m=e.to_mesh();m.calc_loop_triangles();samples=[v.co.copy() for v in m.vertices]
    for tri in m.loop_triangles:
        a,b,c=[m.vertices[i].co for i in tri.vertices];samples.extend([(a+b+c)/3,a*.6+b*.2+c*.2,a*.2+b*.6+c*.2,a*.2+b*.2+c*.6])
    outside=[list(p) for p in samples if not inside(p)]
    mesh=bpy.data.meshes.new_from_object(e);e.to_mesh_clear();temp=bpy.data.objects.new(q.PREFIX+'Difference',mesh);q.collection().objects.link(temp)
    mod=temp.modifiers.new('Independent Exact Difference','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=env;mod.use_self=True;mod.use_hole_tolerant=True
    bpy.context.view_layer.update();e=temp.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();diff=bmesh.new();diff.from_mesh(m)
    volume=abs(diff.calc_volume(signed=True));area=sum(f.calc_area() for f in diff.faces);exterior=sum(not inside(v.co) for v in m.vertices)
    # Absolute residual volume scales with large coplanar faces. Compare the
    # residual's equivalent thickness to the same geometric boundary tolerance.
    thickness=2*volume/max(area,1e-12)
    residual_samples=sum(not inside(p.center) for p in m.polygons)
    result={'method':'double winding + double planar-boundary test + independent Exact Difference','tolerance_m':.0003,'samples':len(samples),'outside_samples':len(outside),'first_outside':outside[:3],'difference_vertices':len(m.vertices),'difference_faces':len(m.polygons),'difference_volume':volume,'difference_area':area,'difference_equivalent_thickness_m':thickness,'difference_exterior_vertices':exterior,'difference_exterior_face_centers':residual_samples,'pass':not outside and not exterior and not residual_samples and thickness<.0003}
    diff.free();e.to_mesh_clear();bm.free()
    for o in [temp,env,cleanhost]:
        data=o.data;bpy.data.objects.remove(o,do_unlink=True)
        if not data.users:bpy.data.meshes.remove(data)
    return result
