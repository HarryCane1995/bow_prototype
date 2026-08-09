shader_type spatial;
render_mode blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

group_uniforms City_Grid;
uniform float grid_spacing : hint_range(8.0, 120.0, 1.0) = 42.0;
uniform float lane_width : hint_range(0.1, 8.0, 0.1) = 1.2;
uniform float road_glow_strength : hint_range(0.0, 1.0, 0.001) = 0.008;
uniform float major_road_frequency : hint_range(2.0, 12.0, 1.0) = 5.0;
uniform float major_road_activity : hint_range(0.25, 3.0, 0.05) = 1.35;

group_uniforms Moving_Lights;
uniform float light_density : hint_range(0.0, 1.0, 0.01) = 0.18;
uniform float light_size : hint_range(0.2, 6.0, 0.1) = 1.4;
uniform float light_streak_length : hint_range(0.2, 18.0, 0.1) = 5.0;
uniform float light_roundness : hint_range(0.0, 1.0, 0.05) = 1.0;
uniform float min_speed : hint_range(0.0, 30.0, 0.1) = 4.0;
uniform float max_speed : hint_range(0.0, 40.0, 0.1) = 10.0;
uniform float brightness : hint_range(0.0, 32.0, 0.1) = 8.0;
uniform float bloom_strength : hint_range(0.0, 4.0, 0.05) = 0.8;

group_uniforms Color;
uniform vec4 primary_color : source_color = vec4(1.0, 0.46, 0.09, 1.0);
uniform vec4 secondary_color : source_color = vec4(0.12, 0.72, 1.0, 1.0);
uniform float secondary_color_chance : hint_range(0.0, 1.0, 0.01) = 0.08;

group_uniforms Stability_And_Fade;
uniform float seed : hint_range(0.0, 9999.0, 1.0) = 731.0;
uniform float distance_fade : hint_range(100.0, 8000.0, 25.0) = 2800.0;

group_uniforms;

varying vec3 world_position;


float hash11(float value) {
	value = fract(value * 0.1031);
	value *= value + 33.33;
	value *= value + value;
	return fract(value);
}


float hash12(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * 0.1031);
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.x + value3.y) * value3.z);
}


float line_mask(float distance_to_line, float width) {
	float antialias_width = max(fwidth(distance_to_line), 0.02);
	return 1.0 - smoothstep(width, width + antialias_width, distance_to_line);
}


float rounded_box_mask(vec2 point, vec2 half_size, float radius) {
	float safe_radius = clamp(radius, 0.0, min(half_size.x, half_size.y));
	vec2 offset = abs(point) - half_size + vec2(safe_radius);
	float signed_distance = length(max(offset, vec2(0.0)))
		+ min(max(offset.x, offset.y), 0.0)
		- safe_radius;
	float antialias_width = max(fwidth(signed_distance), 0.02);
	return 1.0 - smoothstep(0.0, antialias_width, signed_distance);
}


