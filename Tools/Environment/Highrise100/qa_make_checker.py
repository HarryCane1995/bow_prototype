from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
QA=Path(__file__).resolve().parents[3]/'Art/Environment/Highrise100/UV_Material_QA'
im=Image.new('RGB',(512,512));d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',25)
for y in range(4):
    for x in range(4):
        px=x*128;py=y*128;color=(58,84,92) if (x+y)%2 else (191,207,208)
        d.rectangle((px,py,px+127,py+127),fill=color,outline=(10,21,25),width=2)
        d.text((px+9,py+78),str(4*(3-y)+x+1).zfill(2),font=font,fill=(250,122,29))
        d.line((px+86,py+101,px+86,py+28),fill=(252,152,22),width=5)
        d.polygon([(px+86,py+17),(px+74,py+37),(px+98,py+37)],fill=(252,152,22))
im.save(QA/'numbered_checker.png')
