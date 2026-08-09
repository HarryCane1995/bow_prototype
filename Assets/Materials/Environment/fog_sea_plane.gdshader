shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

group_uniforms Appearance;
uniform vec4 fog_color : source_color = vec4(0.25, 0.52, 0.64, 1.0);
uniform float opacity : hint_range(0.0, 1.0, 0.01) = 0.18;
uniform float master_opacity : hint_range(0.0, 1.0, 0.01) = 1.0;
uniform float threshold : hint_range(0.0, 1.0, 0.01) = 0.40;
uniform float softness : hint_range(0.01, 0.5, 0.01) = 0.22;

group_uniforms Noise;
uniform float noise_scale : hint_range(0.00005, 0.01, 0.00005) = 0.0005;
uniform float detail_scale : hint_range(1.0, 8.0, 0.05) = 2.4;
uniform float detail_strength : hint_range(0.0, 1.0, 0.01) = 0.25;

group_uniforms Motion;
uniform vec2 wind_direction = vec2(0.92, 0.38);
uniform float wind_speed : hint_range(0.0, 20.0, 0.1) = 4.0;
uniform float secondary_speed : hint_range(0.0, 2.0, 0.01) = 0.72;

group_uniforms Blending;
uniform float depth_fade_distance : hint_range(0.0, 100.0, 0.5) = 24.0;
uniform bool depth_fade_enabled = true;
uniform float view_angle_fade : hint_range(0.0, 0.5, 0.01) = 0.14;
uniform float distance_fade_start : hint_range(0.0, 5000.0, 10.0) = 450.0;
uniform float distance_fade_end : hint_range(0.0, 5000.0, 10.0) = 1100.0;
uniform float downward_fill_start : hint_range(0.0, 1.0, 0.01) = 0.18;
uniform float downward_fill_end : hint_range(0.0, 1.0, 0.01) = 0.55;
uniform float downward_fill_strength : hint_range(0.0, 1.0, 0.01) = 1.0;

group_uniforms;

uniform sampler2D depth_texture : hint_depth_texture, repeat_disable, filter_nearest;

varying vec3 world_position;


float hash12(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * 0.1031);
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.x + value3.y) * value3.z);
}


float value_noise(vec2 position) {
	vec2 cell = floor(position);
	vec2 local = fract(position);
	vec2 blend = local * local * (3.0 - 2.0 * local);

	float bottom_left = hash12(cell);
	float bottom_right = hash12(cell + vec2(1.0, 0.0));
	float top_left = hash12(cell + vec2(0.0, 1.0));
	float top_right = hash12(cell + vec2(1.0, 1.0));
	return mix(mix(bottom_left, bottom_right, blend.x), mix(top_left, top_right, blend.x), blend.y);
}


void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}


void fragment() {
	vec2 safe_wind_direction = length(wind_direction) > 0.0001 ? normalize(wind_direction) : vec2(1.0, 0.0);
	vec2 base_position = (world_position.xz + safe_wind_direction * TIME * wind_speed) * noise_scale;
	vec2 detail_direction = vec2(-safe_wind_direction.y, safe_wind_direction.x);
	vec2 detail_position = (world_position.xz + detail_direction * TIME * wind_speed * secondary_speed) * noise_scale * detail_scale;

	float base_noise = value_noise(base_position);
	float detail_noise = value_noise(detail_position);
	float density_noise = mix(base_noise, base_noise * 0.72 + detail_noise * 0.28, detail_strength);
	float noise_alpha = smoothstep(threshold - softness, threshold + softness, density_noise);

	float camera_distance = distance(world_position.xz, CAMERA_POSITION_WORLD.xz);
	float distance_alpha = smoothstep(distance_fade_start, max(distance_fade_end, distance_fade_start + 0.001), camera_distance);

	vec3 view_direction = normalize(CAMERA_POSITION_WORLD - world_position);
	float vertical_alignment = abs(view_direction.y);
	float angle_alpha = view_angle_fade > 0.0001
		? mix(0.30, 1.0, smoothstep(0.0, view_angle_fade, vertical_alignment))
		: 1.0;
	float downward_alignment = max(view_direction.y, 0.0);
	float downward_fill = smoothstep(
		downward_fill_start,
		max(downward_fill_end, downward_fill_start + 0.001),
		downward_alignment
	) * downward_fill_strength;

	float intersection_alpha = 1.0;
	if (depth_fade_enabled && depth_fade_distance > 0.001) {
		float scene_depth_sample = textureLod(depth_texture, SCREEN_UV, 0.0).r;
		vec4 scene_position = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, scene_depth_sample, 1.0);
		scene_position.xyz /= scene_position.w;
		float scene_depth = -scene_position.z;
		float fragment_depth = -(VIEW_MATRIX * vec4(world_position, 1.0)).z;
		intersection_alpha = smoothstep(0.0, depth_fade_distance, scene_depth - fragment_depth);
	}

	float procedural_alpha = opacity * noise_alpha * distance_alpha * angle_alpha;
	float coverage_alpha = mix(procedural_alpha, 1.0, downward_fill) * master_opacity;
	ALBEDO = fog_color.rgb;
	ALPHA = fog_color.a * coverage_alpha * intersection_alpha;
}
