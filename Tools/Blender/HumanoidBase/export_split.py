"""CLI: python export_split.py --branch 1POV (or 3POV/all).

First run capture_split.py in the current PoseLab for the selected branch.
Reuses the proven evaluated-pose baker; never edits canonical source or V2 GLB.
"""
import argparse, subprocess, shutil, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--branch',choices=['1POV','3POV','all'],default='all')
p.add_argument('--blender',default=shutil.which('blender') or r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
a=p.parse_args()
for branch in (['1POV','3POV'] if a.branch=='all' else [a.branch]):
    capture=ROOT/'.godot/split-presentation'/branch/'capture.json'
    output=ROOT/'Assets/Characters/BaseHumanoid/Exports'/('BH01_'+branch+'.glb')
    subprocess.run([a.blender,'--background','--python',str(Path(__file__).with_name('export_v2.py')),'--',str(capture),'--output',str(output),'--idle-action','BH01_'+branch+'_IDLE','--parts',*(['ARMS'] if branch=='1POV' else ['HEAD','TORSO','ARMS','LEGS'])],check=True)
    shutil.copyfile(capture.with_name('presentation.json'),output.with_suffix('.presentation.json'))
    # Import settings are input configuration, never generated scene edits.
    config=output.with_suffix('.glb.import')
    if not config.exists():
        config.write_text('[remap]\nimporter="scene"\ntype="PackedScene"\n\n[deps]\nsource_file="res://'+str(output.relative_to(ROOT)).replace('\\','/')+'"\n\n[params]\nanimation/import=true\nanimation/fps=60\nanimation/remove_immutable_tracks=false\nanimation/import_rest_as_RESET=false\nimport_script/path="res://Scripts/Editor/Import/V2AnimationPostImport.gd"\nskins/use_named_skins=true\n')
    print('SPLIT_EXPORTED',branch,output)
