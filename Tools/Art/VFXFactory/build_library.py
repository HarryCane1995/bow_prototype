"""Export the ten curated VFX recipes once, with compact previews and an index."""
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'FacadeFactory/WebLab'))
sys.path.insert(0,str(HERE.parent/'ArtPass'))
from storage import guard
from mesh_archetypes import EFFECTS, defaults
from mesh_vfx_backend import MeshVFXLab


def main():
    guard(25*1024*1024)
    lab=MeshVFXLab();records=[]
    for effect,meta in EFFECTS.items():
        target=lab.exports/meta['slug']
        if target.exists():
            raise FileExistsError(f'{target} already exists; production exports are never overwritten')
        result=lab.export(dict(name=meta['slug'],recipe=defaults(effect)))
        records.append(dict(effect=effect,label=meta['label'],directory=result['directory'],
            scene=result['effect_scene'],review=result['scene'],sample_time=meta['sample_time'],stats=result['stats']))
    index=dict(schema='bowprototype.vfx_library',version=1,count=len(records),effects=records)
    (lab.exports/'library.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    contact=Image.new('RGB',(1600,500),(12,20,26));draw=ImageDraw.Draw(contact)
    for i,item in enumerate(records):
        x=(i%5)*320;y=(i//5)*250
        contact.paste(Image.open(ROOT/item['directory']/'preview.png'),(x,y))
        draw.text((x+10,y+222),item['label'].replace(' · ',' / '),fill=(187,212,200))
    contact.save(lab.exports/'library_contact.png',optimize=True)
    print(json.dumps(index,indent=2))


if __name__=='__main__':main()
