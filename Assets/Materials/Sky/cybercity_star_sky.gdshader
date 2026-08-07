shader_type sky;

group_uniforms Sky;
uniform vec4 sky_top_color : source_color = vec4(0.006, 0.012, 0.035, 1.0);
uniform vec4 sky_horizon_color : source_color = vec4(0.045, 0.11, 0.18, 1.0);
uniform float horizon_fade : hint_range(0.02, 1.0, 0.01) = 0.5;

group_uniforms Stars;
uniform float star_density : hint_range(0.0, 0.65, 0.005) = 0.075;
uniform float star_size_min : hint_range(0.002, 0.24, 0.001) = 0.035;
uniform float star_size_max : hint_range(0.002, 0.3, 0.001) = 0.11;
uniform float star_brightness : hint_range(0.0, 12.0, 0.05) = 6.5;
uniform float star_contrast : hint_range(0.25, 8.0, 0.05) = 3.4;
uniform float star_seed : hint_range(0.0, 1000.0, 1.0) = 42.0;
uniform float star_color_variation : hint_range(0.0, 1.0, 0.01) = 0.35;

group_uniforms Twinkle;
uniform float twinkle_strength : hint_range(0.0, 0.5, 0.005) = 0.08;
uniform float twinkle_speed : hint_range(0.0, 5.0, 0.05) = 0.7;

group_uniforms Atmosphere;
uniform float nebula_strength : hint_range(0.0, 1.0, 0.01) = 0.08;

group_uniforms;

const float STAR_GRID_SCALE = 72.0;


float hash12(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * 0.1031);
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.x + value3.y) * value3.z);
}


vec2 hash22(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * vec3(0.1031, 0.1030, 0.0973));
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.xx + value3.yz) * value3.zy);
}


float hash13(vec3 value) {
	value = fract(value * 0.1031);
	value += dot(value, value.zyx + 31.32);
	return fract((value.x + value.y) * value.z);
}


float value_noise_3d(vec3 position) {
	vec3 cell = floor(position);
	vec3 local = fract(position);
	local = local * local * (3.0 - 2.0 * local);

	float lower_back = mix(hash13(cell), hash13(cell + vec3(1.0, 0.0, 0.0)), local.x);
	float lower_front = mix(hash13(cell + vec3(0.0, 0.0, 1.0)), hash13(cell + vec3(1.0, 0.0, 1.0)), local.x);
	float upper_back = mix(hash13(cell + vec3(0.0, 1.0, 0.0)), hash13(cell + vec3(1.0, 1.0, 0.0)), local.x);
	float upper_front = mix(hash13(cell + vec3(0.0, 1.0, 1.0)), hash13(cell + vec3(1.0, 1.0, 1.0)), local.x);
	float lower = mix(lower_back, lower_front, local.z);
	float upper = mix(upper_back, upper_front, local.z);
	return mix(lower, upper, local.y);
}


vec3 cube_face_projection(vec3 direction) {
	vec3 absolute_direction = abs(direction);
	vec2 face_uv;
	float face_index;

	if (absolute_direction.x >= absolute_direction.y && absolute_direction.x >= absolute_direction.z) {
		face_uv = direction.zy / max(absolute_direction.x, 0.0001);
		face_index = direction.x >= 0.0 ? 0.0 : 1.0;
	} else if (absolute_direction.y >= absolute_direction.z) {
		face_uv = direction.xz / max(absolute_direction.y, 0.0001);
		face_index = direction.y >= 0.0 ? 2.0 : 3.0;
	} else {
		face_uv = direction.xy / max(absolute_direction.z, 0.0001);
		face_index = direction.z >= 0.0 ? 4.0 : 5.0;
	}

	return vec3(face_uv, face_index);
}


vec3 star_plane(vec2 direction_plane, float plane_seed, float density_scale) {
	vec2 grid = direction_plane * STAR_GRID_SCALE;
	vec2 cell = floor(grid);
	vec2 local = fract(grid) - 0.5;
	vec2 keyed_cell = cell + vec2(plane_seed * 17.17, plane_seed * 37.31);

	vec2 center = (hash22(keyed_cell) - 0.5) * 0.64;
	float spawn_random = hash12(keyed_cell + 11.83);
	float size_random = hash12(keyed_cell + 47.17);
	float brightness_random = hash12(keyed_cell + 89.41);
	float color_random = hash12(keyed_cell + 137.59);
	float density = clamp(star_density * density_scale, 0.0, 0.95);
	float exists = step(1.0 - density, spawn_random);

	float minimum_size = min(star_size_min, star_size_max);
	float maximum_size = max(star_size_min, star_size_max);
	float accent = smoothstep(0.992, 1.0, brightness_random);
	float radius = mix(minimum_size, maximum_size, size_random) * mix(1.0, 2.2, accent);
	float distance_to_center = length(local - center);
	float antialias_width = max(radius * 0.35, 0.01);
	float disc = 1.0 - smoothstep(radius - antialias_width, radius + antialias_width, distance_to_center);

	float brightness_distribution = pow(brightness_random, max(star_contrast, 0.01));
	float intensity = mix(0.14, 1.0, brightness_distribution) * mix(1.0, 2.4, accent);
	float phase = spawn_random * TAU;
	float twinkle = 1.0 + sin(TIME * twinkle_speed + phase) * twinkle_strength * mix(0.25, 1.0, brightness_random);

	vec3 cool_tint = vec3(0.63, 0.79, 1.0);
	vec3 warm_tint = vec3(1.0, 0.82, 0.64);
	vec3 varied_tint = mix(cool_tint, warm_tint, color_random);
	vec3 star_tint = mix(vec3(0.88, 0.94, 1.0), varied_tint, star_color_variation);
	return star_tint * disc * exists * intensity * star_brightness * max(twinkle, 0.0);
}


void sky() {
	vec3 direction = normalize(EYEDIR);
	float vertical_height = abs(direction.y);
	float horizon_blend = smoothstep(0.0, max(horizon_fade, 0.001), vertical_height);
	vec3 sky_color = mix(sky_horizon_color.rgb, sky_top_color.rgb, horizon_blend);

	vec3 seed_offset = vec3(star_seed * 0.013, star_seed * 0.021, star_seed * 0.034);
	float broad_noise = value_noise_3d(direction * 4.2 + seed_offset);
	float density_scale = mix(0.5, 1.45, smoothstep(0.2, 0.85, broad_noise));

	vec3 face_projection = cube_face_projection(direction);
	vec3 stars = star_plane(face_projection.xy, star_seed + face_projection.z * 23.0, density_scale);

	float star_visibility = smoothstep(0.0, max(horizon_fade * 0.55, 0.03), vertical_height);
	vec3 galactic_axis = normalize(vec3(0.18, 0.42, 0.89));
	float band_distance = abs(dot(direction, galactic_axis));
	float nebula_band = 1.0 - smoothstep(0.12, 0.72, band_distance);
	float nebula_cloud = smoothstep(0.48, 0.82, broad_noise);
	vec3 nebula_color = mix(sky_horizon_color.rgb, vec3(0.16, 0.09, 0.24), 0.35);
	float nebula_visibility = smoothstep(0.0, 0.35, vertical_height);

	COLOR = sky_color + stars * star_visibility;
	COLOR += nebula_color * nebula_strength * nebula_band * nebula_cloud * nebula_visibility;
}
