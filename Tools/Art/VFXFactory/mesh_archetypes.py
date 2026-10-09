"""Ten authored effect families. Recipes select topology, not just a color/seed."""
import copy


SHAPE_CONTROLS = {
    'effect_length': [.3, 8, .05, 4, 'Length / reach · m', 'EFFECT SHAPE'],
    'effect_radius': [.15, 5, .05, 2, 'Radius / spread · m', 'EFFECT SHAPE'],
    'effect_width': [.015, .6, .005, .07, 'Strand / band width · m', 'EFFECT SHAPE'],
    'effect_count': [3, 48, 1, 16, 'Primary element count', 'EFFECT SHAPE'],
    'effect_segments': [3, 24, 1, 10, 'Path segments', 'EFFECT SHAPE'],
    'effect_jitter': [0, 1, .01, .3, 'Path irregularity', 'EFFECT SHAPE'],
    'effect_arc': [.1, 4, .05, 1.4, 'Arc height / rise · m', 'EFFECT SHAPE'],
    'effect_lifetime': [.08, 5, .02, 1, 'Element lifetime · s', 'EFFECT SHAPE'],
    'effect_stagger': [0, 1, .01, .08, 'Start stagger · s', 'EFFECT SHAPE'],
    'effect_motion': [0, 4, .05, 1, 'Travel multiplier', 'EFFECT SHAPE'],
}


def spec(label, slug, description, seed, enabled, colors, parameters, controls, sample):
    layers = {name: {'enabled': name in enabled} for name in ('core','petals','ring','shards','smoke','dust')}
    for layer, pair in colors.items():
        layers[layer].update(color=pair[0], color_b=pair[1])
    return dict(label=label, slug=slug, description=description, seed=seed, layers=layers,
                parameters=parameters, shape_controls=controls.split(), sample_time=sample)


