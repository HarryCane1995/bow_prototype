"""Compact contact sheets from actual Godot GPU captures, retaining raw frames in ignored .godot."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Tools/Art/ArtPass/review'

def sheet(items,columns,name):
    cw,ch=360,280
    canvas=Image.new('RGB',(cw*columns,44+ch*((len(items)+columns-1)//columns)),'#101b22');draw=ImageDraw.Draw(canvas)
    draw.text((18,15),'BOW / GODOT FORWARD+ / '+name.replace('_',' ').upper(),fill='#becfca')
    for i,(path,label) in enumerate(items):
        im=Image.open(path).convert('RGB');im=im.crop((0,42,im.width,im.height-90));im.thumbnail((cw-8,ch-28))
        x=(i%columns)*cw;y=44+(i//columns)*ch
        canvas.paste(im,(x+(cw-im.width)//2,y+(ch-30-im.height)//2));draw.text((x+12,y+ch-21),label.replace('_',' '),fill='#c1d0cb')
    canvas.save(OUT/(name+'.webp'),quality=90)

if __name__=='__main__':
    vfx=json.loads((ROOT/'Assets/ProceduralArt/VFX/library.json').read_text())['effects']
    sheet([(ROOT/'.godot/art-pass-vfx-review'/f"{e['effect'].lower()}.png",e['effect']) for e in vfx],5,'vfx_godot')
    mat=json.loads((ROOT/'Assets/ProceduralArt/Materials/manifest.json').read_text())['materials']
    ids=[0,2,4,8,12,15,20,24,30,33,37,44]
    sheet([(ROOT/'.godot/art-pass-review'/f'material_{i}.png',mat[i]['id']) for i in ids],4,'materials_godot')
    signs=json.loads((ROOT/'Assets/ProceduralArt/Billboards/manifest.json').read_text())['items']
    sheet([(ROOT/'.godot/art-pass-review'/f'billboard_{i}.png',e['id']) for i,e in enumerate(signs)],4,'billboards_godot')
    sheet([(ROOT/'.godot/art-pass-review'/f'material_shape_{i}.png',label) for i,label in enumerate(['BOX','PLANE 3x3','WALL CORNER','CYLINDER','COLUMN CLUSTER'])],3,'shapes_godot')
    print('4 compact GPU contact sheets saved')
