"""Presentation contact sheets only; concept is never used as a model texture."""
from PIL import Image,ImageDraw,ImageFont,ImageOps
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DIR=ROOT/'Art/Characters/Hero_Silhouette';OUT=DIR/'Review'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',23)
bold=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',29)
small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
variants=[('A_Concept','A / CONCEPT PROPORTIONS'),('B_Powerful','B / MORE POWERFUL'),('C_AnimeLean','C / ANIME LEAN')]
bg=(32,37,42)
sheet=Image.new('RGB',(1200,2110),bg);d=ImageDraw.Draw(sheet)
d.text((28,17),'BOWPROTOTYPE / SILHOUETTE STUDIES',font=bold,fill=(231,232,230))
d.text((28,57),'Grey clay | one mesh set, three proportion states | awaiting visual selection',font=small,fill=(158,172,179))
for row,(name,label) in enumerate(variants):
 y=104+row*660;d.text((28,y),label,font=bold,fill=(220,182,126))
 for col,view in enumerate(['front','quarter','side']):
  im=Image.open(OUT/(name+'_'+view+'.png')).convert('RGB').crop((95,65,605,965))
  im=ImageOps.contain(im,(390,580));x=col*400+(400-im.width)//2
  sheet.paste(im,(x,y+47));d.text((col*400+28,y+620),{'front':'FRONT','quarter':'3/4','side':'SIDE'}[view],font=small,fill=(176,185,190))
sheet.save(OUT/'ABC_All_Views.png')

sheet=Image.new('RGB',(1440,840),bg);d=ImageDraw.Draw(sheet)
d.text((24,15),'CONCEPT / A / B / C — front proportion comparison',font=bold,fill=(232,232,230))
d.text((24,56),'Reference crop at comparable figure height. Study renders share camera and scale.',font=small,fill=(161,174,180))
ref=Image.open(DIR/'Concept_Reference.png').convert('RGB').crop((643,15,781,475))
ref=ImageOps.grayscale(ref).convert('RGB')
imgs=[ref]+[Image.open(OUT/(v[0]+'_front.png')).convert('RGB').crop((110,50,590,960)) for v in variants]
for i,im in enumerate(imgs):
 im=ImageOps.contain(im,(345,660));sheet.paste(im,(i*360+(360-im.width)//2,105+(660-im.height)//2))
 d.text((i*360+24,784),['CONCEPT','A / CONCEPT','B / POWERFUL','C / ANIME LEAN'][i],font=font,fill=(222,183,127))
sheet.save(OUT/'Concept_ABC_Front.png')

sheet=Image.new('RGB',(1080,730),bg);d=ImageDraw.Draw(sheet)
d.text((25,15),'A / B / C — BACK',font=bold,fill=(230,230,228))
for i,(name,_) in enumerate(variants):
 im=Image.open(OUT/(name+'_back.png')).convert('RGB').crop((95,65,605,965));im=ImageOps.contain(im,(350,630));sheet.paste(im,(i*360+(360-im.width)//2,63));d.text((i*360+25,693),'ABC'[i],font=font,fill=(222,183,127))
sheet.save(OUT/'ABC_Back.png')
print('REVIEW_SHEETS_SAVED')
