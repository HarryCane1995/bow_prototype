"""Review sheets from actual Blender/Godot images, no synthetic asset imagery."""
from pathlib import Path
import json,math,html
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
FONT=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17);SMALL=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13);BIG=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',28)
records=json.loads((QA/'candidate_manifest.json').read_text())['buildings']
SHEETS=QA/'ContactSheets';SHEETS.mkdir(exist_ok=True)
def paste(canvas,path,x,y,w,h):
    pic=Image.open(path).convert('RGB');pic.thumbnail((w,h));canvas.paste(pic,(x+(w-pic.width)//2,y+(h-pic.height)//2))
def header(im,title,subtitle):
    d=ImageDraw.Draw(im);d.text((22,15),title,font=BIG,fill='#e1eef0');d.text((22,53),subtitle,font=SMALL,fill='#9dbcc2');return d
for start in range(0,100,25):
    subset=records[start:start+25];w=540;h=265;im=Image.new('RGB',(w*5,h*5+90),'#101c24');d=header(im,f'UV / MATERIAL QA | {start+1:03}-{start+25:03}','FRONT / BACK / ROOF - actual fixed source - geometry unchanged - individual camera fit')
    for i,r in enumerate(subset):
        x=i%5*w;y=i//5*h+90
        for j,p in enumerate([OUT/r['previews'][0],QA/'Views'/f'{r["id"]}_back.png',QA/'Views'/f'{r["id"]}_roof.png']):paste(im,p,x+j*180,y,180,225)
        d.text((x+9,y+228),r['id']+' / '+r['name'][:26],font=FONT,fill='#e0ebed')
        d.text((x+9,y+249),r['category'],font=SMALL,fill='#91b6bd')
    im.save(SHEETS/f'UV_MATERIAL_QA_{start+1:03}_{start+25:03}.jpg',quality=94)

def pairs(ids,path,title,subtitle,getpair,width=360,height=450,cols=2):
    im=Image.new('RGB',(cols*width*2,math.ceil(len(ids)/cols)*(height+42)+90),'#101c24');d=header(im,title,subtitle)
    for i,id in enumerate(ids):
        x=i%cols*width*2;y=i//cols*(height+42)+90
        left,right=getpair(id)
        paste(im,left,x,y,width,height);paste(im,right,x+width,y,width,height)
        d.text((x+12,y+height+8),id+'  BEFORE',font=FONT,fill='#dfb481');d.text((x+width+12,y+height+8),id+'  AFTER',font=FONT,fill='#86d9bf')
    im.save(path,quality=94)
pairs(['HR003','HR027','HR036','HR039','HR007','HR057','HR098','HR100'],QA/'OFFENDERS_BEFORE_AFTER.jpg','UV / MATERIAL OFFENDERS | BEFORE / AFTER','Same meshes, no vertex/face/transform changes. Fixed floor rhythm, sign fit and face roles.',lambda id:(QA/'Before'/f'{id}_front.png',OUT/'Previews'/f'{id}.png'),300,375)
pairs(['HR003','HR027','HR036','HR037','HR039','HR065','HR098','HR100'],QA/'CHECKER_BEFORE_AFTER.jpg','NUMBERED DIRECTIONAL CHECKER | BEFORE / AFTER','Temporary debug materials only. Expected physical UV scale; arrows point upward. Not saved to source.',lambda id:(QA/'Checker'/f'{id}_before.png',QA/'Checker'/f'{id}_after.png'),360,360)
player=[r['id'] for r in json.loads((QA/'Candidate/player_positions.json').read_text())]
pairs(player,QA/'PLAYER_SCALE_BEFORE_AFTER.jpg','PLAYER SCALE | 1.8 m MARKER','Orange QA figure is 1.8 m tall. Roofs / window bands / service scale. Marker is preview-only.',lambda id:(QA/'Before'/f'{id}_player.png',QA/'Candidate'/f'{id}_player.png'),400,320)
# Lightweight all-100 index, detailed triples live in the four sheets above.
im=Image.new('RGB',(1800,2700),'#101c24');d=header(im,'UV_MATERIAL_QA_CONTACTSHEET | 100 / 100','Fixed source | All assets loaded | Detailed front / back / roof sheets: ContactSheets/')
for i,r in enumerate(records):
    x=i%10*180;y=i//10*260+90;paste(im,OUT/r['previews'][0],x,y,180,225);d.text((x+12,y+230),r['id']+' '+r['category'][:13],font=SMALL,fill='#d6e9eb')
im.save(QA/'UV_MATERIAL_QA_CONTACTSHEET.jpg',quality=92)
godot=QA/'GodotSanity';selection=json.loads((godot/'selected.json').read_text())
if all((godot/'Views'/f'{r["id"]}.png').exists() for r in selection):
    im=Image.new('RGB',(1600,1320),'#101c24');d=header(im,'GODOT 4.6.3 | DIRECT BLEND | 12 SAMPLES','Runtime frames: normals, ORM, emission and UVs survived import; isolated QA project.')
    for i,r in enumerate(selection):
        x=i%4*400;y=i//4*410+90;paste(im,godot/'Views'/f'{r["id"]}.png',x,y,400,350);d.text((x+10,y+356),r['id']+' / '+r['category'],font=FONT,fill='#d6e9eb')
    im.save(QA/'GODOT_12_CONTACTSHEET.jpg',quality=94)
links=['UV_MATERIAL_QA_CONTACTSHEET.jpg','OFFENDERS_BEFORE_AFTER.jpg','CHECKER_BEFORE_AFTER.jpg','PLAYER_SCALE_BEFORE_AFTER.jpg','GODOT_12_CONTACTSHEET.jpg']
page='''<!doctype html><html lang="ru"><meta charset="utf-8"><title>Highrise100 UV / material QA</title><style>body{margin:0;background:#101b23;color:#dce9ed;font:16px system-ui}header,section{padding:24px 4vw}h1{font-size:36px}a{color:#82d5cb}nav{display:flex;gap:20px;flex-wrap:wrap}.boards{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px}img{width:100%;display:block}figure{margin:0;background:#1c2b35;border-radius:8px;overflow:hidden}figcaption{padding:12px}.asset{margin:20px 0;border-top:1px solid #38505e;padding-top:16px}.triple{display:grid;grid-template-columns:repeat(3,1fr);max-width:1100px}.triple img{max-height:520px;object-fit:contain}.note{color:#a9c0c9;max-width:1100px}</style><header><h1>Highrise100 · UV / material QA</h1><p>100 зданий · геометрия сохранена · отдельная проверка 12 образцов в Godot</p><nav><a href="../index.html">Библиотека</a><a href="REPORT.md">Полный отчёт</a><a href="Independent/AFTER_INDEPENDENT.md">Независимый QA</a><a href="Independent/top20_before_after.csv">Top 20 до/после</a><a href="Independent/building_coverage_before_after.csv">Material coverage</a></nav><p class="note">Исправлены UV, физический масштаб и назначения материалов. Checker и фигуры 1,8 м используются только в QA-рендерах. Это exploratory-библиотека: повторение текстур заметно; игровая интеграция и traversal здесь не проверяются.</p></header><section class="boards">'''
for link in links:page+=f'<figure><a href="{link}"><img loading="lazy" src="{link}"></a><figcaption>{html.escape(link)}</figcaption></figure>'
page+='</section><section class="boards">'
for start in range(0,100,25):
    link=f'ContactSheets/UV_MATERIAL_QA_{start+1:03}_{start+25:03}.jpg';page+=f'<figure><a href="{link}"><img loading="lazy" src="{link}"></a><figcaption>{start+1}–{start+25}: front / back / roof</figcaption></figure>'
page+='</section><section><h2>Все 100: три ракурса</h2>'
for r in records:
    page+=f'<div class="asset" id="{r["id"]}"><h3>{r["id"]} · {html.escape(r["name"])}</h3><div class="triple">'
    for p in [f'../Previews/{r["id"]}.png',f'Views/{r["id"]}_back.png',f'Views/{r["id"]}_roof.png']:page+=f'<a href="{p}"><img loading="lazy" src="{p}"></a>'
    page+='</div></div>'
page+='</section></html>';(QA/'index.html').write_text(page,encoding='utf-8')
print('QA_BOARDS_CREATED',len(records),'player comparisons',len(player))
