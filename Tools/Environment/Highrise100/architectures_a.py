"""Original massing grammar: ten purpose-led families, five structural subtypes."""
import math
NAMES={
 'corporate':['Setback Veil','Split Blades','Chamfered Wedge','Triad Court','Offset Atrium'],
 'megablock':['Terraced Cliff','Inhabited Gate','Stacked Districts','Buttressed Slab','Open Courtyard'],
 'industrial':['Chimney Bank','Service Spine','Gantry Works','Heat Exchanger','Stepped Foundry'],
 'residential':['Staggered Slabs','L Court','Cross Estate','Balcony Terraces','Three Neighbours'],
 'hvac':['Vent Mast','Radiator Stack','Cooling Racks','External Ducts','Plenum Fork'],
 'billboard':['Screen Sail','Media Gate','Stacked Channels','Beacon Blade','Crown Display'],
 'arcology':['Terrace Mountain','Hanging District','Twin Mountains','Porous Tripod','Sky Courtyard'],
 'needle':['Tapered Lancet','Bifurcated Needle','Radio Spine','Triple Spires','Offset Pinnacle'],
 'twins':['High Bridge','Double Deck','Hinge Towers','Suspended Transfer','Unequal Partners'],
 'reactor':['Triple Vessels','Cooling Hourglass','Armoured Vessel','Split Drums','Flue Cluster']}

