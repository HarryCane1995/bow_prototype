from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100'
data=json.loads((OUT/'manifest.json').read_text());rs=data['buildings']
canvas=Image.new('RGB',(2000,10*302+90),(16,23,29));d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13);title=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',26)
d.text((20,16),'HIGHRISE 100 / COMMON SCALE / 600 m vertical frame',font=title,fill=(215,228,231))
d.text((20,55),'Front elevations / same camera, projection and scale for all 100 / base at 0 m',font=font,fill=(130,187,190))
removed=[]
for i,r in enumerate(rs):
    p=OUT/'QA/CommonScaleTiles'/(r['id']+'.png');x=i%10*200;y=90+i//10*302
    im=Image.open(p).convert('RGB');canvas.paste(im,(x,y))
    d.text((x+6,y+264),r['id']+' / '+r['category'],font=font,fill=(196,222,225));d.text((x+6,y+281),f"{r['bounds_m'][2]:.0f} m",font=font,fill=(148,174,183))
    im.close();removed.append(dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size));p.unlink()
canvas.save(OUT/'CommonScale.jpg',quality=93)
(OUT/'QA/CommonScaleTiles').rmdir()
best=[next(r for r in rs if r['id']==i) for i in data['curated_best']]
for r in best:r['previews']=[f"Previews/{r['id']}_mood.png"]
import sys;sys.path.insert(0,str(Path(__file__).parent));from catalog import board
board(best,OUT/'Mood/Best12.jpg','BOW / 12 CANDIDATES / DUSK',4,280)
(OUT/'QA/cleanup.json').write_text(json.dumps(dict(removed_common_scale_tiles=removed,removed_bytes=sum(r['bytes'] for r in removed),other_cleanup='Facade generator uses one TemporaryDirectory, cleared after each recipe and removed on exit; previous task artifacts untouched'),indent=2))
print('COMMON_SCALE_FINISHED','REMOVED_TEMP_TILES',len(removed))