vec4 moving_lane_light(
	float lane_id,
	float distance_to_lane,
	float along_lane,
	float axis_id,
	float major_lane
) {
	float lane_random = hash12(vec2(lane_id + seed * 0.013, axis_id + seed * 0.071));
	float lane_activity = mix(0.32, 1.0, lane_random) * mix(1.0, major_road_activity, major_lane);
	float lane_presence = step(
		hash12(vec2(lane_id * 1.73 + 19.0, axis_id + seed)),
		clamp(0.12 + light_density * 1.45 * lane_activity, 0.0, 0.96)
	);

	float direction = hash12(vec2(lane_id + 37.0, axis_id + seed * 0.19)) < 0.5 ? -1.0 : 1.0;
	float speed_random = hash12(vec2(lane_id - 11.0, axis_id + seed * 0.31));
	float speed = mix(min(min_speed, max_speed), max(min_speed, max_speed), speed_random);
	float slot_period = grid_spacing * mix(0.85, 2.35, hash12(vec2(lane_id + 7.0, axis_id + seed)));
	float lane_phase = hash12(vec2(lane_id * 2.11, axis_id + seed * 0.47)) * slot_period;

	// Every slot has a stable integer ID. TIME only translates its position.
	float moving_coordinate = (along_lane - direction * TIME * speed + lane_phase) / slot_period;
	float slot_id = floor(moving_coordinate + 0.5);
	float signed_slot_distance = (moving_coordinate - slot_id) * slot_period;
	float slot_random = hash12(vec2(slot_id + lane_id * 41.0, axis_id * 113.0 + seed));
	float slot_presence = step(
		slot_random,
		clamp(light_density * lane_activity, 0.0, 0.92)
	);

	float safe_size = max(light_size, 0.001);
	float safe_streak = max(light_streak_length, safe_size);
	float corner_radius = safe_size * clamp(light_roundness, 0.0, 1.0);
	float light_mask = rounded_box_mask(
		vec2(signed_slot_distance, distance_to_lane),
		vec2(safe_streak, safe_size),
		corner_radius
	) * lane_presence * slot_presence;
	float halo_cross_distance = max(distance_to_lane - safe_size, 0.0);
	float halo_along_distance = max(abs(signed_slot_distance) - safe_streak, 0.0);
	float halo_radius = max(safe_size * 4.0, 0.001);
	float halo_mask = exp(
		-(halo_cross_distance * halo_cross_distance + halo_along_distance * halo_along_distance)
		/ (halo_radius * halo_radius)
	) * lane_presence * slot_presence;

	float color_random = hash12(vec2(slot_id - lane_id * 17.0, axis_id + seed * 0.83));
	vec3 light_color = mix(primary_color.rgb, secondary_color.rgb, step(color_random, secondary_color_chance));
	float brightness_phase = hash12(vec2(slot_id + lane_id, axis_id - seed)) * 6.2831853;
	float slow_brightness_variation = 0.88 + 0.12 * sin(TIME * 0.65 + brightness_phase);
	float individual_brightness = mix(0.72, 1.18, hash11(slot_id + lane_id * 5.0 + axis_id + seed));
	float bloom_energy = halo_mask * bloom_strength * 0.18;
	float coverage = clamp(light_mask + halo_mask * bloom_strength * 0.12, 0.0, 1.0);

	return vec4(
		light_color * slow_brightness_variation * individual_brightness * (light_mask + bloom_energy),
		coverage
	);
}


void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}


void fragment() {
	float safe_spacing = max(grid_spacing, 0.001);
	vec2 grid_position = world_position.xz / safe_spacing;
	float x_lane_id = floor(grid_position.y + 0.5);
	float z_lane_id = floor(grid_position.x + 0.5);
	float distance_to_x_lane = abs(world_position.z - x_lane_id * safe_spacing);
	float distance_to_z_lane = abs(world_position.x - z_lane_id * safe_spacing);

	float safe_major_frequency = max(floor(major_road_frequency + 0.5), 1.0);
	float x_major = 1.0 - step(0.5, mod(abs(x_lane_id), safe_major_frequency));
	float z_major = 1.0 - step(0.5, mod(abs(z_lane_id), safe_major_frequency));

	vec4 x_traffic = moving_lane_light(x_lane_id, distance_to_x_lane, world_position.x, 17.0, x_major);
	vec4 z_traffic = moving_lane_light(z_lane_id, distance_to_z_lane, world_position.z, 53.0, z_major);

	float x_road = line_mask(distance_to_x_lane, lane_width * mix(1.0, 1.8, x_major));
	float z_road = line_mask(distance_to_z_lane, lane_width * mix(1.0, 1.8, z_major));
	float road_mask = max(x_road, z_road);

	float camera_distance = distance(world_position.xz, CAMERA_POSITION_WORLD.xz);
	float fade_end = max(distance_fade, 0.001);
	float distance_visibility = 1.0 - smoothstep(fade_end * 0.72, fade_end, camera_distance);
	float light_alpha = clamp(x_traffic.a + z_traffic.a, 0.0, 1.0) * distance_visibility;
	vec3 traffic_emission = (x_traffic.rgb + z_traffic.rgb) * brightness;
	vec3 road_emission = primary_color.rgb * road_mask * road_glow_strength;

	ALBEDO = vec3(0.0);
	EMISSION = (traffic_emission + road_emission) * distance_visibility;
	ALPHA = clamp(light_alpha + road_mask * road_glow_strength, 0.0, 1.0);
}
