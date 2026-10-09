"""Authored industrial grammars, expressed in the canonical SurfaceCanvas.

References guide construction/scale only: no pixels are sampled or embedded.
Each named recipe changes its assembly, not merely its seed or palette.
"""
import math
from facade_factory import tint

# id, class, visual contract, palette, reference board IDs
ROWS = [
 ('WALL_TECH_SPINE','wall','Offset plates with a central service spine','cold','W02 T05'),
 ('WALL_MAINTENANCE','wall','Wide calm panels with low access hatches','industrial','W01 T06'),
 ('WALL_SERVICE_RACK','wall','Two dense instrument racks around a quiet bay','cold','D01 R05'),
 ('WALL_MEGABLOCK','wall','Staggered cast concrete with embedded tie sockets','concrete','M09 T02'),
 ('WALL_CORPORATE','wall','Broad coated slabs and sparse edge lighting','cold','W04 W05'),
 ('WALL_REINFORCED','wall','Heavy crossing braces over steel plates','industrial','M07 D12'),
 ('WALL_DARK_CONCRETE','wall','Dark concrete bays and narrow cable conduit','concrete','M09 W06'),
 ('WALL_PAINTED_UTILITY','wall','Painted service bands and paired pipe tracks','industrial','W02 R02'),
 ('WALL_REACTOR_HOUSING','wall','Radial coolant ports inside segmented shielding','cold','R08 D10'),
 ('WALL_VENT_BANK','wall','Stacked broad louver banks with maintenance margins','cold','T05 D09'),
 ('WALL_CABLE_RISER','wall','Vertical routed cable ribbons with junction boxes','industrial','R01 D05'),
 ('WALL_TRANSIT_ACOUSTIC','wall','Perforated acoustic bays between blank pilasters','concrete','W11 T09'),
 ('FLOOR_DIAMOND_DECK','floor','Alternating chevron tread in bolted deck plates','industrial','R01 W07'),
 ('FLOOR_METAL_DECK','floor','Long ribbed plates and transverse fastener strips','cold','T03 R02'),
 ('FLOOR_SERVICE_WALKWAY','floor','Clear central route flanked by drain channels','industrial','R01 D15'),
 ('FLOOR_GRATED','floor','Open square grating bounded by load rails','cold','W07 R02'),
 ('FLOOR_ACCESS_TILES','floor','Raised square tiles with alternating lift sockets','cold','W04 R05'),
 ('FLOOR_HAZARD_CROSSING','floor','Restricted crossing with diagonal safety borders','industrial','S03 W06'),
 ('FLOOR_MAINTENANCE','floor','Asymmetric corridor access covers and guide rail','industrial','W01 D15'),
 ('FLOOR_DAMP_CONCRETE','floor','Large concrete pours with dark drainage insets','concrete','R07 T01'),
 ('FLOOR_ROOFTOP','floor','Standing-seam roofing around raised duct covers','cold','M03 R07'),
 ('FLOOR_UTILITY_CUTS','floor','Offset modular cuts with square cable pull boxes','concrete','T02 R07'),
 ('FLOOR_HEX_ARMOR','floor','Hexagonal armored tiles with inset centers','cold','T08 M07'),
 ('FLOOR_DRAINAGE','floor','Parallel drain runs crossed by stamped traction','industrial','R01 R02'),
 ('CEILING_TECH','ceiling','Recessed ceiling cassettes with narrow light strips','cold','W01 L01'),
 ('CEILING_UTILITY','ceiling','Crossing support beams above utility sheet','industrial','W12 R09'),
 ('CEILING_CABLE_TRAY','ceiling','Ladder cable trays and transverse support shoes','industrial','R09 D12'),
 ('CEILING_HATCH','ceiling','Large hinged hatch surrounded by service panels','cold','T09 W12'),
 ('CEILING_VENTILATION','ceiling','Alternating intake filters and long louvers','cold','W12 D09'),
 ('CEILING_LIGHT_BAFFLE','ceiling','Repeated deep baffles with inset practical lights','cold','L01 L09'),
 ('WRAP_HEAVY_PIPE','wrap','Wide flange rings and bolted longitudinal shell','industrial','R01 D10'),
 ('WRAP_TANK_SHELL','wrap','Broad welded tanks with inspection lid and datum band','industrial','R07 R08'),
 ('WRAP_REACTOR_CORE','wrap','Vertical luminous cells isolated by dark cooling fins','cold','R08 D10'),
 ('WRAP_EXOSKELETON','wrap','Diamond load braces around recessed column plates','concrete','D12 M09'),
 ('WRAP_VENT_SHAFT','wrap','Rotating louver banks with heavy coupling rings','cold','D09 R09'),
 ('WRAP_UTILITY_PILLAR','wrap','Service boxes and protected vertical utility routes','industrial','R02 D05'),
 ('WRAP_INSULATED_PIPE','wrap','Segmented insulation jackets with retention straps','concrete','R01 R09'),
 ('WRAP_CONDUIT_CLUSTER','wrap','Bundled unequal conduits with shared ties','cold','D05 R01'),
 ('WRAP_COOLANT_CHAMBER','wrap','Cooling collar stacks interrupted by gauge ports','cold','R08 R02'),
 ('WRAP_PRESSURE_COLUMN','wrap','Overlapping armor scales and sparse status lamps','industrial','D10 R08'),
 ('ACCENT_HAZARD_SKIN','accent','Diagonal restricted-zone paint over service plate','industrial','S03 S08'),
 ('ACCENT_EMISSIVE_PANEL','accent','Inset practical strips around a quiet service panel','cold','L01 T05'),
 ('ACCENT_ACCESS_DOOR','accent','Paired inset door leaves and protected central lock','industrial','T08 S02'),
 ('ACCENT_CONTROL_CONSOLE','accent','Analog gauges, status lamps and switch rows','cold','R05 R06'),
 ('ACCENT_MACHINE_CASING','accent','Offset machine cover, cooling grille and latch rail','industrial','T09 D01'),
 ('ACCENT_SHUTTER','accent','Horizontal interlocking shutter slats and guide rails','cold','T14 D09'),
 ('ACCENT_BILLBOARD_SUPPORT','accent','Support lattice, mounting shoes and cable feed','cold','S04 M08'),
 ('ACCENT_HATCH_CLUSTER','accent','Three differently sized access covers on blank metal','industrial','T05 T09'),
 ('ACCENT_DATACENTER','accent','Tall server modules with intake and status arrays','cold','D01 W04'),
 ('ACCENT_DARK_MONOLITH','accent','Nearly silent stone-like face split by fine light cuts','concrete','M09 L06'),
]
CATALOG = {row[0]: dict(id=row[0].lower(), category=row[1], description=row[2], palette=row[3], references=row[4].split()) for row in ROWS}
TILE_LIBRARY = {k:dict(palette=v['palette']) for k,v in CATALOG.items() if v['category']!='wrap'}
WRAP_LIBRARY = {k:dict(palette=v['palette']) for k,v in CATALOG.items() if v['category']=='wrap'}


