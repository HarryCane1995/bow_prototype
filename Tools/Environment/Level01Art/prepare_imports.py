"""Set explicit 3D mipmaps for the owned Level_01 texture copies after first import.

Godot cannot infer 3D use at initial import when textures arrive through a custom
post-import material resolver. Edit .import settings, never generated .ctex files.
"""
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
manifest=json.loads((ROOT/'Assets/Materials/Environment/Level01Art/placement_manifest.json').read_text())
count=0
for key,item in manifest['materials'].items():
    for channel in item['textures']:
        path=ROOT/f'Assets/Textures/Levels/Level_01/ArtPass/{key}/{channel}.png.import'
        assert path.is_file(), 'Run Godot --import once before this step'
        text=path.read_text()
        for field,value in [('mipmaps/generate','true'),('compress/mode','2'),
                            ('compress/normal_map','1' if channel=='normal' else '2')]:
            text=re.sub(r'^'+re.escape(field)+r'=.*$',field+'='+value,text,flags=re.M)
        path.write_text(text,encoding='utf-8')
        count+=1
print('LEVEL01_ART_3D_TEXTURE_IMPORTS',count)
