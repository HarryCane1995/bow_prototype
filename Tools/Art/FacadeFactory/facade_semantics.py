"""Sidecar semantic buffers. Recording never consumes the architecture RNG."""
import hashlib
from enum import IntEnum
from PIL import Image, ImageDraw


class MaterialClass(IntEnum):
    PAINTED_METAL = 1
    RAW_METAL = 2
    GLASS = 3
    CONCRETE = 4
    VENT = 5
    RECESSED_VOID = 6


class SeamClass(IntEnum):
    DEEP_RECESS = 1
    NORMAL_SEAM = 2
    SUBTLE_JOIN = 3


SURFACE_CLASS = dict(paint=MaterialClass.PAINTED_METAL, metal=MaterialClass.RAW_METAL,
                     glass=MaterialClass.GLASS, concrete=MaterialClass.CONCRETE,
                     dirty=MaterialClass.CONCRETE, recess=MaterialClass.RECESSED_VOID)


class SemanticLayers:
    def __init__(self, size, seed, preset, palette):
        self.seed, self.preset, self.palette = seed, preset, palette
        self.material = Image.new('L', size, int(MaterialClass.PAINTED_METAL))
        self.seam = Image.new('L', size)
        self.outline = Image.new('L', size)
        self.edge = Image.new('L', size)
        self.module = Image.new('I', size)
        self.seam_base = Image.new('RGB', size, palette['base'])
        self.signage = Image.new('L', size)
        self.emission_role = Image.new('L', size)
        self.draws = {k: ImageDraw.Draw(getattr(self, k)) for k in
                      ('material', 'seam', 'outline', 'edge', 'module', 'seam_base','signage','emission_role')}
        self.modules = []
        self.context = None

    def begin(self, box, kind, base):
        key = f'{self.seed}:{self.preset}:{kind}:{tuple(round(v, 3) for v in box)}'
        value = int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big') / 2**32
        seam = (SeamClass.DEEP_RECESS if value < .15 else
                SeamClass.NORMAL_SEAM if value < .57 else SeamClass.SUBTLE_JOIN)
        if kind in ('window', 'vent'):
            seam = SeamClass.DEEP_RECESS
        record = dict(id=len(self.modules)+1, box=list(box), kind=kind, seam=seam.name, finish=value)
        self.modules.append(record)
        old = self.context
        self.context = dict(id=record['id'], kind=kind, seam=seam, base=base)
        return old

    def end(self, previous):
        self.context = previous

    def rect(self, bounds, color, surface, outline=False, edge=False, emission=None):
        context = self.context
        material = SURFACE_CLASS[surface]
        seam = 0
        base = self.palette['base']
        if surface == 'recess':
            seam = context['seam'] if outline and context else SeamClass.DEEP_RECESS
        if context:
            base = context['base']
            if context['kind'] == 'vent' and not outline:
                material = MaterialClass.VENT
        # Thin dark floor joints are joins, not deep empty rooms.
        if surface == 'metal' and bounds[3]-bounds[1] <= 3 and sum(color) < sum(self.palette['metal'])*.78:
            seam = SeamClass.NORMAL_SEAM
            base = self.palette['metal']
        if surface == 'metal' and (bounds[2]-bounds[0] <= 3 or bounds[3]-bounds[1] <= 2):
            edge = edge or sum(color) > sum(self.palette['metal'])*1.06
        def chroma_distance(a,b):
            return sum((x/max(1,max(a))-y/max(1,max(b)))**2 for x,y in zip(a,b))
        marking=surface=='paint' and chroma_distance(color,self.palette['warm'])<.015 and chroma_distance(color,self.palette['warm'])<chroma_distance(color,self.palette['base'])*.5
        light_role=0
        if emission and max(emission)>0:
            light_role=2 if chroma_distance(emission,self.palette['warm'])<chroma_distance(emission,self.palette['accent']) else 1
        for key, value in dict(material=int(material), seam=int(seam), outline=255 if outline else 0,
                               edge=255 if edge else 0, module=context['id'] if context else 0,
                               seam_base=base,signage=255 if marking else 0,emission_role=light_role).items():
            self.draws[key].rectangle(bounds, fill=value)

    def brace(self, start, end, width):
        # Exoskeleton uses direct ImageDraw lines instead of rect().
        for key, value in dict(material=int(MaterialClass.RAW_METAL), seam=0, outline=0,
                               edge=0, module=0,signage=0,emission_role=0).items():
            self.draws[key].line([start, end], fill=value, width=width+7)
        self.draws['edge'].line([(start[0]-3,start[1]), (end[0]-3,end[1])], fill=255, width=2)
