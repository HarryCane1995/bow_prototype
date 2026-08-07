shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

group_uniforms Facade;
uniform vec4 building_color : source_color = vec4(0.004, 0.009, 0.018, 1.0);
uniform vec4 window_color : source_color = vec4(0.12, 0.72, 1.0, 1.0);
uniform vec4 secondary_window_color : source_color = vec4(0.56, 0.22, 1.0, 1.0);
uniform float window_size : hint_range(0.2, 6.0, 0.05) = 1.6;
uniform float window_spacing : hint_range(0.1, 6.0, 0.05) = 1.4;
uniform float window_lit_ratio : hint_range(0.0, 1.0, 0.01) = 0.22;
uniform float window_brightness : hint_range(0.0, 20.0, 0.1) = 4.5;
uniform float window_seed : hint_range(0.0, 1000.0, 1.0) = 37.0;
uniform float window_color_variation : hint_range(0.0, 1.0, 0.01) = 0.3;

group_uniforms Flicker;
uniform float flicker_strength : hint_range(0.0, 0.5, 0.005) = 0.0;
uniform float flicker_speed : hint_range(0.0, 5.0, 0.05) = 0.35;

group_uniforms;

varying vec3 world_position;
varying vec3 world_normal;


float hash12(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * 0.1031);
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.x + value3.y) * value3.z);
}


void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}


void fragment() {
	vec3 absolute_normal = abs(world_normal);
	float vertical_face = 1.0 - smoothstep(0.55, 0.9, absolute_normal.y);
	float use_world_z = step(absolute_normal.z, absolute_normal.x);
	float horizontal_position = mix(world_position.x, world_position.z, use_world_z);

	float cell_size = max(window_size + window_spacing, 0.05);
	vec2 facade_grid = vec2(horizontal_position, world_position.y) / cell_size;
	vec2 window_cell = floor(facade_grid);
	vec2 local_position = fract(facade_grid) - 0.5;
	float horizontal_half_size = clamp(window_size / cell_size, 0.04, 0.94) * 0.5;
	float vertical_half_size = clamp((window_size * 0.68) / cell_size, 0.04, 0.9) * 0.5;
	float edge_softness = 0.025;
	float inside_x = 1.0 - smoothstep(horizontal_half_size - edge_softness, horizontal_half_size + edge_softness, abs(local_position.x));
	float inside_y = 1.0 - smoothstep(vertical_half_size - edge_softness, vertical_half_size + edge_softness, abs(local_position.y));
	float window_shape = inside_x * inside_y * vertical_face;

	float face_seed = mix(19.0, 43.0, use_world_z);
	vec2 randomized_cell = window_cell + vec2(window_seed * 11.17 + face_seed, window_seed * 23.41 - face_seed);
	float lit_random = hash12(randomized_cell);
	float color_random = hash12(randomized_cell + 71.37);
	float phase_random = hash12(randomized_cell + 137.19);
	float lit_window = step(1.0 - window_lit_ratio, lit_random);
	float rare_flicker_window = step(0.9, phase_random);
	float flicker = 1.0 + sin(TIME * flicker_speed + phase_random * TAU) * flicker_strength * rare_flicker_window;

	vec3 varied_window_color = mix(window_color.rgb, secondary_window_color.rgb, color_random);
	vec3 final_window_color = mix(window_color.rgb, varied_window_color, window_color_variation);
	float emission_mask = window_shape * lit_window;

	ALBEDO = mix(building_color.rgb, final_window_color * 0.08, emission_mask);
	METALLIC = 0.18;
	ROUGHNESS = 0.78;
	EMISSION = final_window_color * emission_mask * window_brightness * max(flicker, 0.0);
}
