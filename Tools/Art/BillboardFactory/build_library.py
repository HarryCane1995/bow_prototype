import json
from pathlib import Path
from PIL import Image, ImageDraw
from billboard_factory import *

def build(refresh=False):
    target=ROOT/'Assets/ProceduralArt/Billboards';target.mkdir(parents=True,exist_ok=True)
    entries=[];cards=[]
    for i,(key,item) in enumerate(ARCHETYPES.items()):
        recipe=preset(key,99)
        folder=target/key.lower()
        if folder.exists() and not refresh:
            doc=json.loads((folder/'recipe.billboard.json').read_text())
            if normalize(doc)!=recipe or doc['generator_fingerprint']!=fingerprint():raise ValueError(f'Stale library item {folder}; inspect before regeneration')
            entry={'id':folder.name,'archetype':key,'scene':'res://'+folder.relative_to(ROOT).as_posix()+'/sign.tscn','recipe':doc}
        else:entry=export(recipe,folder,512,refresh=refresh)
        entries.append(entry)
        _,maps=render(recipe,512);img=preview(maps,recipe['parameters']['emission_strength']);img.thumbnail((344,228))
        card=Image.new('RGB',(380,282),'#111b22');card.paste(img,((380-img.width)//2,(234-img.height)//2+9));d=ImageDraw.Draw(card)
        d.text((18,252),f'{i+1:02} / {item[0].upper()}',fill='#b9ccc9');cards.append(card)
    contact=Image.new('RGB',(380*4,282*3),'#111b22')
    for i,im in enumerate(cards):contact.paste(im,((i%4)*380,(i//4)*282))
    review=ROOT/'Tools/Art/ArtPass/review';review.mkdir(parents=True,exist_ok=True);contact.save(review/'billboards.webp',quality=90)
    (target/'manifest.json').write_text(json.dumps({'schema':'bow.art-library','kind':'billboards','items':entries},indent=2),encoding='utf-8')
    print(json.dumps({'billboards':len(entries),'bytes':sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),'preview':str(review/'billboards.webp')}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    build(refresh=args.refresh)
