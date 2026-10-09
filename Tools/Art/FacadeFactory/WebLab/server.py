"""Loopback-only Facade Factory WebLab. Python stdlib + existing generator deps."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import secrets
import sys
import time
import threading
from urllib.parse import urlsplit, unquote
import webbrowser

from lab_backend import HERE, Lab, config, load_recipe
from palette_mixer import randomize_palette
from vfx_backend import VFXLab, config as vfx_config, load_recipe as load_vfx_recipe, generator_hash
from mesh_vfx_backend import MeshVFXLab, config as mesh_config, load_recipe as load_mesh_recipe, generator_hash as mesh_hash
from billboard_backend import BillboardLab, config as billboard_config, load_recipe as load_billboard_recipe
sys.path.insert(0, str(HERE.parents[3] / 'Tools/Art/ArtPass'))
from storage import guard, trim_cache, status as disk_status

ART_WRITE_LOCK = threading.RLock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, lab, token, vfx=None, mesh_vfx=None, billboard=None, **kwargs):
        self.lab, self.token = lab, token
        self.vfx = vfx
        self.mesh_vfx = mesh_vfx
        self.billboard = billboard
        super().__init__(*args, directory=str(HERE / "web"), **kwargs)

    def valid_host(self):
        return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

    def end_headers(self):
        if not self.path.startswith(('/api/', '/cache/', '/favorites/', '/vfx-cache/')):
            self.send_header('Cache-Control', 'no-cache')
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        super().end_headers()

    def json(self, value, status=200):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.valid_host():
            return self.json({"error": "Loopback host required"}, 403)
        route = urlsplit(self.path).path
        if route == '/api/storage':
            return self.json(disk_status())
        if route.startswith('/art-review/'):
            allowed = {'materials_best_12.jpg','materials_catalog_50.jpg','materials_tiles_4.jpg','materials_wraps_4.jpg',
                       'materials_godot.webp','vfx_godot.webp','billboards.webp','billboards_godot.webp','billboards_best_8.webp','shapes_godot.webp'}
            name = route.removeprefix('/art-review/')
            path = HERE.parents[3] / 'Tools/Art/ArtPass/review' / name if name in allowed else None
            if path is None or not path.is_file():
                return self.json({'error':'Review not found'},404)
            return self.file_bytes(path, 'image/webp' if path.suffix=='.webp' else 'image/jpeg')
        if route == '/api/billboard/config':
            return self.json(dict(**billboard_config(), token=self.token))
        if route == '/api/billboard/library':
            return self.json(self.billboard.library())
        if route.startswith(('/billboard-cache/', '/billboard-library/', '/billboard-favorites/')):
            path = self.billboard.asset_path(route)
            if path is None or not path.is_file():
                return self.json({'error':'Sign preview missing; generate again'},404)
            return self.file_bytes(path, 'image/webp' if path.suffix == '.webp' else 'image/png')
        if route.startswith('/material-library/'):
            match = re.fullmatch(r'/material-library/([a-z][a-z0-9_]{0,80})\.webp', route)
            path = HERE.parents[3] / 'Assets/ProceduralArt/Materials' / match[1] / 'preview.webp' if match else None
            if path is None or not path.is_file():
                return self.json({'error':'Material preview missing'},404)
            return self.file_bytes(path, 'image/webp')
        if route == '/api/mesh-vfx/config':
            return self.json(dict(**mesh_config(),token=self.token,generator_fingerprint=mesh_hash()))
        if route == '/api/vfx/config':
            return self.json(dict(**vfx_config(), token=self.token, generator_fingerprint=generator_hash()))
        if route == "/api/config":
            return self.json({**config(), "token": self.token})
        if route == "/api/health":
            return self.json({"status": "ok", "tool": "FacadeFactory WebLab", "local_only": True})
        if route == "/api/favorites":
            return self.json(self.lab.list_favorites())
        if route.startswith('/vfx-cache/'):
            match = re.fullmatch(r'/vfx-cache/([a-f0-9]{64})/(color_sheet|emission_sheet|preview|contact_sheet)\.png', route)
            path = self.vfx.cache / match[1] / f'{match[2]}.png' if match else None
            if path is None or not path.is_file():
                return self.json({'error': 'VFX preview not found'}, 404)
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'private, max-age=31536000, immutable')
            self.end_headers()
            self.wfile.write(raw)
            return
        if route.startswith('/favorites/'):
            path = self.lab.thumbnail_path(route.removeprefix('/favorites/'))
            if path is None:
                return self.json({'error': 'Thumbnail not found'}, 404)
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/webp')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'private, max-age=31536000, immutable')
            self.end_headers()
            self.wfile.write(raw)
            return
        if route.startswith("/cache/"):
            match = re.fullmatch(r"/cache/([a-f0-9]{64})/(albedo|emission|emission_mask|normal|orm|height|detail_albedo|detail_normal|weather_mask|preview_albedo|preview_orm|preview_normal)\.png", route)
            if not match:
                return self.json({"error": "Not found"}, 404)
            path = self.lab.cache / match[1] / f"{match[2]}.png"
            if not path.is_file():
                return self.json({"error": "Preview expired; regenerate"}, 404)
            raw = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
            self.end_headers()
            self.wfile.write(raw)
            return
        # SimpleHTTPRequestHandler handles static web assets only; never project files.
        self.path = route
        return super().do_GET()

    def do_POST(self):
        # A single writer bounds peak memory and makes cache eviction safe across tabs.
        with ART_WRITE_LOCK:
            return self.post_locked()

    def post_locked(self):
        origin = self.headers.get("Origin")
        allowed = (None, f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}")
        if not self.valid_host() or origin not in allowed or self.headers.get("X-Facade-Token") != self.token:
            return self.json({"error": "Use the local WebLab page"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            route = urlsplit(self.path).path
            limit = 262144 if route == '/api/favorites' else 131072
            if not 0 < length <= limit or self.headers.get_content_type() != "application/json":
                raise ValueError(f"Expected a JSON body <={limit // 1024} KB")
            data = json.loads(self.rfile.read(length))
            # Read disk state at each write, retaining a 15 GiB reserve even for a maximum sprite export.
            disk = disk_status() if route == '/api/storage/trim' else guard(512*1024**2 if route.endswith('/export') else 32*1024**2)
            if route == '/api/storage/trim':
                value = trim_cache(96 if disk['mode']=='CONSERVE' else 256)
            elif route == '/api/billboard/preview':
                value = self.billboard.preview(data)
            elif route == '/api/billboard/export':
                value = self.billboard.export(data)
            elif route == '/api/billboard/favorites':
                value = self.billboard.favorite(data)
            elif route == '/api/billboard/recipe/load':
                value = load_billboard_recipe(data)
            elif route == '/api/mesh-vfx/preview':
                value = self.mesh_vfx.preview(data)
            elif route == '/api/mesh-vfx/export':
                value = self.mesh_vfx.export(data)
            elif route == '/api/mesh-vfx/recipe/load':
                value = load_mesh_recipe(data)
            elif route == '/api/vfx/preview':
                value = self.vfx.preview(data)
            elif route == '/api/vfx/export':
                value = self.vfx.export(data)
            elif route == '/api/vfx/recipe/load':
                value = load_vfx_recipe(data)
            elif route == "/api/preview":
                value = self.lab.preview(data)
            elif route == "/api/export":
                value = self.lab.export(data)
            elif route == "/api/favorites":
                value = self.lab.favorite(data)
            elif route == "/api/recipe/load":
                value = load_recipe(data)
            elif route == '/api/palette/randomize':
                seed=data.get('random_seed')
                if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<2**32: raise ValueError('Invalid palette random seed')
                value=randomize_palette(data.get('palette_mix'),seed)
            else:
                return self.json({"error": "Not found"}, 404)
            if route.endswith('/preview'):
                self.server.preview_writes = getattr(self.server, 'preview_writes', 0) + 1
                if disk['mode'] == 'CONSERVE' or self.server.preview_writes % 24 == 0:
                    trim_cache(64 if disk['mode']=='CONSERVE' else 128)
            self.json(value)
        except (ValueError, TypeError, KeyError) as exc:
            self.json({"error": str(exc)}, 400)
        except FileExistsError:
            self.json({"error": "A file with this name appeared during export. Nothing was overwritten; try again."}, 409)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as exc:
            self.log_error("%s: %s", type(exc).__name__, exc)
            self.json({"error": f"Local generation failed: {exc}"}, 500)

    def guess_type(self, path):
        if str(path).endswith(".js"):
            return "text/javascript; charset=utf-8"
        return super().guess_type(path)

    def file_bytes(self, path, mime):
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'private, max-age=60')
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the local page in your default browser")
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    lab = Lab()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, lab=lab, token=token, vfx=VFXLab(), mesh_vfx=MeshVFXLab(), billboard=BillboardLab()))
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"FACADE_WEBLAB_READY {url} (loopback only)", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