def build(t,key,v,w,d,h):
    t.podium(w*(1.10 if key not in ('arcology','twins') else 1.35),d*1.14,12+v*2)
    if key=='corporate':
        if v==0:
            for k in range(4):
                z0=12+k*h*.235; hh=h*.235
                t.box('Shaft',(k*w*.04,0,z0+hh/2),(w*(1-.14*k),d*(1-.09*k),hh))
                t.band(k*w*.04,0,z0+hh,w*(1-.14*k)+1,d*(1-.09*k)+1)
            t.roof(w*.12,0,h*.95,w*.56,d*.7,0);t.tag('four_setbacks','offset_crown')
        elif v==1:
            for s in (-1,1):
                hh=h*(1 if s==-1 else .78)
                t.box('Blade',(s*w*.29,0,12+hh/2),(w*.34,d,hh))
                t.box('Fin',(s*w*.29-w*.17,-d*.51,12+hh/2),(1,1,hh),'metal')
            t.box('Transfer',(0,0,h*.68),(w*.7,d*.52,9),'secondary');t.tag('split_blade','sky_slot','unequal_heights')
        elif v==2:
            t.taper('Wedge',[(12,w*.56,d*.5,0,0),(h*.72,w*.40,d*.4,w*.07,0),(h,w*.07,d*.35,w*.22,0)],n=4)
            for i in range(6):t.beam('Fins',(-w*.46+i*w*.15,-d*.36,18),(w*.22,-d*.25,h-4),.75)
            t.tag('sloped_crown','chamfered_plan')
        elif v==3:
            for k,(x,y,f) in enumerate([(-.34,.18,.80),(.34,.18,1),(0,-.3,.64)]):
                t.box('Triad',(x*w,y*d,14+h*f/2),(w*.36,d*.45,h*f))
                t.roof(x*w,y*d,14+h*f,w*.36,d*.45,k)
            t.box('AtriumLink',(0,0,h*.36),(w*.8,d*.54,8),'glass');t.tag('three_shafts','open_court')
        else:
            t.box('Lower',(0,0,h*.3),(w,d,h*.6))
            t.box('Upper',(w*.17,d*.02,h*.79),(w*.7,d*.82,h*.42),'secondary')
            t.box('GlassAtrium',(-w*.42,-d*.28,h*.66),(w*.16,d*.28,h*.35),'glass')
            for y in (-d*.3,d*.3):t.beam('TransferBrace',(-w*.35,y,h*.42),(w*.5,y,h*.7),2.2)
            t.roof(w*.17,0,h,w*.7,d*.82,4);t.tag('offset_cantilever','attached_atrium')
    elif key=='megablock':
        if v==0:
            for k in range(5):
                hh=h/5;t.box('Terraces',(0,k*d*.065,12+(k+.5)*hh),(w*(1-.12*k),d*(1-.11*k),hh),'facade')
                t.band(0,k*d*.065,12+(k+1)*hh,w*(1-.12*k)+3,d*(1-.11*k)+3,2,'concrete')
            t.tag('five_terraces','wide_footprint')
        elif v==1:
            for s in (-1,1):t.box('GateLeg',(s*w*.34,0,h*.5),(w*.3,d,h))
            t.box('InhabitedLintel',(0,0,h*.85),(w,d,h*.3));t.tag('giant_void','inhabited_lintel')
        elif v==2:
            t.box('Core',(0,d*.14,h*.5),(w*.45,d*.6,h),'concrete')
            for k in range(4):t.box('District',(((-1)**k)*w*.12,-d*.06,20+h*(.1+.22*k)),(w*(.75+.06*k),d,h*.18),'facade' if k%2==0 else 'secondary')
            t.tag('offset_districts','expressed_core')
        elif v==3:
            t.box('Cliff',(0,0,h*.5),(w,d*.75,h))
            for x in (-w*.42,0,w*.42):
                t.box('Buttress',(x,-d*.46,h*.34),(w*.11,d*.34,h*.68),'concrete')
                t.roof(x,-d*.46,h*.68,w*.11,d*.34,1)
            t.tag('deep_buttresses','service_ledges')
        else:
            for s in (-1,1):
                t.box('CourtWing',(s*w*.38,0,h*.5),(w*.24,d,h))
                t.box('CourtLink',(0,s*d*.40,h*(.28 if s==-1 else .42)),(w,d*.2,h*(.56 if s==-1 else .84)))
            t.tag('courtyard_plan','uneven_perimeter')
        if v==4:t.roof(w*.38,0,h,w*.22,d*.6,v)
        elif v!=2:t.roof(0,0,12+h if v==0 else h,w*.3,d*.6,v)
    elif key=='industrial':
        if v==0:
            t.box('Plant',(0,0,h*.31),(w,d,h*.62),'service')
            for i in range(3):
                x=(i-1)*w*.3;hh=h*(.35+i*.08)
                t.cylinder('Flue',(x,0,h*.62+hh/2),w*.085,hh,'metal',10)
                t.cylinder('FlueCap',(x,0,h*.62+hh),w*.1,2,'concrete')
            t.tag('chimney_trio','low_service_base')
        elif v==1:
            t.box('Spine',(w*.26,d*.17,h*.5),(w*.34,d*.55,h),'service')
            for k in range(5):
                z=20+k*h*.18;t.box('Yard',(-w*.12,0,z),(w*.8,d,8),'metal')
                t.box('Works',(-w*.15,d*.12,z+13),(w*.60,d*.65,20),'facade')
            t.tag('external_service_yards','offset_spine')
        elif v==2:
            for x in (-w*.4,w*.4):t.box('GantryLeg',(x,0,h*.47),(w*.16,d*.6,h*.94),'service')
            t.box('GantryHead',(0,0,h*.91),(w*1.15,d*.86,h*.17),'facade')
            for k in range(3):t.box('HangingWorks',(0,0,h*(.22+k*.20)),(w*.6,d*.6,h*.12),'secondary')
            for x in (-w*.25,w*.25):t.beam('Hangers',(x,0,h*.3),(x,0,h*.94),1.5)
            t.tag('open_gantry','suspended_works')
        elif v==3:
            t.box('Exchanger',(0,0,h*.5),(w*.65,d*.65,h),'service')
            for x in (-w*.42,w*.42):
                for y in (-d*.25,0,d*.25):t.cylinder('Pipe',(x,y,h*.45),w*.045,h*.9,'metal',8)
            for z in range(20,int(h),18):t.band(0,0,z,w,d,2)
            t.tag('six_exposed_pipes','regular_service_rings')
        else:
            for k in range(3):
                hh=h*(.45+k*.27);x=(k-1)*w*.29
                t.box('Foundry',(x,0,hh/2),(w*.34,d*(1-k*.12),hh),'facade')
                t.roof(x,0,hh,w*.34,d*(1-k*.12),2)
            t.tag('stepped_parallel_works','unequal_roofs')
    elif key=='residential':
        if v==0:
            for k in range(4):t.box('Slab',((-.15 if k%2==0 else .15)*w,0,12+(k+.5)*h/4),(w*.8,d,h/4))
            t.tag('alternating_slabs','staggered_edges')
        elif v==1:
            t.box('LongWing',(0,d*.2,h*.5),(w,d*.4,h))
            t.box('ShortWing',(-w*.3,-d*.18,h*.37),(w*.4,d*.76,h*.74),'secondary');t.tag('L_plan','two_roof_levels')
        elif v==2:
            t.box('CrossA',(0,0,h*.5),(w,d*.3,h))
            t.box('CrossB',(0,0,h*.41),(w*.3,d,h*.82),'secondary');t.tag('cross_plan','tall_central_mass')
        elif v==3:
            for k in range(6):
                hh=h/6;t.box('Step',(0,k*d*.08,12+(k+.5)*hh),(w,d*(1-.10*k),hh))
                t.band(0,k*d*.08,12+(k+1)*hh,w+4,d*(1-.10*k)+4,1.5,'concrete')
            t.tag('six_habitable_terraces','receding_depth')
        else:
            for k in range(3):
                hh=h*(.60+.19*k);x=(k-1)*w*.42
                t.box('Neighbour',(x,(k%2)*d*.2,hh/2),(w*.32,d*.7,hh))
                t.roof(x,(k%2)*d*.2,hh,w*.32,d*.7,k)
            t.tag('three_detached_slabs','varied_slab_heights')
        if v!=4:
            for k in range(1,int(h/8)):
                z=k*8
                if v in (1,2):t.band(0,d*.2 if v==1 else 0,z,w+1,d*(.4 if v==1 else .3)+1,.55,'concrete')
            t.roof(0,d*.15,h+12 if v in (0,3) else h,w*.5,d*.3,v)
    elif key=='hvac':
        if v==0:
            t.box('Mast',(0,0,h*.5),(w*.55,d*.7,h),'service')
            for k in range(5):
                z=h*(.16+k*.17);t.box('VentPod',(((-1)**k)*w*.32,0,z),(w*.4,d*.8,h*.1),'secondary')
            t.tag('alternating_vent_pods','narrow_mast')
        elif v==1:
            t.box('Core',(0,0,h*.5),(w*.52,d*.55,h),'service')
            for k in range(12):t.band(0,0,15+k*h*.078,w*(1-k*.025),d,3.0,'metal')
            t.tag('radiator_plates','tapered_plate_stack')
        elif v==2:
            for x in (-w*.38,w*.38):t.box('RackSupport',(x,0,h*.5),(w*.15,d*.7,h),'metal')
            for k in range(6):
                z=18+k*h*.16;t.band(0,0,z,w,d,2)
                for x in (-w*.2,w*.2):t.cylinder('CoolingCan',(x,0,z+h*.065),w*.16,h*.13,'service')
            t.tag('exposed_cooling_rack','paired_cylinders')
        elif v==3:
            t.box('Shaft',(0,0,h*.48),(w*.67,d*.62,h*.96),'facade')
            for i in range(4):
                x=-w*.39+i*w*.26
                t.cylinder('Duct',(x,-d*.43,h*.47),w*.075,h*.86,'metal',8)
                t.beam('DuctElbow',(x,-d*.43,h*.90),(x,0,h*.98),w*.15,'metal')
            t.tag('four_external_ducts','elbow_crown')
        else:
            for s in (-1,1):
                t.box('ForkLeg',(s*w*.32,0,h*.42),(w*.3,d*.7,h*.84),'service')
                t.box('Plenum',(s*w*.32,0,h*.85),(w*.48,d,h*.25),'secondary')
            t.box('LowerLink',(0,0,h*.25),(w,d*.65,12),'metal');t.tag('plenum_fork','oversized_vent_crowns')
    elif key=='billboard':
        if v==0:
            t.box('SailShaft',(0,d*.12,h*.5),(w*.65,d*.66,h))
            t.screen(0,-d*.30,h*.51,w*.82,h*.67,v)
            t.box('ServiceBlade',(w*.42,d*.05,h*.56),(w*.15,d*.8,h*.9),'service');t.tag('single_screen_sail','service_blade')
        elif v==1:
            for s in (-1,1):t.box('MediaLeg',(s*w*.36,0,h*.48),(w*.23,d,h*.96),'secondary')
            t.box('Crown',(0,0,h*.89),(w,d,h*.22))
            t.screen(0,-d*.52,h*.89,w*.88,h*.16,v);t.tag('media_portal','screen_lintel')
        elif v==2:
            t.box('Core',(0,0,h*.5),(w*.6,d*.8,h),'service')
            for k in range(4):
                x=(-.16 if k%2==0 else .16)*w;z=h*(.16+.22*k)
                t.box('MediaFloor',(x,0,z),(w*.9,d,h*.16))
                t.screen(x,-d*.52,z,w*.68,h*.12,k)
            t.tag('stacked_media_blocks','alternating_overhangs')
        elif v==3:
            t.taper('Blade',[(12,w*.5,d*.5,0,0),(h*.7,w*.33,d*.45,w*.1,0),(h,w*.12,d*.3,w*.23,0)],n=6)
            for k in range(3):t.screen(w*.08,-d*.43,h*(.25+k*.22),w*(.5-k*.08),h*.17,k)
            t.tag('tapered_beacon','vertical_ad_sequence')
        else:
            t.box('Shaft',(0,0,h*.4),(w*.7,d*.75,h*.8))
            for x in (-w*.3,w*.3):t.box('CrownSupport',(x,0,h*.83),(w*.1,d*.55,h*.2),'metal')
            t.box('DisplayCrown',(0,0,h*.92),(w*1.18,d,h*.19),'service')
            t.screen(0,-d*.52,h*.92,w*1.05,h*.15,v);t.tag('oversized_screen_crown','narrow_neck')
    elif key=='arcology':
        if v==0:
            for k in range(7):
                a=1-k*.105;t.box('District',(0,0,12+(k+.5)*h/7),(w*a,d*a,h/7),'facade' if k%2==0 else 'secondary')
                t.band(0,0,12+(k+1)*h/7,w*a+3,d*a+3,2,'concrete')
            t.tag('seven_terrace_pyramid','district_belts')
        elif v==1:
            for x in (-w*.37,w*.37):t.box('Core',(x,0,h*.5),(w*.18,d*.8,h),'service')
            for k in range(3):
                z=h*(.28+.27*k);t.box('HangingDistrict',(0,0,z),(w*1.1,d*(1-.12*k),h*.17))
            t.tag('suspended_districts','exposed_twin_cores')
        elif v==2:
            for s in (-1,1):
                for k in range(4):
                    hh=h*(.22 if s==-1 else .26);x=s*w*(.30+.02*k)
                    t.box('Mountain',(x,0,12+(k+.5)*hh),(w*(.5-.065*k),d*(1-.12*k),hh))
            t.box('Link',(0,0,h*.5),(w*.52,d*.25,8),'metal');t.tag('twin_stepped_mountains','middle_link')
        elif v==3:
            for x,y in [(-w*.35,d*.24),(w*.35,d*.24),(0,-d*.38)]:
                t.box('TripodLeg',(x,y,h*.37),(w*.2,d*.25,h*.74),'service')
            t.box('UpperDistrict',(0,0,h*.82),(w,d,h*.29));t.tag('three_piers','raised_city_block')
        else:
            for x in (-w*.4,w*.4):t.box('CourtTower',(x,0,h*.5),(w*.24,d*.75,h))
            for y in (-d*.4,d*.4):t.box('SkyCourtLink',(0,y,h*.78),(w,d*.22,h*.2),'secondary')
            t.box('LowerCourt',(0,d*.30,h*.3),(w,d*.3,h*.3));t.tag('open_sky_courtyard','two_link_elevations')
    elif key=='needle':
        if v==0:
            t.taper('Lancet',[(12,w*.5,d*.5,0,0),(h*.72,w*.28,d*.28,0,0),(h,w*.025,d*.025,0,0)],n=8)
            t.tag('octagonal_lancet','sharp_tip')
        elif v==1:
            t.taper('Base',[(12,w*.5,d*.5,0,0),(h*.52,w*.32,d*.3,0,0)],n=6)
            t.box('ForkTransfer',(0,0,h*.51),(w*1.6,d*.7,8),'metal')
            for s in (-1,1):
                t.taper('Fork',[(h*.5,w*.27,d*.32,s*w*.65,0),(h*(.87 if s==1 else 1.03),w*.06,d*.10,s*w*.65,0)],n=4)
                t.beam('ForkBrace',(s*w*.2,0,h*.37),(s*w*.65,0,h*.52),1.5)
            t.tag('bifurcated_tip','six_sided_base')
        elif v==2:
            t.box('ServiceNeedle',(0,0,h*.42),(w*.52,d*.58,h*.84),'service')
            for k in range(4):t.band(0,0,h*(.2+.19*k),w*(.9-k*.13),d*(.9-k*.13),3,'metal')
            t.antenna(0,0,h*.84,h*.24);t.tag('radio_spine','diminishing_platforms')
        elif v==3:
            for k,(x,y,scale) in enumerate([(-.3,.18,.85),(.3,.18,1),(0,-.3,.71)]):
                t.taper('Spire',[(12,w*.20,d*.22,x*w,y*d),(h*scale,w*.03,d*.04,x*w,y*d)],n=6)
            t.tag('triple_tapered_spires','triangular_plan')
        else:
            t.box('ContinuousNeedle',(0,d*.08,h*.5),(w*.32,d*.38,h),'service')
            for k in range(3):
                z=h*(.25+k*.27);x=(-1 if k%2 else 1)*w*.30
                t.box('OffsetPod',(x,0,z),(w*(1.22-k*.17),d*.80,h*.11))
                t.beam('PodBrace',(0,0,z-h*.14),(x,0,z-h*.045),1.8)
            t.antenna(0,d*.08,h,h*.08);t.tag('three_large_offset_pods','continuous_service_needle')
    elif key=='twins':
        gap=w*(.30 if v==3 else .20);bw=w*.38
        height_a=h*(.83 if v in (2,4) else 1);height_b=h*(.72 if v in (0,4) else .95)
        for x,hh in [(-gap-bw/2,height_a),(gap+bw/2,height_b)]:
            t.box('Tower',(x,0,hh/2),(bw,d*(.78 if x>0 and v==2 else 1),hh),'facade' if x<0 else 'secondary')
            t.roof(x,0,hh,bw,d,v)
        levels=[[.63],[.34,.72],[.47],[.77],[.26,.56]][v]
        for j,z in enumerate(levels):
            depth=d*([.32,.46,.72,.64,.3][v]);t.box('Skybridge',(0,0,h*z),(gap*2+bw,depth,8+v*2),'metal')
            t.box('BridgeHabitat',(0,0,h*z+5),(gap*2+bw,depth*.86,6),'glass')
            for x in (-gap,gap):t.beam('BridgeBrace',(x*1.6,0,h*z-20),(0,0,h*z),2.1)
        if v==2:t.box('HingeCore',(0,d*.33,h*.32),(gap*1.3,d*.25,h*.64),'service')
        if v==3:
            for x in (-gap,gap):t.beam('Suspension',(x,0,h*.95),(0,0,h*.76),1.7)
        t.tag(['single_high_bridge','two_bridge_levels','hinged_core','suspended_deck','unequal_partners'][v],'separate_shafts')
    elif key=='reactor':
        if v==0:
            for k in range(3):
                x=(k-1)*w*.30;hh=h*(.7+.14*k)
                t.cylinder('Vessel',(x,0,hh/2),w*.18,hh,'service')
                for z in (hh*.25,hh*.6,hh*.94):t.cylinder('Collar',(x,0,z),w*.2,3,'metal')
            t.tag('three_pressure_vessels','unequal_cylinders')
        elif v==1:
            t.taper('CoolingShell',[(12,w*.57,d*.57,0,0),(h*.4,w*.27,d*.27,0,0),(h*.85,w*.36,d*.36,0,0),(h,w*.46,d*.46,0,0)],'service',12)
            for k in range(8):
                a=k*math.tau/8;t.beam('CoolingRib',(w*.54*math.cos(a),d*.54*math.sin(a),14),(w*.27*math.cos(a),d*.27*math.sin(a),h*.4),1.7)
            t.tag('hourglass_shell','splayed_lower_ribs')
        elif v==2:
            t.cylinder('ArmouredCore',(0,0,h*.46),w*.36,h*.92,'service',10)
            for k in range(5):
                z=h*(.15+k*.17);t.cylinder('ArmourRing',(0,0,z),w*.49,h*.10,'concrete',10)
            t.antenna(0,0,h*.92,h*.12);t.tag('armoured_ring_stack','central_vessel')
        elif v==3:
            for s in (-1,1):
                t.cylinder('Drum',(s*w*.29,0,h*(.46 if s==-1 else .35)),w*.22,h*(.92 if s==-1 else .7),'service')
            t.box('ControlLink',(0,0,h*.51),(w,d*.33,16),'facade');t.tag('split_drums','control_bridge')
        else:
            for k in range(7):
                a=math.radians(-35+k*38);x=math.cos(a)*w*.43;y=math.sin(a)*d*.43;hh=h*(.68+.05*(k%3))
                t.box('HollowShell',(x,y,hh/2),(w*.24,d*.34,hh),'service',rot=math.degrees(a))
                t.cylinder('ShortFlue',(x,y,hh+8+k),w*.05,16+2*k,'metal',8)
            t.box('AttachedControl',(w*.45,-d*.28,h*.23),(w*.28,d*.35,h*.46),'facade');t.tag('hollow_industrial_court','segmented_shell','short_flues')
