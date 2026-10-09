"""Summarize the current pass against the initial inventory; no production mutations."""
import json
from pathlib import Path
from datetime import datetime
from storage import ROOT,REPORT,snapshot

def main():
    before=json.loads((REPORT/'storage_before.json').read_text())
    after=snapshot('after')
    protected=[path for path,digest in before['protected'].items() if after['protected'].get(path)!=digest]
    assert not protected, f'Protected source drift: {protected}'
    prefixes=('Tools/Art/','Tools/Rendering/art_library_review','Tools/Rendering/verify_art_library',
              'Tools/Rendering/verify_vfx_library','Assets/ProceduralArt/','Scenes/Debug/ArtPassReview',
              'Docs/ART_TOOLING_PASS','Docs/PROCEDURAL_MATERIAL_LIBRARY','Docs/VFX_FACTORY')
    started=datetime.fromisoformat(before['timestamp']).timestamp()
    sources=['Tools/Art/ArtPass/.gdignore'];generated=[]
    for path,size in after['files'].items():
        if not path.startswith(prefixes) or '/.cache/' in path or '/__pycache__/' in path:continue
        file=ROOT/path
        if path not in before['files'] or before['files'][path]!=size or file.stat().st_mtime>=started:
            (generated if path.startswith(('Assets/ProceduralArt/','Tools/Art/Library/','Tools/Art/ArtPass/review/')) else sources).append(path)
    deletions=[{'path':p,'bytes':n} for p,n in before['files'].items() if p not in after['files'] and p.startswith('Tools/Art/')]
    cleanup=json.loads((REPORT/'cache_cleanup_initial.json').read_text())
    folders=['.godot','.godot/imported','Tools/Art/FacadeFactory','Tools/Art/ArtPass','Assets/ProceduralArt',
             'Assets/ProceduralArt/Materials','Assets/ProceduralArt/VFX','Assets/ProceduralArt/Billboards','Tools/Art/Library','.git','Art']
    qa={}
    for name in ['materials_qa','materials_controls_qa','vfx_geometry_qa','billboard_qa','integration_qa']:
        item=json.loads((REPORT/(name+'.json')).read_text());qa[name]=item.get('result',item.get('passed',item.get('checks','see report')))
    for name,folder in [('godot_materials_signs','art-pass-review'),('godot_vfx','art-pass-vfx-review')]:
        qa[name]=json.loads((ROOT/'.godot'/folder/'runtime_report.json').read_text())
    data={'start_disk':before['disk'],'end_disk':after['disk'],
          'start_project_bytes':before['project_bytes'],'end_project_bytes':after['project_bytes'],
          'folder_deltas':{p:{'before':before['folders'].get(p,0),'after':after['folders'].get(p,0),
                               'delta':after['folders'].get(p,0)-before['folders'].get(p,0)} for p in folders},
          'protected_files_checked':len(before['protected']),'protected_changed':protected,
          'authored_counts':{'materials':50,'vfx':10,'billboard_archetypes':12},
          'qa':qa,'cache_cleanup_manifest_bytes':cleanup['removed_bytes'],'cache_cleanup_manifest_entries':len(cleanup['entries']),
          'all_deleted_art_cache_bytes':sum(d['bytes'] for d in deletions),'deleted_art_paths':deletions,
          'source_files_added_or_changed':sorted(sources),'generated_art_paths':sorted(generated),
          'browser_qa':{'tabs':3,'material_catalog_filter_and_wrap_load':'PASS','wrap_seam_label':'PASS X, 12 maps, delta 0',
                        'vfx_energy_orb_playback':'PASS','billboard_pin_randomize_return_A_seed_99':'PASS',
                        'review_gallery':'PASS','console_errors':0},
          'remaining_scope':'No level application or gameplay integration; prototype art review handoff.',
          'disk_note':'Whole-drive free-space changes include activity outside this project; project delta is measured independently.'}
    (REPORT/'final_scope_storage.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (REPORT/'changed_files.md').write_text('# Art-pass changed paths\n\n## Sources\n\n'+''.join('- `'+p+'`\n' for p in sorted(sources))+
          '\n## Generated recipes / runtime / review\n\n'+''.join('- `'+p+'`\n' for p in sorted(generated)),encoding='utf-8')
    print(json.dumps({'free_before_gib':before['disk']['free_gib'],'free_after_gib':after['disk']['free_gib'],
                      'project_before_gib':round(before['project_bytes']/1024**3,3),'project_after_gib':round(after['project_bytes']/1024**3,3),
                      'protected_files':len(before['protected']),'protected_changed':protected,'library_mib':round(after['folders']['Assets/ProceduralArt']/1024**2,3),
                      'source_paths':len(sources),'removed_art_cache_mib':round(sum(d['bytes'] for d in deletions)/1024**2,3)},indent=2))

if __name__=='__main__':main()
