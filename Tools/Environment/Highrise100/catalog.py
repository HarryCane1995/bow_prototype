"""Offline, searchable review catalog and contact sheets from actual Blender renders."""
from pathlib import Path
import json, html, shutil
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100'
FONT=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
SMALL=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
TITLE=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',26)
def board(records,path,title,columns=5,width=250):
    rows=(len(records)+columns-1)//columns;tile_h=int(width*1.25)+65
    im=Image.new('RGB',(columns*width,rows*tile_h+80),(17,24,30));d=ImageDraw.Draw(im)
    d.text((20,18),title,font=TITLE,fill=(221,229,230))
    subtitle='BOW PROTOTYPE / ATMOSPHERE REVIEW / real procedural geometry' if 'DUSK' in title else 'BOW PROTOTYPE / EXPLORATION / neutral lighting / individual fit-to-frame'
    d.text((20,51),subtitle,font=SMALL,fill=(127,162,170))
    for i,r in enumerate(records):
        x=i%columns*width;y=80+i//columns*tile_h
        p=OUT/r['previews'][0]
        if p.exists():
            pic=Image.open(p).convert('RGB');pic.thumbnail((width-8,int(width*1.25)))
            im.paste(pic,(x+(width-pic.width)//2,y))
        d.text((x+8,y+int(width*1.25)+5),r['id']+'  '+r['name'][:24],font=FONT,fill=(229,231,222))
        d.text((x+8,y+int(width*1.25)+26),r['category']+' / '+r['role'],font=SMALL,fill=(132,184,188))
        d.text((x+8,y+int(width*1.25)+44),f"{r['bounds_m'][2]:.0f} m / {r['metrics']['triangles']:,} tris",font=SMALL,fill=(146,158,166))
    im.save(path,quality=92)
def main():
    data=json.loads((OUT/'manifest.json').read_text());records=data['buildings']
    (OUT/'ContactSheets').mkdir(exist_ok=True);(OUT/'Cards').mkdir(exist_ok=True)
    for r in records:(OUT/'Cards'/(r['id']+'.json')).write_text(json.dumps(r,indent=2))
    for start in range(0,len(records),25):board(records[start:start+25],OUT/'ContactSheets'/f'{start+1:03}-{min(start+25,len(records)):03}.jpg',f'HIGHRISE 100 / {start+1:03} - {min(start+25,len(records)):03}')
    for family in sorted(set(r['category'] for r in records)):
        board([r for r in records if r['category']==family],OUT/'ContactSheets'/(family+'.jpg'),family.upper(),5,270)
    board(records,OUT/'ContactSheet_All.jpg',f'HIGHRISE 100 / {len(records)} BUILDINGS',10,180)
    template='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Bow / Highrise 100</title>
<style>*{box-sizing:border-box}body{background:#111a21;color:#dce6e8;font:15px system-ui;margin:0}header{padding:34px 4vw 20px;border-bottom:1px solid #31404b}h1{font-size:38px;margin:0 0 8px}p{color:#a4b8c3}a{color:#81c5cb}nav{display:flex;gap:18px;flex-wrap:wrap}.controls{padding:18px 4vw;display:flex;gap:12px;position:sticky;top:0;background:#111a21ee;z-index:1;flex-wrap:wrap}select,input,button{font:inherit;background:#23333e;color:#dfeded;border:1px solid #435763;padding:10px;border-radius:5px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:18px;padding:0 4vw 40px}.card{background:#1b2832;border:1px solid #32434e;border-radius:8px;overflow:hidden}.card img{width:100%;display:block;aspect-ratio:4/5;object-fit:cover}.info{padding:13px}.id{color:#7fc8cb;font-size:13px;letter-spacing:2px}h2{font-size:19px;margin:4px 0 9px}.metrics{font-size:13px;color:#a4b8c3;line-height:1.7}.tags{font-size:12px;color:#bdd0c6;min-height:38px;margin:10px 0}details{margin-top:10px;font-size:12px}summary{cursor:pointer;color:#82cbd0}pre{white-space:pre-wrap;max-height:240px;overflow:auto}#count{margin-left:auto;padding:10px;color:#83b2bb}.note{font-size:13px;max-width:980px}</style>
<header><div class="id">BOW PROTOTYPE / ENVIRONMENT EXPLORATION</div><h1>100 высоток · один город</h1><p>20 семейств · отдельные конструктивные подтипы · процедурные фасады и поверхности</p>
<nav><a href="Highrise100.blend">Blender library</a><a href="ContactSheet_All.jpg">Все силуэты</a><a href="Materials.jpg">Материалы</a><a href="manifest.json">Manifest</a><a href="REPORT.md">Отчёт</a><a href="References/index.html">Референсы</a></nav>
<p class="note">Превью подогнаны под кадр: физические высоты указаны в карточках. Выбирайте по ID; в Blender Asset Browser и коллекциях сохранены те же имена. Это библиотека для дальнейшего kitbashing: без интерьеров, LOD и игровых коллизий. Показатели art direction — диагностические оценки, а не результаты измерения восприятия.</p></header>
<div class="controls"><input id="q" placeholder="ID, имя, признак…"><select id="family"><option value="">Все семейства</option></select><select id="role"><option value="">Все роли</option><option>background</option><option>midground</option><option>hero</option></select><select id="sort"><option value="id">По ID</option><option value="height">По высоте</option><option value="triangles">По полигонам</option></select><span id="count"></span></div><main id="grid"></main>
<script>const records=__DATA__;const $=id=>document.getElementById(id);for(const f of [...new Set(records.map(r=>r.category))]){$('family').add(new Option(f,f))}function draw(){let rs=records.filter(r=>(!$('family').value||r.category===$('family').value)&&(!$('role').value||r.role===$('role').value)&&JSON.stringify([r.id,r.name,r.features]).toLowerCase().includes($('q').value.toLowerCase()));if($('sort').value==='height')rs.sort((a,b)=>b.bounds_m[2]-a.bounds_m[2]);if($('sort').value==='triangles')rs.sort((a,b)=>a.metrics.triangles-b.metrics.triangles);$('count').textContent=rs.length+' / '+records.length;$('grid').innerHTML=rs.map(r=>`<article class="card"><a href="${r.previews[0]}" target="_blank"><img loading="lazy" src="${r.previews[0]}" alt="${r.id} ${r.name}"></a><div class="info"><div class="id">${r.id} / ${r.role}</div><h2>${r.name}</h2><div class="metrics">${r.category} · ${r.bounds_m[2].toFixed(0)} m<br>${r.bounds_m[0].toFixed(0)} × ${r.bounds_m[1].toFixed(0)} m · ${r.metrics.triangles.toLocaleString()} tris<br>${r.metrics.meshes} editable parts</div><div class="tags">${r.features.join(' · ')}</div><a href="Cards/${r.id}.json">Карточка</a>${r.previews.slice(1).map((p,i)=>` · <a href="${p}" target="_blank">Вид ${i+2}</a>`).join('')}<details><summary>Параметры / material recipes</summary><pre>${JSON.stringify({parameters:r.parameters,axes:r.axes,recipes:r.recipes},null,2)}</pre></details></div></article>`).join('')}for(const id of ['q','family','role','sort'])$(id).addEventListener('input',draw);draw();</script></html>'''
    template=template.replace('References/index.html','References/CATALOG.html')
    template=template.replace('<a href="Materials.jpg">','<a href="UV_Material_QA/index.html">UV / material QA · до и после</a><a href="Materials.jpg">')
    (OUT/'index.html').write_text(template.replace('__DATA__',json.dumps(records,ensure_ascii=False)),encoding='utf-8')
    print('CATALOG',len(records),'bytes',sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()),'free',shutil.disk_usage(ROOT).free)
if __name__=='__main__':main()
