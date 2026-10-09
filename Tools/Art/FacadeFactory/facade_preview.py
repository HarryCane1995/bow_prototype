"""Contact and software box preview, all derived from generated pixels."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

BG=(15,23,29)
INK=(212,224,219)
TEAL=(100,180,160)


def contact_sheet(variants, path):
    tw,th=232,464
    margin,gap=28,14
    w=margin*2+6*(tw+gap)-gap
    h=130+4*(th+44)+38
    board=Image.new("RGB",(w,h),BG);d=ImageDraw.Draw(board)
    title=ImageFont.load_default(size=32);font=ImageFont.load_default(size=13)
    d.text((margin,23),"FACADE FACTORY / 01",font=title,fill=INK)
    d.text((margin,68),"BOWPROTOTYPE   /   PROCEDURAL RASTER STUDIES   /   6 GRAMMARS x 4 SEEDS",font=font,fill=TEAL)
    for idx,v in enumerate(variants):
        col,row=idx//4,idx%4;x=margin+col*(tw+gap);y=118+row*(th+44)
        tex=Image.open(v["albedo"]).convert("RGB").resize((tw,th),Image.Resampling.LANCZOS)
        board.paste(tex,(x,y));d.rectangle((x-1,y-1,x+tw,y+th),outline=(54,73,77))
        d.text((x,y+th+7),v["preset"],font=font,fill=INK)
        d.text((x,y+th+23),f'SEED {v["seed"]:03}',font=font,fill=TEAL)
    d.text((margin,h-25),"UNIQUE SHEETS  /  ALBEDO ONLY  /  NO AI IMAGES  /  v0.1",font=font,fill=TEAL)
    Path(path).parent.mkdir(parents=True,exist_ok=True);board.save(path)


def box_sheet(variants,path):
    board=Image.new("RGB",(1560,890),BG);d=ImageDraw.Draw(board)
    d.text((28,22),"VERTICAL VOLUME / material placement study",font=ImageFont.load_default(size=25),fill=INK)
    for i,v in enumerate(variants[1::4]):
        x=35+i*255;y=130
        tex=Image.open(v["albedo"]).convert("RGB")
        em=Image.open(v["albedo"].replace("_albedo.png","_emission.png")).convert("RGB")
        import numpy as np
        lit=Image.fromarray(np.uint8(np.clip(np.asarray(tex,dtype=float)+np.asarray(em,dtype=float)*.18,0,255)))
        # Inverse affine mapping onto two parallelogram building faces.
        face=lit.resize((158,615),Image.Resampling.NEAREST).convert("RGBA")
        left=face.transform((158,680),Image.Transform.AFFINE,(1,0,0,-.24,1,0),Image.Resampling.BILINEAR)
        board.paste(left,(x,y+38),left)
        side=ImageEnhance.Brightness(lit).enhance(.59).resize((63,615)).convert("RGBA")
        right=side.transform((63,680),Image.Transform.AFFINE,(1,0,0,.60,1,-38),Image.Resampling.BILINEAR)
        board.paste(right,(x+158,y+38),right)
        d.polygon([(x,y+38),(x+63,y),(x+221,y+38),(x+158,y+76)],fill=(72,92,92))
        d.text((x,813),v["preset"],font=ImageFont.load_default(size=13),fill=INK)
        d.text((x,835),f'SEED {v["seed"]}',font=ImageFont.load_default(size=12),fill=TEAL)
    board.save(path)
