"""Refresh only owned metric overlays from the recorded current-runtime snapshot."""
import bpy
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend'
if Path(bpy.data.filepath).resolve()!=SOURCE.resolve():
    raise RuntimeError('Wrong source; metric update refused.')
data=json.loads((ROOT/'Docs/Reviews/LevelFreestyle01/metrics_snapshot.json').read_text(encoding='utf-8'))
OWNER='freestyle_current_metrics_20260920'
for obj in list(bpy.data.objects):
    if obj.get('metric_owner')==OWNER:
        bpy.data.objects.remove(obj,do_unlink=True)
cols={name:bpy.data.collections[name] for name in ('DEV_METRICS','GRAPPLE_GUIDES')}

def mat(name,rgb):
    result=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    result.diffuse_color=(*rgb,1)
    return result
jumpmat=mat('M_Freestyle_JumpArc',(.15,.7,.85))
wallmat=mat('M_Freestyle_WallArc',(.95,.45,.15))
grapplemat=mat('M_Freestyle_GrappleArc',(.55,.7,.2))
def own(obj,col):
    obj['metric_owner']=OWNER
    obj['snapshot']='2026-09-20; physical InputEvents; first IsOnFloor; not guaranteed maximum'
    cols[col].objects.link(obj)
    return obj
def curve(name,points,material,col='DEV_METRICS',width=.065):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.bevel_depth=width;c.bevel_resolution=1
    spline=c.splines.new('POLY');spline.points.add(len(points)-1)
    for p,co in zip(spline.points,points):p.co=(*co,1)
    c.materials.append(material)
    return own(bpy.data.objects.new(name+'-noimp',c),col)
def text(name,xyz,material,col='DEV_METRICS',size=.6):
    c=bpy.data.curves.new(name,'FONT');c.body=name;c.size=size;c.materials.append(material)
    obj=own(bpy.data.objects.new(name+'-noimp',c),col);obj.location=xyz
    return obj
labels={'standing':'REST + W','running':'RUN JUMP','double':'RUN + AIR JUMP',
    'slide_jump':'SLIDE JUMP','wallrun_left':'WALLRUN (SHIFT)',
    'wall_jump':'WALL + JUMP','wall_air_jump':'WALL + JUMP + AIR'}
for i,(key,title) in enumerate(labels.items()):
    m=data['measurements'][key]
    base=(-91,32-i*9,.08)
    samples=m['samples'];start=samples[0]['position']
    points=[(base[0]-(s['position'][2]-start[2]),base[1]-(s['position'][0]-start[0]),
             base[2]+s['position'][1]-start[1]) for s in samples]
    color=wallmat if key.startswith('wall') else jumpmat
    curve(key,points,color)
    end=points[-1]
    curve(key+'_ground',[(base[0],base[1],.05),(end[0],end[1],.05)],color,width=.025)
    curve(key+'_landing',[(end[0],end[1]-.6,.1),(end[0],end[1]+.6,.1)],color)
    text(f'{title}  {m["range_m"]:.2f}m / +{m["rise_m"]:.2f}m',(base[0],base[1]-1.7,.1),color,size=.55)
text('MEASURED 20 SEP 2026 | sample trajectories, not guarantees',(-91,39,.08),jumpmat,size=.8)
text('Safe gap starts: rest 5m | run 6m | double 16-18m | slide 10-11m',(-91,36,.08),jumpmat,size=.55)
for i,distance in enumerate((15,30,45)):
    m=data['measurements']['grapple_'+str(distance)]
    samples=m['samples'];start=samples[0]['position'];base=(-85,65+i*10,.08)
    points=[(base[0]-(s['position'][2]-start[2]),base[1]-(s['position'][0]-start[0]),
             base[2]+s['position'][1]-start[1]) for s in samples]
    curve('Grapple_'+str(distance),points,grapplemat,'GRAPPLE_GUIDES')
    text(f'GRAPPLE {distance}m horiz / +10m anchor -> landing {m["landing_range_m"]:.1f}m',
         (base[0],base[1]-2,.08),grapplemat,'GRAPPLE_GUIDES',.55)
    if m['launch_position']:
        p=m['launch_position']
        marker=(base[0]-(p[2]-start[2]),base[1]-(p[0]-start[0]),base[2]+p[1]-start[1])
        curve('Exit_'+str(distance),[(marker[0],marker[1]-1,marker[2]),(marker[0],marker[1]+1,marker[2])],grapplemat,'GRAPPLE_GUIDES',.1)
        text('EXIT ~40m/s',(marker[0],marker[1],marker[2]+.5),grapplemat,'GRAPPLE_GUIDES',.5)
text('ACQUISITION: <=50m from camera + aim + LOS | stations 15 / 30 / 45m',(-85,97,.08),grapplemat,'GRAPPLE_GUIDES',.65)
config=data['config']
for i,(title,speed) in enumerate((('RUN',config['MoveSpeed']),('AIR REDIRECT',config['DoubleJumpRedirectSpeed']),('WALLRUN',config['WallRunSpeed']),('SLIDE JUMP CAP',config['SlideJumpMaxHorizontalSpeed']),('SLIDE ENTRY',config['SlideInitialSpeed']),('PULL CAP',config['MaxPullSpeed']))):
    x,y=-35,-60-i*4
    curve('Speed_'+title,[(x,y,.08),(x+speed,y,.08)],jumpmat,width=.04)
    text(f'{title}: {speed:g}m/s',(x,y-1.1,.08),jumpmat,size=.5)
text('CONFIGURED SPEED BANDS | bars = distance at constant speed for 1 second',(-35,-56,.08),jumpmat,size=.65)
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
print('FREESTYLE_METRIC_GUIDES',len([o for o in bpy.data.objects if o.get('metric_owner')==OWNER]))