class Grammar:
    def __init__(self, f):
        self.f=f; self.w,self.h=f.size; self.p=f.pal; self.rng=f.rng
        self.scale=f.params.get('panel_scale',1)

    def rect(self,x,y,w,h,role='base',mat='paint',z=145,gain=1,light=False):
        c=tint(self.p[role],gain)
        self.f.rect((x,y,x+w,y+h),c,mat,tint(c,.9) if light else None,height=z)

    def line(self,x0,y0,x1,y1,width=4,role='metal',z=161):
        count=max(1,math.ceil(max(abs(x1-x0),abs(y1-y0))))
        for i in range(count+1):
            t=i/count; self.rect(x0+(x1-x0)*t-width/2,y0+(y1-y0)*t-width/2,width,width,role,'metal',z)

    def plate(self,x,y,w,h,mat='paint',vent=False):
        self.f.plate((x,y,x+w,y+h),mat,vent)

    def grid(self,cols,rows,mat='paint',offset=False):
        cols=max(1,round(cols/self.scale));rows=max(1,round(rows/self.scale))
        cw,ch=self.w/cols,self.h/rows
        for row in range(rows):
            for col in range(cols):
                x=(col+(.5 if offset and row%2 else 0))*cw-32;y=row*ch-24
                self.plate(x,y,cw-2,ch-2,mat)

    def vent(self,x,y,w,h,vertical=False,pitch=10):
        self.plate(x,y,w,h,'metal')
        for p in range(8,int(w if vertical else h)-7,pitch):
            self.rect(x+p if vertical else x+8,y+8 if vertical else y+p,2 if vertical else w-16,h-16 if vertical else 3,'recess','recess',109)

    def bolts(self,x,y,w,h,pitch=32):
        for xx in range(int(x+10),int(x+w-4),pitch):
            self.rect(xx,y+4,3,3,'metal','metal',163,.55)
            self.rect(xx,y+h-7,3,3,'metal','metal',163,.55)

    def light(self,x,y,w,h,role='accent'):
        self.rect(x-3,y-3,w+6,h+6,'recess','recess',108)
        self.rect(x,y,w,h,role,'glass',126,.64,True)

    def circle(self,cx,cy,r,role='metal',z=160,thick=4):
        n=max(20,round(r*5))
        for i in range(n):
            a=i/n*math.tau
            self.rect(cx+math.cos(a)*r-thick/2,cy+math.sin(a)*r-thick/2,thick,thick,role,'metal' if role!='recess' else 'recess',z)

    def hazard(self,x,y,w,h,pitch=32):
        self.rect(x,y,w,h,'recess','paint',146)
        for yy in range(int(h)+1):
            for xx in range(-int(h)-pitch,int(w)+pitch,pitch*2):
                left=max(0,xx+yy);right=min(w,xx+yy+pitch)
                if right>left:self.rect(x+left,y+yy,right-left,1,'warm','paint',147,.9)

    def conduit(self,x,y,w,h,count=3):
        for i in range(count):
            self.rect(x+i*w/count,y,w/count*.48,h,'recess','recess',113)
            self.rect(x+i*w/count+2,y,w/count*.38,h,'metal','metal',173,.8+i*.08)
        for yy in range(int(y+24),int(y+h),64):self.rect(x-4,yy,w+4,5,'metal','metal',178,.65)

    def hatch(self,x,y,w,h):
        self.plate(x,y,w,h,'metal');self.plate(x+9,y+9,w-18,h-18)
        for yy in (y+15,y+h-29):self.rect(x-2,yy,11,14,'metal','metal',167,.75)
        self.rect(x+w-22,y+h*.44,4,h*.15,'recess','recess',111)

    def control(self,x,y,w,h):
        self.plate(x,y,w,h,'metal')
        for i in range(3):
            xx=x+w*(i+1)/4;self.circle(xx,y+h*.28,min(w/11,h/7),'recess',112,6)
            self.line(xx,y+h*.28,xx+4,y+h*.28-7,2,'warm',150)
            self.light(xx-2,y+h*.51,4,3,'warm' if i==2 else 'accent')
        for yy in range(int(y+h*.65),int(y+h-8),12):
            for xx in range(int(x+12),int(x+w-10),18):self.rect(xx,yy,6,4,'metal','metal',156,.7)

    def run(self,name):
        key=name.split('_',1)[1]; category=CATALOG[name]['category']
        if category=='wrap':return self.wrap(key)
        f=self.f;p=self.p
        if name in ('WALL_DARK_CONCRETE','ACCENT_DARK_MONOLITH'):
            f.pal={k:tint(v,.52) if k in ('base','concrete','metal') else v for k,v in p.items()};self.p=f.pal
        mat='concrete' if key in ('MEGABLOCK','DARK_CONCRETE','DAMP_CONCRETE','UTILITY_CUTS','DARK_MONOLITH') else 'paint'
        self.rect(0,0,512,512,'concrete' if mat=='concrete' else 'base',mat,134)
        if category=='wall':
            self.grid(2 if key in ('CORPORATE','DARK_CONCRETE','REACTOR_HOUSING') else 3,2 if key!='MEGABLOCK' else 4,mat,key=='MEGABLOCK')
            if key=='TECH_SPINE':
                self.conduit(210,0,38,512);self.hatch(261,168,149,178);self.light(74,76,65,4)
            elif key=='MAINTENANCE':
                for x in (38,288):self.hatch(x,295,170,123)
                self.rect(0,240,512,8,'metal','metal',159,.72)
            elif key=='SERVICE_RACK':
                for x in (20,329):self.control(x,66,154,148);self.vent(x,245,154,219)
                self.conduit(222,0,39,512,2)
            elif key=='MEGABLOCK':
                for y in (44,170,298,426):
                    for x in (53,190,320,446):self.circle(x,y,4,'recess',118,3)
            elif key=='CORPORATE':
                for x in (12,260):self.rect(x,0,5,512,'metal','metal',153,.8);self.light(x+10,42,3,94)
                self.rect(0,440,512,9,'metal','metal',152,.72)
            elif key=='REINFORCED':
                for x in (-256,0,256):self.line(x,0,x+256,512,13);self.line(x+256,0,x,512,13)
                self.rect(0,246,512,18,'metal','metal',175,.8)
            elif key=='DARK_CONCRETE':self.conduit(438,0,28,512,2);self.hatch(318,299,90,104)
            elif key=='PAINTED_UTILITY':
                self.rect(0,130,512,53,'warm','paint',146,.53);self.conduit(56,0,42,512,2);self.hatch(332,282,130,118)
            elif key=='REACTOR_HOUSING':
                for y in (128,384):
                    for x in (128,384):
                        self.circle(x,y,80,'recess',111,11);self.circle(x,y,65,'metal',171,9)
                        for a in range(0,360,45):
                            rad=math.radians(a);self.line(x+math.cos(rad)*37,y+math.sin(rad)*37,x+math.cos(rad)*59,y+math.sin(rad)*59,6)
                        self.light(x-19,y-3,38,6)
            elif key=='VENT_BANK':
                for y in (28,260):self.vent(25,y,462,204,pitch=13)
            elif key=='CABLE_RISER':self.conduit(23,0,115,512,6);self.conduit(402,0,74,512,4);self.hatch(160,67,210,150);self.hatch(195,301,136,139)
            elif key=='TRANSIT_ACOUSTIC':
                for x in (24,190,356):
                    for yy in range(27,482,15):
                        for xx in range(x,x+128,15):self.rect(xx,yy,3,4,'recess','recess',120)
        elif category=='floor':self.floor(key)
        elif category=='ceiling':self.ceiling(key)
        else:self.accent(key)
        # Optional authored service overlays are tied to function and the existing
        # density control, not decorative random texture noise.
        density=f.params.get('floor_markings_density',.1) if category=='floor' else f.params.get('wall_module_density',.35)
        if self.rng.random()<density:
            x=self.rng.randrange(30,450);y=self.rng.randrange(30,450)
            self.rect(x,y,21,7,'warm','paint',147,.72)
        return f

    def floor(self,key):
        if key=='HEX_ARMOR':
            # Four columns, six staggered rows exactly close on the torus.
            # Squashed hex cells preserve a rational repeating domain at 512px.
            for row in range(6):
                yy=row*512/6
                for col in range(4):
                    cx=col*128+(64 if row%2 else 0)
                    ry=512/6*2/3
                    pts=[(cx,yy-ry),(cx+64,yy-ry/2),(cx+64,yy+ry/2),
                         (cx,yy+ry),(cx-64,yy+ry/2),(cx-64,yy-ry/2)]
                    for a,b in zip(pts,pts[1:]+pts[:1]):self.line(*a,*b,5,'recess',113)
                    self.rect(cx-15,yy-7,30,14,'metal','metal',147,.85)
            return
        self.grid(4 if key=='ACCESS_TILES' else 2,4 if key=='ACCESS_TILES' else 2,'concrete' if key in ('DAMP_CONCRETE','UTILITY_CUTS') else 'metal',key=='UTILITY_CUTS')
        if key=='DIAMOND_DECK':
            for y in range(12,512,25):
                for x in range(12,512,27):self.line(x,y,x+8,y+(5 if (x//27+y//25)%2 else -5),2,'metal',152)
        elif key=='METAL_DECK':
            for x in range(14,512,25):self.rect(x,0,3,512,'metal','metal',159,.73)
            for y in (109,365):self.rect(0,y,512,10,'metal','metal',165,.8);self.bolts(0,y-1,512,14)
        elif key in ('SERVICE_WALKWAY','DRAINAGE'):
            for x in ((16,432) if key=='SERVICE_WALKWAY' else (72,230,388)):self.vent(x,0,52,512,pitch=10)
            if key=='SERVICE_WALKWAY':
                for x in (83,418):self.rect(x,0,4,512,'warm','paint',149,.8)
            else:
                for y in range(30,512,32):self.rect(139,y,54,3,'metal','metal',151)
        elif key=='GRATED':
            self.rect(0,0,512,512,'recess','recess',105)
            for x in range(0,512,16):self.rect(x,0,4,512,'metal','metal',151,.9)
            for y in range(0,512,16):self.rect(0,y,512,3,'metal','metal',149,.85)
            for x in (0,250):self.rect(x,0,12,512,'metal','metal',161)
        elif key=='ACCESS_TILES':
            for y in (54,182,310,438):
                for x in (36,164,292,420):self.rect(x,y,12,3,'recess','recess',115);self.rect(x+30,y,12,3,'recess','recess',115)
        elif key=='HAZARD_CROSSING':
            for y in (44,409):self.hazard(0,y,512,43)
            for x in (94,350):self.hatch(x,155,69,186)
        elif key=='MAINTENANCE':self.hatch(31,80,174,253);self.hatch(278,212,165,177);self.rect(226,0,7,512,'warm','paint',148,.77)
        elif key=='DAMP_CONCRETE':
            for y in (224,480):self.vent(0,y,512,27,pitch=8)
            for x in (69,367):self.circle(x,78,9,'recess',116,4)
        elif key=='ROOFTOP':
            for x in range(0,512,51):self.rect(x,0,5,512,'metal','metal',160,.8)
            self.hatch(74,136,139,175);self.vent(304,330,131,114)
        elif key=='UTILITY_CUTS':
            for x,y in ((25,28),(299,276)):self.hatch(x,y,123,141)

    def ceiling(self,key):
        self.grid(2,2)
        if key=='TECH':
            for x in (27,287):self.plate(x,38,192,435,'metal');self.light(x+18,77,5,162)
        elif key=='UTILITY':
            for x in (37,293):self.rect(x,0,19,512,'metal','metal',178,.78)
            for y in (38,294):self.rect(0,y,512,19,'metal','metal',177,.82)
            self.conduit(115,0,62,512,3)
        elif key=='CABLE_TRAY':
            for x in (26,298):
                self.conduit(x,0,144,512,9)
                for y in range(0,512,48):self.rect(x-9,y,164,7,'metal','metal',181,.77)
        elif key=='HATCH':self.hatch(58,57,394,361);self.light(84,454,130,5);self.vent(294,437,157,58)
        elif key=='VENTILATION':
            for y in (25,280):self.vent(23,y,203,201,True);self.vent(282,y,203,201,False)
        elif key=='LIGHT_BAFFLE':
            for x in range(12,512,42):self.rect(x,0,18,512,'recess','recess',109);self.rect(x,0,4,512,'metal','metal',176)
            for y in (98,357):self.light(45,y,414,12)

    def accent(self,key):
        self.grid(1,1)
        if key=='HAZARD_SKIN':
            self.hazard(0,81,512,102,42);self.hazard(0,334,512,48,24);self.hatch(195,199,122,112)
        elif key=='EMISSIVE_PANEL':
            self.hatch(108,67,296,378)
            for x in (35,467):self.light(x,50,8,405)
            self.control(163,164,185,151)
        elif key=='ACCESS_DOOR':
            for x in (28,260):self.plate(x,18,222,477);self.plate(x+25,73,171,310,'metal')
            self.hatch(214,204,81,106);self.light(218,142,75,5)
        elif key=='CONTROL_CONSOLE':
            for y in (18,267):self.control(20,y,297,219);self.vent(343,y,149,218)
        elif key=='MACHINE_CASING':self.hatch(42,46,283,420);self.vent(352,65,118,277,True);self.control(351,371,119,95)
        elif key=='SHUTTER':
            for y in range(0,512,29):self.rect(0,y,512,4,'recess','recess',114);self.rect(0,y+5,512,3,'metal','metal',166,1.08)
            for x in (20,478):self.rect(x,0,14,512,'metal','metal',174,.75)
        elif key=='BILLBOARD_SUPPORT':
            self.line(0,0,512,512,13);self.line(512,0,0,512,13)
            for x in (68,410):self.rect(x,0,30,512,'metal','metal',168,.73)
            for y in (69,402):self.plate(14,y,115,45,'metal');self.plate(383,y,115,45,'metal')
            self.conduit(233,0,31,512,2)
        elif key=='HATCH_CLUSTER':self.hatch(25,24,257,245);self.hatch(310,44,173,154);self.hatch(142,301,276,171)
        elif key=='DATACENTER':
            for x in (14,186,358):
                for y in range(21,492,78):self.vent(x,y,146,63,pitch=7);self.light(x+120,y+10,7,3)
        elif key=='DARK_MONOLITH':self.rect(330,0,5,512,'recess','recess',109);self.light(338,74,2,156);self.rect(0,391,512,2,'metal','metal',138,.7)

    def wrap(self,key):
        f=self.f;p=f.params;h=self.h;n=int(p['circumference_modules']);bands=int(p['vertical_band_count'])
        self.grid(max(3,n),max(1,bands),'metal' if key in ('HEAVY_PIPE','VENT_SHAFT','CONDUIT_CLUSTER') else 'paint')
        if key=='HEAVY_PIPE':
            for y in range(45,h,190):self.rect(0,y-4,512,26,'recess','recess',112);self.rect(0,y,512,18,'metal','metal',183);self.bolts(0,y,512,18,24)
        elif key=='TANK_SHELL':
            self.grid(3,2);self.hatch(59,349,178,226);self.rect(0,783,512,15,'warm','paint',147,.68)
        elif key=='REACTOR_CORE':
            for x in range(10,512,51):self.vent(x,0,35,h,True);self.light(x+14,50,6,h-100)
        elif key=='EXOSKELETON':
            for y in range(0,h,256):
                for x in range(-128,512,128):self.line(x,y,x+128,y+256,13);self.line(x+128,y,x,y+256,13)
        elif key=='VENT_SHAFT':
            for y in range(14,h,204):
                for x in (13,268):self.vent(x,y,230,174,pitch=12)
        elif key=='UTILITY_PILLAR':
            self.conduit(35,0,91,h,4);self.hatch(178,84,220,217);self.control(174,424,226,179);self.hatch(210,736,148,181)
        elif key=='INSULATED_PIPE':
            self.grid(4,7,'concrete',True)
            for y in range(65,h,146):self.rect(0,y,512,11,'metal','metal',165,.83)
            for x in (92,348):self.rect(x,0,8,h,'metal','metal',153,.65)
        elif key=='CONDUIT_CLUSTER':self.rect(0,0,512,h,'recess','recess',111);self.conduit(0,0,512,h,12)
        elif key=='COOLANT_CHAMBER':
            for y in range(18,h,39):self.rect(0,y,512,12,'metal','metal',180,.85);self.rect(0,y+12,512,4,'recess','recess',109)
            for y in (182,687):self.control(102,y,305,135)
        elif key=='PRESSURE_COLUMN':
            for y in range(-35,h,136):
                for x in range(-50,512,128):self.plate(x+(64 if y//136%2 else 0),y,115,152,'metal')
            for y in (237,734):self.light(87,y,65,6,'warm')
        # Common physical controls remain meaningful in every new wrap grammar.
        for i in range(round(p['ring_density']*4)):
            y=(i+.24)*h/max(1,round(p['ring_density']*4));self.rect(0,y,512,7,'metal','metal',170,.76)
        for i in range(int(p['vertical_seam_count'])):
            x=(i+.19)*512/max(1,p['vertical_seam_count']);self.rect(x,0,1,h,'recess','recess',128)
        if self.rng.random()<p['service_hatch_density']:self.hatch(346,319,102,141)
        if self.rng.random()<p['emission_band_density']:self.light(0,h*.64,512,3)
        if not f.periodic[1]:
            self.rect(0,0,512,14,'metal','metal',165,.72);self.rect(0,h-15,512,14,'metal','metal',165,.72)
        return f


def generate_archetype(canvas):
    return Grammar(canvas).run(canvas.name)
