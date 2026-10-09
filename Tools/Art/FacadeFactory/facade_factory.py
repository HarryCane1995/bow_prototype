"""BowPrototype deterministic facade sheets. No network or image generation models.

python Tools/Art/FacadeFactory/facade_factory.py --batch
python Tools/Art/FacadeFactory/facade_factory.py --preset corporate --seed 42 --width 512 --height 1024
"""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from facade_presets import PRESETS, PALETTES, get_preset
from facade_stylizer import normal_from_height, stylize
from facade_semantics import SemanticLayers
from facade_art_profiles import apply_art, normalized_art

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEXTURES = ROOT / "Assets/Textures/Levels/Level_01/FacadeFactory"
MATERIALS = ROOT / "Assets/Materials/Environment/FacadeFactory"
SEEDS = (17, 42, 103, 271)
VERSION = "0.4.0"
STRUCTURE_RNG_VERSION = "0.1.0"  # Frozen: release/art changes must not reseed architecture.
# Albedo colors are sRGB. Material data values are linear 8-bit values.
SURFACES = {"concrete": (244, 222, 0, 132), "paint": (242, 182, 28, 140),
            "metal": (240, 137, 178, 155), "glass": (224, 88, 0, 85),
            "recess": (155, 224, 0, 62), "dirty": (215, 240, 0, 120)}


