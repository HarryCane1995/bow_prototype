"""Local deterministic signage. Recipes + original pixel lettering; no brands or downloaded art."""
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'ArtPass'))
from storage import guard

VERSION='1.0'
PALETTES={
 'COLD_SERVICE':{'neon':'#69e5da','accent':'#ffc36b','back':'#17272c','ink':'#b9ceca'},
 'AMBER_WARNING':{'neon':'#ffd477','accent':'#ed6942','back':'#29271e','ink':'#ded9b7'},
 'NIGHT_MARKET':{'neon':'#ff7c91','accent':'#79d9ef','back':'#281e2e','ink':'#e0c6cd'},
 'CORPORATE_ICE':{'neon':'#b0dbea','accent':'#71b4ce','back':'#18232e','ink':'#c6ced4'},
 'REACTOR_LIME':{'neon':'#bdda79','accent':'#ecc585','back':'#252c20','ink':'#cbd7b5'},
}
CONTROLS={
 'aspect':[.25,5,.05,2,'Width / height'], 'density':[.1,1,.05,.55,'Glyph density'],
 'emission_strength':[0,6,.1,2,'Emission strength'], 'wear':[0,1,.02,.12,'Localized wear'],
 'grime':[0,1,.02,.12,'Grime overlay'], 'border':[0,1,.02,.7,'Frame width'],
 'glyph_scale':[.5,1.5,.05,1,'Primary glyph scale'],
}
ARCHETYPES={
 'VERTICAL_NEON':('Vertical neon',.35,'NIGHT_MARKET','glyph'),
 'HORIZONTAL_BILLBOARD':('Transit billboard',3.1,'COLD_SERVICE','transit'),
 'SERVICE_STRIP':('Service strip',4.4,'COLD_SERVICE','service'),
 'WARNING_PANEL':('Industrial warning',1.35,'AMBER_WARNING','warning'),
 'PANEL_AD':('Abstract panel ad',1.5,'CORPORATE_ICE','ad'),
 'STACKED_SIGNAGE':('Stacked street signage',.65,'NIGHT_MARKET','stack'),
 'HOLOGRAM':('Scanline hologram',1.3,'COLD_SERVICE','holo'),
 'GLYPH_MONOLITH':('Pseudo-glyph monolith',.5,'REACTOR_LIME','glyph'),
 'NUMERIC_CODE':('Industrial numeric code',2.1,'AMBER_WARNING','code'),
 'CORPORATE_PANEL':('Clean corporate panel',2.4,'CORPORATE_ICE','corporate'),
 'DIRTY_LIGHTBOX':('Worn backlit panel',2.5,'REACTOR_LIME','lightbox'),
 'INACTIVE_BILLBOARD':('Inactive billboard',2.8,'CORPORATE_ICE','inactive'),
}
# Authored 5x7 bitmap alphabet, portable and deterministic on every host.
FONT={
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'C':['01111','10000','10000','10000','10000','10000','01111'],
'D':['11110','10001','10001','10001','10001','10001','11110'],
'E':['11111','10000','10000','11110','10000','10000','11111'],
'F':['11111','10000','10000','11110','10000','10000','10000'],
'G':['01111','10000','10000','10111','10001','10001','01111'],
'H':['10001','10001','10001','11111','10001','10001','10001'],
'I':['11111','00100','00100','00100','00100','00100','11111'],
'J':['00111','00010','00010','00010','10010','10010','01100'],
'K':['10001','10010','10100','11000','10100','10010','10001'],
'L':['10000','10000','10000','10000','10000','10000','11111'],
'M':['10001','11011','10101','10101','10001','10001','10001'],
'N':['10001','11001','10101','10011','10001','10001','10001'],
'O':['01110','10001','10001','10001','10001','10001','01110'],
'P':['11110','10001','10001','11110','10000','10000','10000'],
'Q':['01110','10001','10001','10001','10101','10010','01101'],
'R':['11110','10001','10001','11110','10100','10010','10001'],
'S':['01111','10000','10000','01110','00001','00001','11110'],
'T':['11111','00100','00100','00100','00100','00100','00100'],
'U':['10001','10001','10001','10001','10001','10001','01110'],
'V':['10001','10001','10001','10001','10001','01010','00100'],
'W':['10001','10001','10001','10101','10101','10101','01010'],
'X':['10001','10001','01010','00100','01010','10001','10001'],
'Y':['10001','10001','01010','00100','00100','00100','00100'],
'Z':['11111','00001','00010','00100','01000','10000','11111'],
'0':['01110','10001','10011','10101','11001','10001','01110'],
'1':['00100','01100','00100','00100','00100','00100','01110'],
'2':['01110','10001','00001','00010','00100','01000','11111'],
'3':['11110','00001','00001','01110','00001','00001','11110'],
'4':['00010','00110','01010','10010','11111','00010','00010'],
'5':['11111','10000','10000','11110','00001','00001','11110'],
'6':['01110','10000','10000','11110','10001','10001','01110'],
'7':['11111','00001','00010','00100','01000','01000','01000'],
'8':['01110','10001','10001','01110','10001','10001','01110'],
'9':['01110','10001','10001','01111','00001','00001','01110'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
'/':['00001','00001','00010','00100','01000','10000','10000'],
'.':['00000','00000','00000','00000','00000','00110','00110'],
' ':['00000']*7,
}

def fingerprint():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def preset(key,seed=99):
    _,aspect,palette,kind=ARCHETYPES[key]
    p={k:v[3] for k,v in CONTROLS.items()};p['aspect']=aspect
    if kind=='inactive':p.update(emission_strength=0,wear=.32,grime=.25)
    if kind=='lightbox':p.update(wear=.45,grime=.38)
    if kind=='corporate':p.update(wear=.03,grime=.02)
    return dict(schema='bow.billboard',version=1,generator_version=VERSION,archetype=key,seed=seed,
                palette=palette,colors=copy.deepcopy(PALETTES[palette]),parameters=p,
                support_frame=kind!='holo',hazard=kind=='warning')

def normalize(data):
    if not isinstance(data,dict):raise ValueError('Recipe must be an object')
    if data.get('schema','bow.billboard')!='bow.billboard' or data.get('version',1)!=1:raise ValueError('Unsupported billboard recipe')
    if data.get('generator_version',VERSION)!=VERSION:raise ValueError('Unsupported billboard generator version')
    key=data.get('archetype','HORIZONTAL_BILLBOARD')
    if key not in ARCHETYPES:raise ValueError('Unknown signage archetype')
    r=preset(key);seed=data.get('seed',99)
    if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<2**31:raise ValueError('Seed must be a nonnegative 31-bit integer')
    r['seed']=seed;palette=data.get('palette',r['palette'])
    if palette not in PALETTES:raise ValueError('Unknown palette')
    r['palette']=palette;r['colors']=dict(PALETTES[palette])
    colors=data.get('colors',{})
    if not isinstance(colors,dict) or set(colors)-set(r['colors']):raise ValueError('Unknown color role')
    for k,v in colors.items():
        if not isinstance(v,str) or not re.fullmatch('#[0-9a-fA-F]{6}',v):raise ValueError('Colors must be hex RGB')
        r['colors'][k]=v.lower()
    params=data.get('parameters',{})
    if not isinstance(params,dict) or set(params)-set(CONTROLS):raise ValueError('Unknown billboard parameter')
    for k,v in params.items():
        lo,hi,*_=CONTROLS[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'{k} must be in {lo}..{hi}')
        r['parameters'][k]=float(v)
    for k in ('support_frame','hazard'):
        if k in data:
            if not isinstance(data[k],bool):raise ValueError(k+' must be a boolean')
            r[k]=data[k]
    return r

def rgb(value):return tuple(int(value[i:i+2],16) for i in (1,3,5))

def render(data,long_edge=512):
    r=normalize(data);p=r['parameters'];rng=random.Random(r['seed']);kind=ARCHETYPES[r['archetype']][3]
    if long_edge not in (256,512,1024):raise ValueError('Resolution must be 256, 512 or 1024')
    aspect=p['aspect']; w,h=(long_edge,max(64,round(long_edge/aspect))) if aspect>=1 else (max(64,round(long_edge*aspect)),long_edge)
    c={k:rgb(v) for k,v in r['colors'].items()}
    a=Image.new('RGB',(w,h),c['back']);e=Image.new('RGB',(w,h));ad,ed=ImageDraw.Draw(a),ImageDraw.Draw(e)
    m=max(4,int(min(w,h)*.07));stroke=max(1,int(min(w,h)*.012))
    def rect(box,color,lit=False,width=0):
        ad.rectangle(tuple(map(int,box)),fill=None if width else color,outline=color if width else None,width=max(1,width))
        if lit:ed.rectangle(tuple(map(int,box)),fill=None if width else color,outline=color if width else None,width=max(1,width))
    def line(points,color,lit=True,weight=stroke):
        points=[(int(x),int(y)) for x,y in points];ad.line(points,fill=color,width=weight)
        if lit:ed.line(points,fill=color,width=weight)
    def text(label,x,y,scale,color=None,lit=False):
        color=color or c['ink'];scale=max(1,int(scale))
        for i,ch in enumerate(label):
            for yy,row in enumerate(FONT.get(ch,FONT['-'])):
                for xx,bit in enumerate(row):
                    if bit=='1':rect((x+(i*6+xx)*scale,y+yy*scale,x+(i*6+xx+1)*scale-1,y+(yy+1)*scale-1),color,lit)
    def fit(label,x,y,available,color=None,lit=False):text(label,x,y,max(1,int(available/max(1,len(label)*6))),color,lit)
    def glyph(x,y,size,color):
        grid=[(x+size*i/4,y+size*j/4) for j in range(5) for i in range(5)]
        for pts in ([grid[2],grid[22]],[grid[5],grid[9]],[grid[16],grid[18]]):line(pts,color,True,max(1,int(size*.075)))
        for _ in range(2+rng.randrange(3)):
            row=rng.randrange(5);col=rng.randrange(5)
            if rng.random()<.5:pts=[grid[row*5],grid[row*5+4]]
            else:pts=[grid[col],grid[20+col]]
            line(pts,color,True,max(1,int(size*.075)))
    def logo(cx,cy,size,color):
        line([(cx,cy-size),(cx+size,cy),(cx,cy+size),(cx-size,cy),(cx,cy-size)],color,True,stroke*2)
        line([(cx-size*.5,cy),(cx+size*.5,cy)],color,True,stroke*2)
        line([(cx,cy-size*.5),(cx,cy+size*.5)],color,True,stroke*2)
    # The backing has manufactured regions; grime and wear are independent overlays below.
    rect((m/2,m/2,w-m/2,h-m/2),tuple(min(255,v+15) for v in c['back']),width=max(1,int(stroke+p['border']*m*.35)))
    rect((m,m,w-m,h-m),c['neon'],True,width=max(1,int(stroke*p['border']*1.5)))
    code=f'{rng.randrange(10,99)}-{rng.randrange(100,999)}'
    if kind=='glyph':
        count=max(2,int(2+p['density']*4));size=min(w-4*m,(h-5*m)/count)*p['glyph_scale']*.72
        for i in range(count):glyph((w-size)/2,m*2+(h-4*m)/count*i,size,c['neon'] if i%2==0 else c['accent'])
        fit(code,m*2,h-m*2.4,w-4*m,c['ink'])
        line([(w-m*1.5,m*2),(w-m*1.5,h-m*3)],c['accent'],True)
    elif kind=='transit':
        rect((m*1.7,m*1.7,w*.24,h-m*1.7),c['neon']);fit('08',m*2.3,h*.30,w*.17,c['back'])
        fit('SECTOR / TRANSIT',w*.29,h*.24,w*.64,c['neon'],True)
        fit('PLATFORM '+code,w*.29,h*.57,w*.5,c['ink'])
        line([(w*.9,h*.68),(w*.94,h*.75),(w*.9,h*.82)],c['accent'],True,stroke*3)
    elif kind=='service':
        fit('SERVICE / '+code,m*2,h*.28,w*.75,c['neon'],True)
        line([(w*.85,h*.35),(w*.93,h*.5),(w*.85,h*.65)],c['accent'],True,stroke*3)
        line([(m*2,h*.8),(w-m*2,h*.8)],c['accent'],True)
    elif kind=='warning':
        tri=[(w*.5,h*.17),(w*.73,h*.59),(w*.27,h*.59),(w*.5,h*.17)]
        line(tri,c['neon'],True,stroke*3);fit('!',w*.47,h*.30,w*.06,c['neon'],True)
        # Exclamation is deliberately drawn, separate from abstract pseudo lettering.
        rect((w*.48,h*.32,w*.52,h*.45),c['neon'],True);rect((w*.48,h*.49,w*.52,h*.53),c['neon'],True)
        fit('HIGH VOLTAGE',m*2,h*.67,w-4*m,c['ink']);fit('LOCKOUT / '+code,m*2,h*.83,w-4*m,c['accent'])
    elif kind in ('ad','holo'):
        logo(w*.5,h*.35,min(w,h)*.19,c['neon']);fit('NOVA / SYSTEMS',m*2,h*.64,w-4*m,c['neon'],True)
        fit('LINK '+code,m*2,h*.82,w-4*m,c['accent'],True)
        for j in range(5):line([(w*.15+j*w*.14,h*.12),(w*.20+j*w*.14,h*.12)],c['accent'],True)
    elif kind=='stack':
        count=3
        for i in range(count):
            y=m*2+i*(h-4*m)/count;ph=(h-5*m)/count
            rect((m*1.6,y,w-m*1.6,y+ph),c['neon'] if i%2==0 else c['accent'],True,width=stroke*2)
            gs=min(ph*.50,w*.25);glyph(m*2.4,y+ph*.18,gs,c['accent'] if i%2==0 else c['neon'])
            fit(str(20+i)+f'-{rng.randrange(10,99)}',w*.50,y+ph*.3,w*.30,c['ink'],True)
    elif kind=='code':
        fit('ZONE / ACCESS',m*2,h*.20,w*.7,c['ink']);fit(code,m*2,h*.40,w-4*m,c['neon'],True)
        for i in range(int(15+45*p['density'])):
            x=m*2+(w-4*m)*i/60;rect((x,h*.81,x+1+rng.randrange(3),h*.90),c['accent'])
    elif kind=='corporate':
        logo(w*.17,h*.46,h*.20,c['neon']);fit('AXIOM',w*.33,h*.26,w*.52,c['neon'],True)
        fit('INFRASTRUCTURE',w*.33,h*.59,w*.54,c['ink']);line([(w*.33,h*.79),(w*.89,h*.79)],c['accent'])
    elif kind=='lightbox':
        rect((m*1.7,m*1.7,w-m*1.7,h-m*1.7),tuple(int(v*.60) for v in c['neon']),True)
        fit('MAINTENANCE',m*2.4,h*.27,w-4.8*m,c['back']);fit('BAY '+code,m*2.4,h*.59,w-4.8*m,c['back'])
        # Opaque lettering masks the lit panel, as real backlit signs do.
        ar=np.asarray(a);mask=np.all(ar==np.asarray(c['back']),axis=2);ea=np.asarray(e).copy();ea[mask]=0;e=Image.fromarray(ea);ed=ImageDraw.Draw(e)
    elif kind=='inactive':
        for yy in np.linspace(h*.18,h*.75,5):line([(m*2,yy),(w-m*2,yy)],tuple(v+7 for v in c['back']),False,stroke)
        fit('OFFLINE / '+code,m*2,h*.35,w-4*m,tuple(v+22 for v in c['back']))
        fit('SERVICE REQUIRED',m*2,h*.74,w-4*m,c['ink']);e=Image.new('RGB',(w,h));ed=ImageDraw.Draw(e)
    if r['hazard']:
        stripe=max(4,m*2)
        for x in range(-stripe,w,stripe*2):
            poly=[(x,h-m),(x+stripe,h-m),(x+stripe*2,h-m*.3),(x+stripe,h-m*.3)]
            ad.polygon(poly,fill=c['accent'])
    # Secondary data rhythm varies with density independently of primary layout.
    for i in range(int(p['density']*18)):
        x=m*2+i*(w-4*m)/18;rect((x,m*.55,x+max(1,stroke),m*.73),c['ink'])
    arr=np.asarray(a,dtype=np.float32);em=np.asarray(e,dtype=np.float32)
    wear=Image.new('L',(w,h));wd=ImageDraw.Draw(wear)
    for _ in range(int(140*p['wear'])):
        x=rng.randrange(w);y=rng.choice([rng.randrange(max(1,m*3)),h-rng.randrange(1,max(2,m*3)),rng.randrange(h)])
        wd.line([(x,y),(x+rng.randrange(2,max(3,w//18)),y)],fill=rng.randrange(90,210),width=1)
    wear_mask=np.asarray(wear,dtype=np.float32)/255*p['wear']
    yy,xx=np.mgrid[:h,:w];edge=np.exp(-np.minimum.reduce([xx,w-1-xx,yy,h-1-yy])/max(1,m*1.8))
    grime=edge*p['grime']*(.35+.15*np.sin(xx/max(1,w)*17))
    arr=arr*(1-grime[...,None])*(1-wear_mask[...,None])
    em=em*(1-grime[...,None])*(1-wear_mask[...,None])
    if kind=='holo':
        scan=(yy%4!=0)*.65+.35;arr*=scan[...,None];em*=scan[...,None]
        alpha=np.where(np.max(em,axis=2)>5,220,24).astype('uint8')
    else:alpha=np.full((h,w),255,dtype='uint8')
    rgba=np.concatenate([np.clip(arr,0,255).astype('uint8'),alpha[...,None]],axis=2)
    orm=np.stack([np.full((h,w),255),np.clip(120+grime*120+wear_mask*30,0,255),np.full((h,w),30)],axis=2).astype('uint8')
    return r,{'albedo':Image.fromarray(rgba),'emission':Image.fromarray(np.clip(em,0,255).astype('uint8')),'orm':Image.fromarray(orm)}

def preview(maps,strength):
    base=maps['albedo'].convert('RGB');em=maps['emission'];arr=np.asarray(base,dtype=float)+np.asarray(em,dtype=float)*min(1.0,strength*.20)
    glow=np.asarray(em.filter(ImageFilter.GaussianBlur(max(1,base.width/150))),dtype=float)*min(.45,strength*.12)
    return Image.fromarray(np.clip(arr+glow,0,255).astype('uint8'))

def export(data,target,long_edge=512,refresh=False):
    guard(12*1024**2);target=Path(target)
    existed=target.exists()
    if existed:
        if not refresh:raise FileExistsError(target)
        saved=json.loads((target/'recipe.billboard.json').read_text())
        if normalize(saved)!=normalize(data):raise ValueError('Refresh only the exact authored recipe')
    if not target.resolve().is_relative_to(ROOT):raise ValueError('Export outside project')
    r,maps=render(data,long_edge);target.mkdir(parents=True,exist_ok=refresh)
    resource='res://'+target.relative_to(ROOT).as_posix();w,h=maps['albedo'].size
    try:
        for name,im in maps.items():im.save(target/f'{name}.png',optimize=True)
        thumb=preview(maps,r['parameters']['emission_strength']);thumb.thumbnail((256,192));thumb.save(target/'preview.webp',quality=87)
        doc={**r,'generator_fingerprint':fingerprint(),'long_edge':long_edge,'size':[w,h],
             'sha256':{k:hashlib.sha256((target/f'{k}.png').read_bytes()).hexdigest() for k in maps}}
        (target/'recipe.billboard.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
        holo=r['archetype']=='HOLOGRAM'
        (target/'sign.tres').write_text(f'''[gd_resource type="ORMMaterial3D" load_steps=4 format=3]
[ext_resource type="Texture2D" path="{resource}/albedo.png" id="1"]
[ext_resource type="Texture2D" path="{resource}/emission.png" id="2"]
[ext_resource type="Texture2D" path="{resource}/orm.png" id="3"]
[resource]
resource_name = "{r['archetype']}"
transparency = {1 if holo else 0}
cull_mode = 2
albedo_texture = ExtResource("1")
orm_texture = ExtResource("3")
emission_enabled = true
emission = Color(1, 1, 1, 1)
emission_operator = 1
emission_energy_multiplier = {r['parameters']['emission_strength']}
emission_texture = ExtResource("2")
texture_filter = 0
''',encoding='utf-8')
        width,height=(3.0,3.0*h/w) if w>=h else (3.0*w/h,3.0)
        scene=f'''[gd_scene load_steps=5 format=3]
[ext_resource type="Material" path="{resource}/sign.tres" id="1"]
[sub_resource type="QuadMesh" id="Panel"]
size = Vector2({width}, {height})
[sub_resource type="BoxMesh" id="Backing"]
size = Vector3({width+.09}, {height+.09}, 0.10)
[sub_resource type="StandardMaterial3D" id="Support"]
albedo_color = Color(0.065, 0.085, 0.095, 1)
metallic = 0.7
roughness = 0.65
[node name="{r['archetype']}" type="Node3D"]
[node name="Panel" type="MeshInstance3D" parent="."]
position = Vector3(0, 0, 0.062)
mesh = SubResource("Panel")
material_override = ExtResource("1")
[node name="Support" type="MeshInstance3D" parent="."]
visible = {str(r['support_frame']).lower()}
mesh = SubResource("Backing")
material_override = SubResource("Support")
'''
        (target/'sign.tscn').write_text(scene,encoding='utf-8')
        return {'id':target.name,'archetype':r['archetype'],'directory':target.relative_to(ROOT).as_posix(),'scene':resource+'/sign.tscn','recipe':doc,'dimensions':[width,height],'bytes':sum(f.stat().st_size for f in target.iterdir())}
    except Exception:
        # This directory was just exclusively created by this call.
        import shutil
        if not existed:shutil.rmtree(target)
        raise

def config():
    return {'defaults':preset('HORIZONTAL_BILLBOARD'),'archetypes':{k:{'label':v[0],'recipe':preset(k)} for k,v in ARCHETYPES.items()},'controls':CONTROLS,'palettes':PALETTES,'generator_fingerprint':fingerprint()}
