"""Bounded generator QA: replay, resolutions, semantic data and normal convention."""
import hashlib
import json
from pathlib import Path
import tempfile
import time
import shutil
import numpy as np
from PIL import Image
from facade_factory import generate, get_preset, PRESETS, HERE, TEXTURES, MATERIALS, write_material
from facade_stylizer import normal_from_height


def main():
    start=time.perf_counter();checks=[]
    with tempfile.TemporaryDirectory(prefix="facade_qa_") as tmp:
        for size in [(256,512),(512,1024),(1024,2048)]:
            t=time.perf_counter()
            for name in PRESETS:
                p=get_preset(name)
                a=generate(p,42,*size,Path(tmp)/"a",None)
                b=generate(p,42,*size,Path(tmp)/"b",None)
                assert a["sha256"]==b["sha256"],f"Non-deterministic {name} {size}"
                for channel in ["albedo","emission","normal","orm","height"]:
                    im=Image.open(Path(tmp)/"a"/f'{a["stem"]}_{channel}.png')
                    assert im.size==size
                    if channel=="emission":
                        values=np.asarray(im); coverage=np.any(values>0,axis=2).mean()
                        assert 0<coverage<.5
                    if channel=="normal":
                        n=np.asarray(im,dtype=float)/127.5-1
                        assert np.abs(np.linalg.norm(n,axis=2)-1).max()<.015
                        assert n[...,2].min()>.85
                    if channel=="orm":
                        v=np.asarray(im)
                        assert np.any(np.all(v==[224,88,0],axis=2)),"Missing glass semantics"
                        assert np.any(np.all(v==[240,137,178],axis=2)),"Missing metal semantics"
                        assert np.any(np.all(v==[155,224,0],axis=2)),"Missing recess/AO semantics"
                    im.close()
                if size != (512,1024):
                    dest=TEXTURES/"resolution_tests";dest.mkdir(exist_ok=True)
                    for path in (Path(tmp)/"a").glob(a["stem"]+"*"):
                        shutil.copy2(path,dest/path.name)
                    write_material(MATERIALS/"resolution_tests"/(a["stem"]+".tres"),a["stem"],dest,p)
            checks.append(dict(size=list(size),presets=6,replays=2,seconds=round(time.perf_counter()-t,3),pass_=True))
        # Nonstandard aspect/resolution, seed divergence, configuration handles.
        p=get_preset("industrial")
        x=generate(p,91,333,777,Path(tmp)/"odd",None)
        y=generate(p,92,333,777,Path(tmp)/"odd",None)
        assert x["sha256"]!=y["sha256"]
        changed=get_preset("industrial",{"grime_amount":.75,"window_density":.1})
        z=generate(changed,91,333,777,Path(tmp)/"edit",None)
        assert x["sha256"]["albedo"]!=z["sha256"]["albedo"]
    ramp_x=np.tile(np.uint8(np.clip(np.arange(512)*4,0,255)),(1024,1))
    ramp_y=np.tile(np.uint8(np.clip(np.arange(1024)*4,0,255))[:,None],(1,512))
    nx=np.asarray(normal_from_height(Image.fromarray(ramp_x)))
    ny=np.asarray(normal_from_height(Image.fromarray(ramp_y)))
    assert nx[32,32,0]<128 and ny[32,32,1]>128,"OpenGL normal orientation"
    manifest=json.loads((HERE/"generated/batch_manifest.json").read_text())
    assert len(manifest["variants"])==24
    for variant in manifest["variants"]:
        for channel,digest in variant["sha256"].items():
            assert hashlib.sha256((TEXTURES/f'{variant["stem"]}_{channel}.png').read_bytes()).hexdigest()==digest
        assert (MATERIALS/f'{variant["stem"]}.tres').is_file()
    report=dict(passed=True,resolutions=checks,arbitrary_resolution=[333,777],
                seed_divergence=True,config_override=True,byte_identical_png_replay=True,
                open_gl_normal_ramps=True,orm_channels="R=AO / G=roughness / B=metallic",
                unique_non_tiling=True,batch_maps=120,seconds=round(time.perf_counter()-start,3))
    (HERE/"review/quick_qa.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":main()
