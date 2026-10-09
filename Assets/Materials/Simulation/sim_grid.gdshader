shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

// SIM_GRID is a stable import contract; the visual system need not be a grid.
group_uniforms ArtDirection;
uniform int visual_system : hint_enum("A / Ceramic modules", "B / Isofield", "C / Vector strata") = 0;
uniform vec4 surface_color : source_color = vec4(0.57, 0.60, 0.57, 1.0);
uniform vec4 accent_color : source_color = vec4(1.0, 0.34, 0.10, 1.0);
uniform float structure_scale : hint_range(2.0, 20.0, 0.25) = 8.0;
uniform float structure_contrast : hint_range(0.0, 1.0, 0.01) = 0.45;
uniform float accent_density : hint_range(0.0, 0.6, 0.01) = 0.16;
uniform float emission_strength : hint_range(0.0, 3.0, 0.05) = 0.65;
uniform float motion_speed : hint_range(0.0, 1.0, 0.01) = 0.12;
uniform float distortion : hint_range(0.0, 1.0, 0.01) = 0.35;

varying vec3 world_position;
varying vec3 world_normal;

float hash_cell(vec2 p) {
    vec3 q = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973));
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}
float stroke(float d, float width, float aa) {
    return 1.0 - smoothstep(width - aa, width + aa, d);
}
float box_mask(vec2 p, vec2 center, vec2 half_size, float aa) {
    vec2 d = abs(p - center) - half_size;
    return 1.0 - smoothstep(-aa, aa, max(d.x, d.y));
}
// R = structural darkening, G = accent, B = subtle panel value variation.
vec3 ceramic(vec2 p) {
    vec2 q = p / vec2(structure_scale, structure_scale * 0.5);
    q.x += mod(floor(q.y), 2.0) * 0.5;
    vec2 id = floor(q);
    vec2 f = fract(q);
    float h = hash_cell(id);
    float aa = max(length(fwidth(p)) / structure_scale, 0.0001);
    float fade = 1.0 - smoothstep(0.018, 0.09, aa);
    vec2 edge = min(f, 1.0 - f);
    float joint = stroke(min(edge.x, edge.y * 0.5), 0.006, aa);
    float inset = box_mask(f, vec2(0.78, 0.77), vec2(0.135, 0.065), aa) * step(0.7, h);
    float tag = box_mask(f, vec2(0.10, 0.19), vec2(0.044, 0.017), aa);
    float enabled = step(1.0 - accent_density, hash_cell(id + 61.0));
    float breath = 0.83 + 0.17 * sin(TIME * motion_speed * TAU + h * TAU);
    return vec3((joint * 0.65 + inset * 0.24) * fade, tag * enabled * breath * fade, (h - 0.5) * 0.13 * fade);
}
vec3 vector_strata(vec2 p) {
    vec2 q = p / structure_scale;
    float lane = floor(q.y * 0.55);
    float h = hash_cell(vec2(lane, 7.0));
    // Broad oblique cuts, long calm lanes, a traveling capsule in selected lanes.
    float phase = q.x * 0.34 + q.y * mix(-0.28, 0.28, step(0.5, h));
    float aa = max(length(fwidth(q)), 0.0001);
    float band = 1.0 - smoothstep(0.12 - aa, 0.12 + aa, abs(fract(phase) - 0.5));
    float lane_edge = abs(fract(q.y * 0.55) - 0.5);
    band *= smoothstep(0.05, 0.13, lane_edge);
    float phase_mark = fract(phase - TIME * motion_speed * 0.09 + h);
    float accent = stroke(abs(phase_mark - 0.5), 0.027, aa * 0.4);
    accent *= stroke(abs(lane_edge - 0.28), 0.023, aa * 0.55);
    accent *= step(1.0 - accent_density, h);
    accent *= 1.0 - smoothstep(0.015, 0.07, aa);
    float far_fade = 1.0 - smoothstep(0.06, 0.24, aa);
    return vec3(mix(0.12, band * 0.60, far_fade), accent, (h - 0.5) * 0.10 * far_fade);
}
void vertex() {
    world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}
void fragment() {
    vec3 n = normalize(world_normal);
    vec3 weights = pow(abs(n), vec3(8.0));
    weights /= max(dot(weights, vec3(1.0)), 0.0001);
    vec3 motif;
    if (visual_system == 0) {
        motif = ceramic(world_position.zy) * weights.x;
        motif += ceramic(world_position.xz) * weights.y;
        motif += ceramic(world_position.xy) * weights.z;
    } else if (visual_system == 1) {
        // Continuous 3D scalar field: no projection seams, stationary contours.
        vec3 p = world_position / structure_scale;
        float field = dot(p, vec3(0.55, 0.82, 0.31));
        field += distortion * (sin(p.x * 1.7 + sin(p.z * 1.2)) + sin(p.y * 1.3 - p.z * 0.8));
        float aa = max(fwidth(field), 0.0001);
        float fade = 1.0 - smoothstep(0.035, 0.16, aa);
        float contour = stroke(abs(fract(field) - 0.5), 0.018, aa) * fade;
        float terrace = mix(0.5, smoothstep(0.12, 0.88, fract(field)), fade);
        float signal = 0.5 + 0.5 * sin(field * 0.27 - TIME * motion_speed);
        signal = smoothstep(1.0 - max(accent_density, 0.001) * 0.65, 1.0, signal) * step(0.001, accent_density);
        motif = vec3(contour * 0.62 + terrace * 0.22, contour * signal, terrace * 0.06);
    } else {
        motif = vector_strata(world_position.zy) * weights.x;
        motif += vector_strata(world_position.xz) * weights.y;
        motif += vector_strata(world_position.xy) * weights.z;
    }
    // Broad orientation cue survives when fine markings disappear in the distance.
    float orientation_value = mix(0.78, 1.0, smoothstep(-0.15, 0.85, n.y));
    vec3 body = surface_color.rgb * orientation_value;
    body *= 1.0 + motif.b - motif.r * structure_contrast;
    ALBEDO = mix(body, accent_color.rgb, clamp(motif.g, 0.0, 1.0));
    // Low diffuse-looking fill keeps the simulated solid readable in unlit cavities.
    // Below bloom intensity; lighting and sparse signals remain the brighter terms.
    float fill_shape = 0.65 + 0.35 * max(dot(n, normalize(vec3(0.4, 0.8, 0.3))), 0.0);
    EMISSION = body * 0.22 * fill_shape + accent_color.rgb * motif.g * emission_strength;
    ROUGHNESS = 0.86;
    METALLIC = 0.0;
}
