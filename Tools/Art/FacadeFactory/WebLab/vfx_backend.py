"""Additive VFX service, with its own schema, cache and export namespace."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time

from lab_backend import ROOT, HERE
VFX = ROOT / 'Tools/Art/VFXFactory'
sys.path.insert(0, str(VFX))
from schema import config, normalize, fingerprint
from explosion import assemble
from godot_export import write_godot, TEMPLATES


def generator_hash():
    return hashlib.sha256((fingerprint() + ''.join(hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(TEMPLATES.glob('*')) if p.is_file())).encode()).hexdigest()


def load_recipe(data):
    if data.get('generator_fingerprint', generator_hash()) != generator_hash():
        raise ValueError('VFX generator changed; this recipe requires its original version')
    return normalize(data)


class VFXLab:
    def __init__(self, cache=None, exports=None):
        self.cache = Path(cache or HERE / '.cache/vfx')
        self.exports = Path(exports or ROOT / 'Assets/VFX/Explosions/PSXExplosion')
        self.cache.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def preview(self, data):
        start = time.perf_counter()
        recipe = normalize(data)
        key = hashlib.sha256(json.dumps([generator_hash(), recipe], sort_keys=True).encode()).hexdigest()
        folder = self.cache / key
        with self.lock:
            cached = (folder / 'result.json').is_file()
            if not cached:
                with tempfile.TemporaryDirectory(prefix='vfx_', dir=self.cache) as tmp:
                    metadata = assemble(recipe, tmp)
                    result = dict(key=key, recipe=recipe, metadata=metadata,
                        images={name: f'/vfx-cache/{key}/{name}.png' for name in
                                ('color_sheet', 'emission_sheet', 'preview', 'contact_sheet')})
                    (Path(tmp) / 'result.json').write_text(json.dumps(result), encoding='utf-8')
                    shutil.copytree(tmp, folder)
            result = json.loads((folder / 'result.json').read_text())
        return dict(**result, cached=cached, elapsed_ms=round((time.perf_counter() - start) * 1000))

    def export(self, data):
        name = data.get('name', '')
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,63}', name):
            raise ValueError('Asset name: 1–64 ASCII letters, digits, _ or -; start with a letter')
        if name.upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
            raise ValueError('Reserved Windows filename')
        recipe = normalize(data.get('recipe', {}))
        export_format = data.get('format', 'BOTH')
        if export_format not in ('FLIPBOOK', 'BOTH'):
            raise ValueError('Export format must be FLIPBOOK or BOTH')
        emission = data.get('emission', True)
        if not isinstance(emission, bool):
            raise ValueError('Emission must be boolean')
        with self.lock:
            self.exports.mkdir(parents=True, exist_ok=True)
            chosen, revision = name, 1
            while (self.exports / chosen).exists():
                revision += 1; chosen = f'{name}_r{revision:02}'
            target = self.exports / chosen
            resource_path = 'res://' + target.relative_to(ROOT).as_posix()
            with tempfile.TemporaryDirectory(prefix='vfx_export_', dir=self.cache) as tmp:
                stage = Path(tmp)
                metadata = assemble(recipe, stage, sequence=export_format == 'BOTH', emission=emission)
                write_godot(stage, resource_path, recipe, metadata)
                hashes = {p.relative_to(stage).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(stage.rglob('*.png'))}
                doc = dict(**recipe, generator_fingerprint=generator_hash(), name=chosen,
                           created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                           export_format=export_format, emission=emission, sha256=hashes)
                (stage / f'{chosen}.vfx.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
                (stage / 'metadata.json').write_text(json.dumps(dict(**metadata, sha256=hashes), indent=2) + '\n', encoding='utf-8')
                # Same-volume rename publishes a complete set; never overwrite a user asset.
                stage.rename(target)
        return dict(name=chosen, directory=target.relative_to(ROOT).as_posix(), recipe=doc, metadata=metadata,
                    scene=resource_path + '/review.tscn', files=sorted(p.relative_to(ROOT).as_posix() for p in target.rglob('*') if p.is_file()))
