"""Bounded local art storage: inspect first; prune only reproducible WebLab cache."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'Tools/Art/ArtPass/review'
GIB = 1024**3

def status():
    free = shutil.disk_usage(ROOT).free
    return {'free_bytes': free, 'free_gib': round(free/GIB, 3),
            'mode': 'STOP' if free < 15*GIB else 'CONSERVE' if free < 25*GIB else 'NORMAL'}

def guard(estimated_bytes=0):
    free = shutil.disk_usage(ROOT).free
    if free - estimated_bytes < 15*GIB:
        raise ValueError('Disk guard: less than 15 GiB reserve. Stop generation and inspect cache.')
    return {'free_bytes': free, 'free_gib': round(free/GIB, 3),
            'mode': 'CONSERVE' if free-estimated_bytes < 25*GIB else 'NORMAL'}

def snapshot(label):
    buckets, files, large, protected = defaultdict(int), {}, [], {}
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not Path(base,d).is_symlink()]
        for name in names:
            path=Path(base,name)
            try:
                rel=path.relative_to(ROOT).as_posix(); size=path.stat().st_size
            except OSError:
                continue
            files[rel]=size
            parts=rel.split('/')
            for n in range(1,min(3,len(parts)-1)+1): buckets['/'.join(parts[:n])]+=size
            if size>=20*1024**2: large.append({'path':rel,'bytes':size})
            if (parts[0] in ('Scripts','Scenes','Resources') and not rel.startswith(('Scripts/Environment/','Scenes/Debug/ArtPass'))) or (len(parts)==1 and path.suffix in ('.blend','.godot','.tscn')):
                protected[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
    data=dict(timestamp=datetime.now(timezone.utc).isoformat(),root=str(ROOT),
              disk=status(),project_bytes=sum(files.values()),file_count=len(files),
              folders=dict(sorted(buckets.items(),key=lambda x:-x[1])),
              large_files=sorted(large,key=lambda x:-x['bytes'])[:35],files=files,protected=protected)
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/f'storage_{label}.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('disk','project_bytes','file_count')},indent=2))
    print(json.dumps(dict(list(data['folders'].items())[:16]),indent=2))
    return data

def trim_cache(max_mib=256, keep=12):
    cache=(ROOT/'Tools/Art/FacadeFactory/WebLab/.cache').resolve()
    if not cache.is_relative_to(ROOT.resolve()) or cache.name!='.cache' or cache.is_symlink():
        raise ValueError('Unsafe cache path')
    if not cache.exists(): return {'removed_bytes':0,'entries':[]}
    # Only content-addressed cache entries. Never touch recipes/favorites/production or unknown files.
    import re
    entries=[]
    for parent in (cache,cache/'mesh-vfx',cache/'vfx',cache/'billboards'):
        if not parent.is_dir() or parent.is_symlink():continue
        for p in parent.iterdir():
            if not re.fullmatch(r'[a-f0-9]{64}(?:\.json)?',p.name) or p.is_symlink():continue
            if p.is_dir() and any(q.is_symlink() for q in p.rglob('*')):continue
            size=sum(q.stat().st_size for q in p.rglob('*') if q.is_file()) if p.is_dir() else p.stat().st_size
            entries.append((p.stat().st_mtime,p,size))
    entries.sort(reverse=True); total=sum(e[2] for e in entries); removed=[]
    for _,p,size in reversed(entries[keep:]):
        if total<=max_mib*1024**2: break
        resolved=p.resolve()
        if not resolved.is_relative_to(cache):raise ValueError('Cache escaped root')
        shutil.rmtree(resolved) if resolved.is_dir() else resolved.unlink()
        total-=size;removed.append({'path':p.relative_to(ROOT).as_posix(),'bytes':size})
    result={'removed_bytes':sum(r['bytes'] for r in removed),'remaining_bytes':total,'entries':removed}
    REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'cache_cleanup.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot');parser.add_argument('--trim-cache',action='store_true')
    args=parser.parse_args()
    if args.trim_cache:print(json.dumps(trim_cache(),indent=2))
    if args.snapshot:snapshot(args.snapshot)
