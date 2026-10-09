"""Derived repeat maps for UV QA. Original art/maps remain unchanged."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'Art/Environment/Highrise100'
CHANNELS=('albedo','normal','orm','height','emission')

def main():
    original=[r for r in json.loads((OUT/'materials.json').read_text()) if not r.get('uv_qa_version')]
    additions=[]
    for rec in original:
        key=rec['key']
        if not (key.startswith('f') and key[1:2].isdigit() or key.startswith('sign_')):continue
        facade=key.startswith('f');newkey=key+'_uv';dest=OUT/'Textures'/newkey;dest.mkdir(exist_ok=True)
        for ch in CHANNELS:
            src=Image.open(OUT/'Textures'/key/(ch+'.png')).convert('RGB')
            if facade:
                # Remove unique roof/base lips. Retain the authored internal assembly.
                a=np.asarray(src.crop((0,36,src.width,992))).copy()
                # Periodic narrow structural seams. Every edge texel and corner agrees;
                # normal seam is flat and no luminous window is cut at the repeat edge.
                c={'albedo':(22,29,33),'normal':(128,128,255),'orm':(210,190,90),'height':(92,92,92),'emission':(0,0,0)}[ch]
                h,w=a.shape[:2];distance=np.minimum(np.minimum(np.arange(w)[None,:],(w-1-np.arange(w))[None,:]),np.minimum(np.arange(h)[:,None],(h-1-np.arange(h))[:,None]))
                alpha=np.clip(distance/5,0,1)[...,None]
                a=np.rint(a*alpha+np.array(c)*(1-alpha)).astype('uint8');result=Image.fromarray(a)
            else:
                # Preserve complete sign art. CLAMP extends only this dark matte,
                # allowing face UV to letterbox without stretching or cropping text.
                c={'albedo':(9,13,17),'normal':(128,128,255),'orm':(255,180,20),'height':(128,128,128),'emission':(0,0,0)}[ch]
                result=Image.new('RGB',(src.width+8,src.height+8),c);result.paste(src,(4,4))
            result.save(dest/(ch+'.png'))
        new=dict(rec);new.update(key=newkey,source_key=key,mode='PERIODIC_FACADE_INTERIOR' if facade else 'CLAMP_SIGN_LETTERBOX',recipe=f'Recipes/{newkey}.uv.json',uv_qa_version=1)
        if facade:new.update(crop=[0,36,512,992],tile_width_m=42,nominal_floor_rows=956/rec['parameters']['floor_height'])
        new['sha256']={c:hashlib.sha256((dest/(c+'.png')).read_bytes()).hexdigest() for c in CHANNELS}
        new['image_size']=list(result.size)
        (OUT/new['recipe']).write_text(json.dumps(new,indent=2));additions.append(new)
    (OUT/'materials.json').write_text(json.dumps(original+additions,indent=2))
    print('DERIVED_UV_MATERIALS',len(additions),'originals preserved',len(original))
if __name__=='__main__':main()
