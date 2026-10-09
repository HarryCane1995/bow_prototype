"""Authored defaults shared by WebLab and the reproducible production batch."""
from surface_archetypes import CATALOG

PALETTES = {
 'WALL_CORPORATE':'CORPORATE_CYAN','WALL_DARK_CONCRETE':'COLD_MONO',
 'WALL_REACTOR_HOUSING':'BLACK_RED_TECH','WALL_PAINTED_UTILITY':'WARNING_ORANGE',
 'FLOOR_HAZARD_CROSSING':'WARNING_ORANGE','FLOOR_DAMP_CONCRETE':'DIRTY_CONCRETE',
 'FLOOR_SERVICE_WALKWAY':'OXIDIZED_GREEN','CEILING_LIGHT_BAFFLE':'COLD_MONO',
 'WRAP_REACTOR_CORE':'CORPORATE_CYAN','WRAP_COOLANT_CHAMBER':'BLACK_RED_TECH',
 'WRAP_INSULATED_PIPE':'DIRTY_CONCRETE','ACCENT_HAZARD_SKIN':'WARNING_ORANGE',
 'ACCENT_CONTROL_CONSOLE':'INDUSTRIAL_GREEN','ACCENT_DARK_MONOLITH':'BLACK_RED_TECH',
}


def authored_request(name):
    item=CATALOG[name]; category=item['category']; wrap=category=='wrap'
    i=list(CATALOG).index(name)
    params=dict(circumference_modules=6+(i%3)*2,vertical_band_count=3+(i%3),ring_density=.25,
        vertical_seam_count=4,service_hatch_density=.16,emission_band_density=.08,pipe_grime_flow=.48) if wrap else dict(
        panel_scale=1,grout_width=2,seam_visibility=.30,floor_markings_density=.08,wall_module_density=.18)
    palette=PALETTES.get(name,{'cold':'NEUTRAL_COLD','industrial':'INDUSTRIAL_GREEN','concrete':'DIRTY_CONCRETE'}[item['palette']])
    result=dict(preset=name,surface_mode='CYLINDER_WRAP' if wrap else 'TILEABLE_SURFACE',
        tile_mode='HORIZONTAL_WRAP_ONLY' if wrap else 'FULL_2D_TILE',seed=4100+i*37,
        palette=item['palette'],resolution=[512,1024] if wrap else [512,512],parameters=params,
        art=dict(profile='BOW_BASE',material_mix=1,weathering=.18,overrides=dict(panel_outline_strength=.1,
            seam_contrast=.28,detail_contrast=.25,baked_lighting_strength=.12,module_irregularity=.25)),
        breakup=dict(mode='LAYERED',export_mode='BAKED',macro_variation=.18,
            grime=.22 if category=='floor' else .14,micro_grain=.025,retro_artifacts=0),
        palette_mix=dict(enabled=True,preset=palette,albedo_influence=.82,emission_influence=.85,
            weather_tint_influence=.15,material_variation_influence=.4,accent_usage=.75,
            colored_balance=.8,structural_separation=.65,orm_influence=.65))
    if name=='WALL_DARK_CONCRETE':result['palette_mix']['colors']=dict(BASE='#353d40',SECONDARY='#495154')
    if name=='FLOOR_DAMP_CONCRETE':
        result['palette_mix']['material_responses']={'CONCRETE':{'roughness':.62}}
        result['palette_mix']['colors']=dict(BASE='#585e59',SECONDARY='#656960')
    return result
