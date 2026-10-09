"""Small deterministic recipe-library thumbnail, projected from generated triangles.

This CPU illustration is a navigation aid. Godot/Three.js remain render truth.
"""
import math
import numpy as np
from PIL import Image, ImageDraw


def rotation(q):
    x,y,z,w=q
    return np.array([[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],
                     [2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],
                     [2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]])


def thumbnail(data, time, size=(320,220)):
    p=data['recipe']['parameters'];triangles=[]
    right=np.array([.83,0,-.56]);up=np.array([-.18,.946,-.27]);forward=np.cross(right,up)
    for d in data['parts']:
        layer=data['recipe']['layers'][d['layer']];u=(time-d['start'])/d['life']
        if not layer['enabled'] or u<0 or u>=1:continue
        growth=(1-math.exp(-4*d['speed']*u))/(1-math.exp(-4*d['speed']))
        scale=np.array(d['scale0'])*(1-growth)+np.array(d['scale1'])*growth
        angle=d['spin']*u;spin=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
        xyz=np.asarray(data['meshes'][d['mesh']]['positions']).reshape(-1,3)*scale
        xyz=xyz@(rotation(d['rotation'])@spin).T+np.array(d['origin'])+np.array(d['travel'])*growth
        xyz[:,1]-=d['gravity']*u*u
        points=np.column_stack((xyz@right,-xyz@up));depth=xyz@forward
        fade=np.clip((u-d['fade_start'])/(1-d['fade_start']),0,1)
        if layer['fade_curve']=='SMOOTH':fade=fade*fade*(3-2*fade)
        elif layer['fade_curve']=='EASE_OUT':fade=1-(1-fade)**2
        alpha=layer['opacity']*(1-fade)
        a=np.array([int(layer['color'][j:j+2],16) for j in (1,3,5)])
        b=np.array([int(layer['color_b'][j:j+2],16) for j in (1,3,5)])
        base=a*.65+b*.35
        if d['layer']=='smoke':base*=1-p['smoke_darkness']*.7
        for i in range(0,len(xyz),3):
            v=xyz[i:i+3];normal=np.cross(v[1]-v[0],v[2]-v[0]);normal/=max(np.linalg.norm(normal),1e-9)
            lighting=1 if layer['unshaded'] else .45+.55*abs(np.dot(normal,np.array([-.4,.85,.5])))
            color=np.clip(base*(lighting+layer['emission']*.3),0,255)
            # Opaque drawing uses the known dark background for compact readable cards.
            color=color*alpha+np.array([14,24,30])*(1-alpha)
            triangles.append((float(depth[i:i+3].mean()),points[i:i+3],tuple(color.astype(int))))
    image=Image.new('RGB',size,(14,24,30));draw=ImageDraw.Draw(image)
    if not triangles:return image
    all_points=np.concatenate([v[1] for v in triangles]);minimum=all_points.min(axis=0);maximum=all_points.max(axis=0)
    center=(minimum+maximum)/2;scale=min((size[0]-32)/max(maximum[0]-minimum[0],.1),(size[1]-26)/max(maximum[1]-minimum[1],.1))
    for _,points,color in sorted(triangles,key=lambda t:t[0]):
        projected=(points-center)*scale+np.array(size)/2
        draw.polygon([tuple(row) for row in projected],fill=color)
    return image
