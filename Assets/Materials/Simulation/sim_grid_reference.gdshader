shader_type spatial;
render_mode diffuse_burley, specular_schlick_ggx;

group_uniforms Appearance;
uniform vec4 base_color : source_color = vec4(0.003, 0.008, 0.010, 1.0);
uniform vec4 grid_color : source_color = vec4(0.035, 0.920, 0.590, 1.0);
uniform float cell_size : hint_range(0.1, 8.0, 0.05) = 1.0;
uniform float line_width : hint_range(0.005, 0.2, 0.001) = 0.025;
uniform float emission_strength : hint_range(0.0, 8.0, 0.05) = 2.2;

group_uniforms Animation;
uniform float scan_speed : hint_range(-4.0, 4.0, 0.05) = 0.35;
uniform float scan_strength : hint_range(0.0, 2.0, 0.01) = 0.35;
uniform float noise_strength : hint_range(0.0, 0.25, 0.005) = 0.025;

varying vec3 sim_world_position;
varying vec3 sim_world_normal;


float grid_on_plane(vec2 position) {
	vec2 cell = position / max(cell_size, 0.001);
	vec2 edge_distance = min(fract(cell), 1.0 - fract(cell));
	vec2 antialias = max(fwidth(cell) * 0.75, vec2(0.0005));
	vec2 line = 1.0 - smoothstep(
		vec2(line_width) - antialias,
		vec2(line_width) + antialias,
		edge_distance
	);
	return max(line.x, line.y);
}


float digital_noise(vec3 position) {
	vec3 cell = floor(position / max(cell_size * 0.25, 0.001));
	float time_step = floor(TIME * 2.0);
	return fract(sin(dot(cell, vec3(12.9898, 78.233, 37.719)) + time_step) * 43758.5453);
}


void vertex() {
	sim_world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	sim_world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}


void fragment() {
	vec3 weights = pow(abs(normalize(sim_world_normal)), vec3(8.0));
	weights /= max(weights.x + weights.y + weights.z, 0.0001);

	float grid = grid_on_plane(sim_world_position.yz) * weights.x;
	grid += grid_on_plane(sim_world_position.xz) * weights.y;
	grid += grid_on_plane(sim_world_position.xy) * weights.z;
	grid = clamp(grid, 0.0, 1.0);

	float scan_wave = 0.5 + 0.5 * sin(
		sim_world_position.y / max(cell_size * 2.5, 0.001) * TAU
		- TIME * scan_speed * TAU
	);
	float scan_pulse = pow(scan_wave, 12.0) * scan_strength;
	float noise = (digital_noise(sim_world_position) - 0.5) * noise_strength;

	ALBEDO = mix(base_color.rgb, grid_color.rgb * 0.22, grid);
	EMISSION = grid_color.rgb * grid * emission_strength * (1.0 + scan_pulse);
	EMISSION += grid_color.rgb * max(noise, 0.0);
	METALLIC = 0.05;
	ROUGHNESS = 0.68;
}