def fork_rng(seed, label):
    digest = hashlib.sha256(f"{STRUCTURE_RNG_VERSION}:{seed}:{label}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def tint(color, factor):
    return tuple(max(0, min(255, round(c * factor))) for c in color)


class Facade:
    def __init__(self, preset, seed):
        self.p, self.seed = preset, seed
        self.pal = PALETTES[preset.palette]
        self.albedo = Image.new("RGB", (512, 1024), self.pal["base"])
        self.emission = Image.new("RGB", (512, 1024))
        self.height = Image.new("L", (512, 1024), 128)
        self.orm = Image.new("RGB", (512, 1024), (245, 194, 20))
        self.draws = [ImageDraw.Draw(i) for i in (self.albedo, self.emission, self.height, self.orm)]
        self.window_states = Counter()
        self.groups = []
        self.sign_count = 0
        self.font = ImageFont.load_default(size=10)
        self.semantic = SemanticLayers((512,1024),seed,preset.name,self.pal)

    def rect(self, box, color, surface="paint", emission=None, height=None, outline=False, edge=False):
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        if x1 < x0 or y1 < y0:
            return
        bounds = (x0, y0, x1, y1)
        ao, rough, metal, h = SURFACES[surface]
        self.draws[0].rectangle(bounds, fill=color)
        self.draws[1].rectangle(bounds, fill=emission or (0, 0, 0))
        self.draws[2].rectangle(bounds, fill=h if height is None else height)
        self.draws[3].rectangle(bounds, fill=(ao, rough, metal))
        self.semantic.rect(bounds,color,surface,outline,edge,emission)

    def panel(self, box, rng, material="paint", vents=False):
        x0, y0, x1, y1 = box
        c = tint(self.pal["metal" if material == "metal" else "base"], rng.uniform(.92, 1.12))
        context = self.semantic.begin(box,'vent' if vents else 'panel',c)
        self.rect(box, self.pal["recess"], "recess", outline=True)
        self.rect((x0+2, y0+3, x1-2, y1-2), c, material)
        self.rect((x0+2, y0+2, x1-2, y0+3), tint(c, 1.26), material, edge=True)
        self.rect((x0+2, y0+4, x0+3, y1-2), tint(c, 1.1), material, edge=True)
        if vents:
            for yy in range(int(y0+7), int(y1-4), 5):
                self.rect((x0+7, yy, x1-7, yy+2), self.pal["recess"], "recess")
                self.rect((x0+7, yy+3, x1-7, yy+3), tint(c, 1.15), "metal")
        elif x1-x0 > 36 and y1-y0 > 22:
            # Sparse hatch corners, a single latch, not a greeble per pixel.
            for xx in (x0+5, x1-6):
                self.rect((xx, y0+7, xx+1, y0+8), tint(c, 1.35), "metal")
            self.rect((x1-10, (y0+y1)/2, x1-7, (y0+y1)/2+5), self.pal["recess"], "metal")
        self.semantic.end(context)

    def window(self, box, state, rng, warm=False):
        self.window_states[state] += 1
        x0,y0,x1,y1 = box
        context = self.semantic.begin(box,'window',self.pal['base'])
        self.rect(box, self.pal["recess"], "recess")
        palette = self.pal["warm" if warm else "accent"]
        light = {"OFF": 0, "DIM": .13, "ON": .52, "BRIGHT": .90, "SERVICE": .64,
                 "BLOCKED": 0, "BROKEN/DARK": 0}[state]
        if state in ("BLOCKED", "BROKEN/DARK"):
            c = tint(self.pal["base"], .64) if state == "BLOCKED" else (14, 23, 27)
        elif light:
            c = tint(palette, .43 + light * .50)
        else:
            c = tint(self.pal["glass"], rng.uniform(.85, 1.23))
        e = tint(palette, light)
        self.rect((x0+2,y0+2,x1-2,y1-2), c, "glass", e)
        self.rect((x0+2,y1-1,x1,y1), tint(self.pal["metal"], .85), "metal")
        if state == "BLOCKED":
            for y in range(int(y0+4), int(y1-2), 4):
                self.rect((x0+2,y,x1-2,y), tint(c,.65), "paint")
        elif state == "BROKEN/DARK":
            self.draws[0].line([(x0+2,y0+2), ((x0+x1)/2,(y0+y1)/2),(x1-3,y0+3)], fill=tint(self.pal["glass"],1.2), width=1)
        else:
            # A top reflection and a blind/desk band imply an interior cluster.
            self.rect((x0+2,y0+2,x1-2,y0+3), tint(c,1.15), "glass", tint(e,.82))
            if x1-x0 > 17:
                self.rect(((x0+x1)/2,y0+2,(x0+x1)/2,y1-2), tint(c,.5), "metal")
            if rng.random() < .28:
                self.rect((x0+2,y1-5,x1-2,y1-4), tint(c,.56), "glass", tint(e,.45))
        self.semantic.end(context)

    def sign(self, x, y, text, rng, lit=False):
        width = int(self.font.getlength(text)) + 12
        self.rect((x,y,x+width,y+18), self.pal["recess"], "recess")
        self.rect((x,y,x+2,y+18), self.pal["warm"], "paint")
        self.draws[0].text((x+7,y+3),text,font=self.font,fill=tint(self.pal["concrete"],1.45))
        self.semantic.draws['signage'].text((x+7,y+3),text,font=self.font,fill=255)
        if lit:
            self.draws[1].text((x+7,y+3),text,font=self.font,fill=tint(self.pal["accent"],.65))
            self.semantic.draws['emission_role'].text((x+7,y+3),text,font=self.font,fill=1)
        self.sign_count += 1

    def strip(self, x0, x1, y, warm=False):
        color = self.pal["warm" if warm else "accent"]
        self.rect((x0,y-2,x1,y+5),self.pal["recess"],"recess")
        self.rect((x0+3,y,x1-3,y+2),tint(color,.85),"glass",tint(color,.9))

    def service(self, x0, x1, y0, y1, rng):
        self.rect((x0,y0,x1,y1), self.pal["recess"], "recess")
        count = max(1,int((x1-x0)/58))
        for i in range(count):
            left = x0+5+i*(x1-x0-10)/count
            self.panel((left,y0+4,left+(x1-x0-10)/count-4,y1-5),rng,"metal",True)
        if rng.random() < .58:
            self.strip(x0+8,min(x1-6,x0+28),y0+4,True)

    def wear(self, box, rng):
        x0,y0,x1,y1=box
        # Streaks originate at ledges. Low-opacity dust changes albedo and roughness.
        overlay=Image.new("RGBA",(512,1024)); d=ImageDraw.Draw(overlay)
        for _ in range(int(self.p.grime_amount*12)):
            x=rng.uniform(x0+3,x1-3); length=rng.uniform(5, min(38,y1-y0))
            d.polygon([(x,y0+2),(x+3,y0+2),(x+1,y0+length)], fill=(16,24,24,int(70*self.p.grime_amount)))
        if not getattr(self, 'layered_material', False):
            self.albedo.paste(Image.alpha_composite(self.albedo.convert("RGBA"),overlay).convert("RGB"))

    def generate(self):
        p,pal = self.p,self.pal
        rng=fork_rng(self.seed,p.name+":macro")
        grammar=p.grammar
        # Macro widths are coherent for the entire height, then subdivided in groups.
        if grammar == "industrial":
            edges=[12,122+rng.randint(-8,8),350+rng.randint(-12,12),500]
        elif grammar == "landmark":
            edges=[12,100+rng.randint(-12,12),312+rng.randint(-18,18),500]
        else:
            bays=4 if grammar in ("corporate","office") else 3
            edges=[12+i*488/bays for i in range(bays+1)]
        group_count=max(8,min(20,round(950/(p.floor_height*(2.5 if grammar!="office" else 2.2)))))
        group_h=950/group_count
        for group in range(group_count):
            gr=fork_rng(self.seed,p.name+f":group:{group}")
            top,bottom=36+group*group_h,36+(group+1)*group_h-3
            dark=gr.random()<p.dark_floor_frequency
            service=gr.random()<p.service_floor_frequency
            occupied=max(.03,min(.92,p.emission_density+gr.uniform(-.25,.25)))
            record=dict(index=group,dark=dark,service=service,occupancy=round(occupied,3),zones=[])
            self.groups.append(record)
            for zone,(a,b) in enumerate(zip(edges,edges[1:])):
                zr=fork_rng(self.seed,p.name+f":group:{group}:zone:{zone}")
                x0,x1=a+p.structural_width/2,b-p.structural_width/2
                self.rect((x0,top,x1,bottom), tint(pal["base"],zr.uniform(.88,1.1)),"concrete" if grammar=="megablock" else "paint")
                zone_occ=max(.01,min(.97,occupied+zr.uniform(-.16,.16)))
                record["zones"].append(round(zone_occ,3))
                if service and (grammar!="corporate" or zone==1):
                    self.service(x0,x1,top+3,bottom-4,zr)
                else:
                    rows=max(1,round((bottom-top)/p.floor_height))
                    floor_h=(bottom-top)/rows
                    for row in range(rows):
                        yy=top+row*floor_h+4
                        wh=floor_h*(.55 if grammar=="megablock" else .74)
                        desired_w=max(10,wh*p.window_aspect)
                        count=max(1,int((x1-x0)/(desired_w+6)))
                        cell=(x1-x0)/count
                        # Neighbour cells inherit a small shared occupancy cluster.
                        cluster_on=zr.random()<zone_occ
                        for col in range(count):
                            if col%3==0:
                                cluster_on=zr.random()<zone_occ
                            xx=x0+col*cell+2
                            window_box=(xx,yy,xx+cell-5,yy+wh)
                            has_window=zr.random()<p.window_density
                            if grammar=="landmark" and zone==0:
                                has_window=False
                            if not has_window:
                                self.panel(window_box,zr,vents=zr.random()<p.panel_density*.65)
                                continue
                            v=zr.random()
                            if dark:
                                state="OFF"
                            elif v<.035:
                                state="BROKEN/DARK"
                            elif v<.09:
                                state="BLOCKED"
                            elif v<.115:
                                state="SERVICE"
                            elif cluster_on:
                                state="BRIGHT" if v>.90 else "ON"
                            else:
                                state="DIM" if v<.48 else "OFF"
                            self.window(window_box,state,zr,warm=(zone==len(edges)-2 and gr.random()<.23))
                        self.rect((x0,yy+wh+2,x1,yy+wh+4),tint(pal["metal"],.55),"metal")
                if grammar=="megablock":
                    # Thick continuous floor aprons + irregular deep missing bays.
                    self.rect((a, bottom-5,b,bottom+2),pal["concrete"],"concrete",height=165)
                    self.rect((a,bottom+3,b,bottom+6),pal["recess"],"recess")
                    if zr.random()<.23:
                        self.rect((x0,top+4,x0+(x1-x0)*.48,bottom-9),tint(pal["recess"],.63),"recess")
                self.wear((x0,top,x1,bottom),zr)
                if zr.random()<p.signage_density*.26:
                    self.sign(x0+4,bottom-19,zr.choice([f"A-{self.seed%89:02}",f"SECTOR {group:02}","CTRL","MAINT","GRID","NODE"]),zr,service)
            if grammar in ("office","corporate"):
                self.rect((12,bottom+1,500,bottom+3),tint(pal["metal"],.7),"metal")
            if grammar=="industrial" and group%4==1:
                self.rect((edges[1]+12,bottom-6,edges[2]-12,bottom),pal["warm"],"paint")
                for x in range(int(edges[1]+12),int(edges[2]-16),14):
                    self.rect((x,bottom-6,x+6,bottom),pal["recess"],"paint")
            if (service or grammar=="megablock") and gr.random()<.27:
                self.strip(18,edges[1]-8,top+2)
        # Primary uninterrupted structure is drawn over the secondary modules.
        for idx,x in enumerate(edges):
            sw=p.structural_width
            c=pal["concrete"] if grammar in ("megablock","exoskeleton") else pal["metal"]
            self.rect((x-sw/2,28,x+sw/2,992),tint(c,.82),"concrete" if grammar=="megablock" else "metal",height=176)
            self.rect((x-sw/2,28,x-sw/2+2,992),tint(c,1.24),"metal",height=181)
            if grammar=="corporate" and idx in (1,len(edges)-2):
                self.rect((x+sw/2+1,40,x+sw/2+3,974),pal["recess"],"recess")
                for group in range(2,group_count-1,4):
                    self.rect((x+sw/2+1,38+group*group_h,x+sw/2+2,38+(group+1)*group_h),tint(pal["accent"],.65),"glass",tint(pal["accent"],.48))
        if grammar=="industrial":
            for x in (edges[1]-15,edges[2]+12):
                self.rect((x-9,32,x+9,989),pal["recess"],"recess")
                for offset,bright in [(-6,.6),(-3,.95),(2,1.25),(5,.65)]:
                    self.rect((x+offset,32,x+offset+3,989),tint(pal["metal"],bright),"metal",height=190)
                for y in range(65,970,62):
                    self.rect((x-10,y,x+10,y+5),tint(pal["base"],1.45),"metal",height=202)
        if grammar=="exoskeleton":
            for i in range(5):
                y0,y1=34+i*190,34+(i+1)*190
                pairs=[((18,y0),(494,y1)),((494,y0),(18,y1))]
                for start,end in pairs:
                    width=int(p.structural_width*.72)
                    for draw,fill in zip(self.draws,[pal["recess"],(0,0,0),170,(216,150,165)]):
                        draw.line([start,end],fill=fill,width=width+7)
                    self.draws[0].line([start,end],fill=pal["metal"],width=width)
                    self.draws[0].line([(start[0]-3,start[1]),(end[0]-3,end[1])],fill=tint(pal["metal"],1.37),width=2)
                    self.semantic.brace(start,end,width)
                self.rect((12,y1-3,500,y1+4),pal["metal"],"metal",height=179)
        if grammar=="landmark":
            x=edges[1]*.55
            self.rect((x-19,52,x+19,974),pal["recess"],"recess")
            for i in range(6):
                y0=70+i*143
                self.rect((x-10,y0,x+7,y0+101),tint(pal["accent"],.76),"glass",tint(pal["accent"],.92))
                self.rect((x+9,y0,x+11,y0+74),pal["metal"],"metal")
            for i in (3,8):
                y=36+i*group_h
                self.rect((edges[1]+8,y-18,479,y+16),pal["recess"],"recess")
                self.strip(edges[1]+14,480,y-5)
                self.sign(edges[1]+22,y+5,"NODE / 07",rng,True)
        # Designed unique sheet boundaries, no tile claim. Dark roof/base lips.
        self.rect((0,0,511,26),pal["recess"],"recess")
        self.rect((0,24,511,28),pal["metal"],"metal")
        self.rect((0,994,511,1023),tint(pal["base"],.6),"concrete")
        self.sign(25,3,f"{rng.choice(['AX','KM','NEX','IO'])}-{self.seed%100:02}",rng)
        self.sign(402,999,"UNIT 8",rng)
        return self


def resource_path(path):
    try:
        return "res://"+path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        raise ValueError("Godot materials require --output inside this project; use --no-material for external output")


def write_material(path, stem, out, preset):
    channels=("albedo","emission","normal","orm")
    entries='\n'.join(f'[ext_resource type="Texture2D" path="{resource_path(out / (stem+"_"+c+".png"))}" id="{i+1}"]' for i,c in enumerate(channels))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(f'''[gd_resource type="ORMMaterial3D" load_steps=5 format=3]

{entries}

[resource]
resource_name = "{stem}"
albedo_texture = ExtResource("1")
orm_texture = ExtResource("4")
normal_enabled = true
normal_texture = ExtResource("3")
normal_scale = 0.55
ao_enabled = true
ao_light_affect = 0.2
emission_enabled = true
emission = Color(1, 1, 1, 1)
emission_operator = 1
emission_texture = ExtResource("2")
emission_energy_multiplier = {preset.emission_strength}
texture_filter = 5
texture_repeat = false
uv1_scale = Vector3(1, 1, 1)
''',encoding="utf-8")


def generate(preset, seed, width=512, height=1024, output=TEXTURES, materials=MATERIALS, art=None, breakup=None, palette_mix=None):
    if not 64 <= width <= 4096 or not 128 <= height <= 8192 or width*height>16_777_216:
        raise ValueError("Supported dimensions: width 64..4096, height 128..8192, <=16M pixels")
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if materials is not None:
        resource_path(output)
    from surface_breakup import normalized_breakup, clean_material, finish_layers
    breakup=normalized_breakup(breakup)
    f=Facade(preset,seed)
    f.layered_material=breakup['mode']=='LAYERED'
    f.generate()
    # Architecture is resolution independent; pixel density is deliberately retro.
    # Stylize once in design space, then resize all channels with aligned sampling.
    maps,art_recipe,art_stats=(clean_material(f,art) if f.layered_material else apply_art(f,art))
    from palette_mixer import apply_palette, normalized_palette
    f.palette_mix=normalized_palette(palette_mix,preset.palette)
    if f.palette_mix['enabled'] and not f.layered_material: raise ValueError('Palette Mixer requires Layered pipeline')
    maps=apply_palette(f,maps,f.palette_mix)
    maps={k:v.resize((width,height),Image.Resampling.NEAREST) for k,v in maps.items()}
    maps["normal"]=normal_from_height(maps["height"])
    maps=finish_layers(f,maps,breakup)
    stem=f"{preset.name.lower()}_s{seed}_{width}x{height}"
    hashes={}
    for channel,img in maps.items():
        path=output/f"{stem}_{channel}.png"
        img.save(path,optimize=False,compress_level=6)
        hashes[channel]=hashlib.sha256(path.read_bytes()).hexdigest()
    metadata=dict(version=VERSION,preset=preset.name,seed=seed,resolution=[width,height],
                  config=asdict(preset),floor_groups=f.groups,window_states=dict(f.window_states),
                  signage_count=f.sign_count,tiling="unique sheet / clamp",normal="OpenGL +X +Y +Z",
                  orm={"R":"ambient occlusion","G":"roughness","B":"metallic"},sha256=hashes)
    metadata.update(art=art_recipe,art_statistics=art_stats,breakup=breakup,palette_mix=f.palette_mix,structure_rng_version=STRUCTURE_RNG_VERSION,
                    structure_hash=hashlib.sha256(f.height.tobytes()+f.emission.tobytes()).hexdigest())
    (output/f"{stem}.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    if materials is not None:
        write_material(Path(materials)/f"{stem}.tres",stem,output,preset)
    return dict(stem=stem,albedo=str(output/f"{stem}_albedo.png"),preset=preset.name,seed=seed,sha256=hashes)


def parse_assignments(items, integer_fields=()):
    result={}
    for item in items:
        key,value=item.split("=",1)
        result[key]=int(value) if key in integer_fields else float(value)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preset",default="corporate")
    ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--width",type=int,default=512)
    ap.add_argument("--height",type=int,default=1024)
    ap.add_argument("--output",type=Path,default=TEXTURES)
    ap.add_argument("--materials",type=Path,default=MATERIALS)
    ap.add_argument("--no-material",action="store_true")
    ap.add_argument("--batch",action="store_true",help="6 presets x seeds 17,42,103,271 + contact/box sheets")
    ap.add_argument("--set",action="append",default=[],metavar="FIELD=VALUE")
    ap.add_argument("--style",action="append",default=[],metavar="FIELD=VALUE")
    ap.add_argument("--config",type=Path,help='JSON with "parameters" and/or "style" overrides')
    ap.add_argument("--art-profile",choices=("LEGACY","BOW_BASE"))
    ap.add_argument("--material-mix",type=float,default=1)
    ap.add_argument("--weathering",type=float,default=.6)
    args=ap.parse_args()
    try:
        config=json.loads(args.config.read_text(encoding="utf-8-sig")) if args.config else {}
        params={**config.get("parameters",{}),**parse_assignments(args.set)}
        style={**config.get("style",{}),**parse_assignments(args.style,("posterization","color_quantization"))}
        art=config.get('art')
        if args.art_profile:
            art=normalized_art(dict(profile=args.art_profile,material_mix=args.material_mix,weathering=args.weathering))
        start=time.perf_counter(); variants=[]
        names=list(PRESETS) if args.batch else [args.preset]
        for name in names:
            p=get_preset(name,params,style)
            for seed in SEEDS if args.batch else [args.seed]:
                variants.append(generate(p,seed,args.width,args.height,args.output,None if args.no_material else args.materials,art=art))
        generation_seconds=time.perf_counter()-start
        if args.batch:
            from facade_preview import contact_sheet, box_sheet
            contact_sheet(variants,HERE/"review/FACADE_FACTORY_REVIEW.png")
            box_sheet(variants,HERE/"review/FACADE_BOX_REVIEW.png")
        report=dict(version=VERSION,resolution=[args.width,args.height],variants=variants,
                    generation_seconds=round(generation_seconds,3),total_seconds=round(time.perf_counter()-start,3))
        HERE.joinpath("generated").mkdir(exist_ok=True)
        report_path=HERE/"generated"/("batch_manifest.json" if args.batch else "last_generation.json")
        report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="variants"},indent=2))
        print(f"{len(variants)} facades -> {args.output}")
    except (ValueError,TypeError,KeyError) as ex:
        ap.error(str(ex))


if __name__ == "__main__":
    main()
