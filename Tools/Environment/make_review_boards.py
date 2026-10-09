"""Contact sheets from actual Blender/Godot captures; no image synthesis."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'Art/Environment/Skyscrapers/Review'
FONT=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)

def board(items,cols,w,h,dest):
    rows=(len(items)+cols-1)//cols
    out=Image.new('RGB',(cols*w,rows*(h+38)),(17,24,29));draw=ImageDraw.Draw(out)
    for i,(path,title) in enumerate(items):
        im=Image.open(R/path).convert('RGB');im.thumbnail((w-8,h))
        x=(i%cols)*w;y=(i//cols)*(h+38)
        out.paste(im,(x+(w-im.width)//2,y+(h-im.height)//2))
        draw.text((x+10,y+h+7),title,font=FONT,fill=(184,218,210))
    out.save(R/dest,quality=94)

items=[(p.name,p.stem.replace('kit_L01_Skyline_','').replace('_',' / ')) for p in sorted(R.glob('kit_L01*.png'))]
board(items,5,400,496,'Kit_Lineup.jpg')
board([('after_skyline_west.png','WEST / truss + distant needle'),
       ('after_skyline_east.png','EAST / suspended + clean spire'),
       ('after_route_spawn.png','ROUTE / spawn viewpoint'),
       ('after_route_ground.png','ROUTE / combat approach')],2,800,500,'Skyline_and_Route.jpg')
board([('after_exoskeleton.png','01 / Exoskeleton'),('after_suspended.png','04 / Suspended volumes'),
       ('after_landmark.png','10 / Offset halo')],3,640,400,'Tower_Closeups.jpg')
print('REVIEW_BOARDS_SAVED')