EFFECTS = {
 'MESH_EXPLOSION_3D': spec('01 · Industrial burst','industrial_burst',
    'Faceted core, curled fire shells, shock ring, ballistic shards and smoke.', 1101,
    ['core','petals','ring','shards','smoke'], {}, {}, '', .24),
 'SHOCK_RING': spec('02 · Pressure shock rings','pressure_shock_rings',
    'Three staggered volumetric bands and a serrated pressure crown.', 1102,
    ['core','ring','shards'], {'ring':('#65d9bf','#286c9b'),'shards':('#beefd9','#3b9790')},
    {'duration':1.6,'effect_radius':3.3,'effect_width':.12,'effect_count':18,'effect_lifetime':1.2,'effect_stagger':.12},
    'effect_radius effect_width effect_count effect_lifetime effect_stagger', .38),
 'SPARK_BURST': spec('03 · Electric spark burst','electric_spark_burst',
    'Radial needle sparks with short bent tails and cold electrode flash.', 1103,
    ['core','shards','petals'], {'core':('#ddffff','#72dcff'),'shards':('#a8f3ff','#247dcc'),'petals':('#368fb8','#8adbff')},
    {'duration':1.3,'effect_count':28,'effect_radius':2.8,'effect_width':.045,'effect_length':.7,'effect_lifetime':.65,'effect_jitter':.35},
    'effect_radius effect_width effect_length effect_count effect_lifetime effect_jitter effect_motion', .22),
 'DIRECTIONAL_LIGHTNING': spec('04 · Directional lightning','directional_lightning',
    'Solid zigzag strike from +Y to origin, with tapered branching forks.', 1104,
    ['core','petals','shards','ring'], {'core':('#efffff','#b9c6ff'),'petals':('#aad9ff','#615dda'),'shards':('#7967e4','#ceeeff'),'ring':('#8ab4e4','#6050a2')},
    {'duration':1.3,'effect_length':4.7,'effect_width':.065,'effect_segments':13,'effect_jitter':.46,'effect_count':6,'effect_lifetime':.48,'effect_stagger':.09},
    'effect_length effect_width effect_segments effect_jitter effect_count effect_lifetime effect_stagger', .2),
 'ARC_CLUSTER': spec('05 · Arcing electricity','arcing_electricity',
    'Curved electrical bridges between a hub and spatially separated terminals.', 1105,
    ['core','petals','shards'], {'core':('#e4ffee','#65e7ad'),'petals':('#65e7c0','#2b7495'),'shards':('#c5ffd7','#329b80')},
    {'duration':2,'effect_radius':2.3,'effect_count':7,'effect_width':.045,'effect_segments':15,'effect_arc':1.7,'effect_jitter':.2,'effect_lifetime':1.15,'effect_stagger':.16},
    'effect_radius effect_count effect_width effect_segments effect_arc effect_jitter effect_lifetime effect_stagger', .35),
 'LASER_IMPACT': spec('06 · Laser impact flare','laser_impact_flare',
    'Short +Z incoming beam, axial flare spikes and upright impact rings.', 1106,
    ['core','petals','ring','shards'], {'core':('#fff3c7','#fff8e8'),'petals':('#ff793a','#ffcf73'),'ring':('#ed5732','#fcae48'),'shards':('#ffe8a3','#ff592e')},
    {'duration':1.2,'effect_length':3.8,'effect_radius':1.35,'effect_width':.06,'effect_count':10,'effect_lifetime':.68},
    'effect_length effect_radius effect_width effect_count effect_lifetime', .19),
 'PROJECTILE_TRAIL': spec('07 · Projectile streak','projectile_streak',
    'Tapered comet filaments and delayed energy beads along the local -Z wake.', 1107,
    ['core','petals','shards'], {'core':('#ecfbff','#77dbe6'),'petals':('#389bbd','#bbf9dc'),'shards':('#547db4','#b2f2e6')},
    {'duration':1.8,'effect_length':5.2,'effect_radius':.5,'effect_width':.07,'effect_segments':16,'effect_count':9,'effect_arc':.45,'effect_jitter':.08,'effect_lifetime':1.3,'effect_motion':.5},
    'effect_length effect_radius effect_width effect_segments effect_count effect_arc effect_jitter effect_lifetime effect_motion', .3),
 'ENERGY_ORB': spec('08 · Energy orb discharge','energy_orb_discharge',
    'Faceted plasma sphere, three spatial orbital bands and radial satellites.', 1108,
    ['core','ring','shards'], {'core':('#b1f4cf','#3877a0'),'ring':('#94f1d9','#31599e'),'shards':('#dbffca','#62b9b3')},
    {'duration':2.2,'core_size':.75,'core_lifetime':1,'effect_radius':2.3,'effect_width':.045,'effect_count':14,'effect_lifetime':1.5,'effect_motion':1},
    'effect_radius effect_width effect_count effect_lifetime effect_motion', .42),
 'SMOKE_BURST': spec('09 · Dissipating smoke','dissipating_smoke',
    'Layered rising low-poly smoke lobes and a ground-hugging dust skirt.', 1109,
    ['smoke','dust'], {'smoke':('#8c9892','#4e625e'),'dust':('#707c73','#3d4b49')},
    {'duration':3.8,'effect_radius':1.8,'effect_arc':2.6,'effect_count':15,'effect_lifetime':3.1,'effect_stagger':.3,'smoke_darkness':.15,'smoke_puff_size':.8,'effect_motion':1},
    'effect_radius effect_arc effect_count effect_lifetime effect_stagger effect_motion', 1.05),
 'DEBRIS_SCATTER': spec('10 · Debris and hot sparks','debris_spark_scatter',
    'Solid irregular metal chunks on ballistic paths with trailing hot fragments.', 1110,
    ['shards','petals','dust'], {'shards':('#b6a48b','#4d615f'),'petals':('#efb462','#bd4b29'),'dust':('#626d63','#323f3e')},
    {'duration':2.4,'effect_radius':3,'effect_count':24,'effect_width':.16,'effect_length':.7,'effect_lifetime':1.6,'effect_motion':1.1,'effect_arc':2.3},
    'effect_radius effect_width effect_length effect_count effect_lifetime effect_motion effect_arc', .42),
}


def defaults(effect):
    value = EFFECTS[effect]
    return copy.deepcopy(dict(effect=effect, seed=value['seed'], parameters=value['parameters'], layers=value['layers']))
