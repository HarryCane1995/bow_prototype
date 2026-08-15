shader_type spatial;
render_mode unshaded, fog_disabled, cull_disabled, depth_draw_never, depth_test_disabled;

uniform sampler2D screen_texture : hint_screen_texture, repeat_disable, filter_linear;
uniform sampler2D depth_texture : hint_depth_texture, repeat_disable, filter_nearest;

uniform bool effect_enabled = true;
uniform int display_mode = 0;
uniform float strength : hint_range(0.0, 1.0) = 0.55;
uniform float radius : hint_range(0.05, 3.0) = 0.8;
uniform float bias : hint_range(0.0, 0.35) = 0.06;
uniform float falloff : hint_range(0.5, 4.0) = 2.0;
uniform float fade_start : hint_range(0.0, 200.0) = 25.0;
uniform float fade_end : hint_range(1.0, 500.0) = 70.0;
uniform float debug_depth_range : hint_range(1.0, 500.0) = 80.0;

const int MODE_PASSTHROUGH = 0;
const int MODE_LINEAR_DEPTH = 1;
const int MODE_OCCLUSION_MASK = 2;
const int MODE_COMPOSITE = 3;
const float FAR_DEPTH_EPSILON = 0.000001;

void vertex() {
	// Godot 4.3+ uses reversed-Z: clip-space near is 1.0 and far is 0.0.
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

vec3 reconstruct_view_position(vec2 uv, float raw_depth, mat4 inverse_projection) {
	vec3 ndc = vec3(uv * 2.0 - 1.0, raw_depth);
	vec4 view = inverse_projection * vec4(ndc, 1.0);
	return view.xyz / view.w;
}

float sample_contact_occlusion(
	vec2 center_uv,
	vec3 center_position,
	vec3 surface_normal,
	vec2 uv_offset,
	mat4 inverse_projection
) {
	vec2 sample_uv = clamp(center_uv + uv_offset, vec2(0.0), vec2(1.0));
	float sample_depth = textureLod(depth_texture, sample_uv, 0.0).r;
	if (sample_depth <= FAR_DEPTH_EPSILON) {
		return 0.0;
	}

	vec3 sample_position = reconstruct_view_position(sample_uv, sample_depth, inverse_projection);
	vec3 delta = sample_position - center_position;
	float distance_to_sample = length(delta);
	if (distance_to_sample <= 0.0001 || distance_to_sample >= radius) {
		return 0.0;
	}

	float hemisphere = max(dot(surface_normal, delta / distance_to_sample) - bias, 0.0);
	float distance_weight = pow(max(1.0 - distance_to_sample / radius, 0.0), falloff);
	return hemisphere * distance_weight;
}

float contact_occlusion(
	vec2 uv,
	float raw_depth,
	vec3 center_position,
	mat4 inverse_projection,
	mat4 projection,
	vec2 viewport_size
) {
	if (raw_depth <= FAR_DEPTH_EPSILON) {
		return 0.0;
	}

	vec3 surface_normal = normalize(cross(dFdy(center_position), dFdx(center_position)));
	if (dot(surface_normal, -center_position) < 0.0) {
		surface_normal = -surface_normal;
	}

	float view_depth = max(-center_position.z, 0.0001);
	vec2 projected_radius = vec2(
		0.5 * radius * projection[0][0] / view_depth,
		0.5 * radius * projection[1][1] / view_depth
	);
	vec2 pixel_size = 1.0 / viewport_size;
	projected_radius = clamp(projected_radius, pixel_size, pixel_size * 24.0);

	float occlusion = 0.0;
	occlusion += sample_contact_occlusion(uv, center_position, surface_normal, vec2(projected_radius.x, 0.0), inverse_projection);
	occlusion += sample_contact_occlusion(uv, center_position, surface_normal, vec2(-projected_radius.x, 0.0), inverse_projection);
	occlusion += sample_contact_occlusion(uv, center_position, surface_normal, vec2(0.0, projected_radius.y), inverse_projection);
	occlusion += sample_contact_occlusion(uv, center_position, surface_normal, vec2(0.0, -projected_radius.y), inverse_projection);
	occlusion = clamp(occlusion * 0.5, 0.0, 1.0);

	float safe_fade_end = max(fade_end, fade_start + 0.001);
	float distance_visibility = 1.0 - smoothstep(fade_start, safe_fade_end, view_depth);
	return occlusion * distance_visibility;
}

void fragment() {
	vec3 scene_color = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	vec3 output_color = scene_color;

	if (!effect_enabled || display_mode == MODE_PASSTHROUGH) {
		output_color = scene_color;
	} else {
		float raw_depth = textureLod(depth_texture, SCREEN_UV, 0.0).r;
		if (display_mode == MODE_LINEAR_DEPTH) {
			if (raw_depth <= FAR_DEPTH_EPSILON) {
				output_color = vec3(1.0);
			} else {
				vec3 view_position = reconstruct_view_position(SCREEN_UV, raw_depth, INV_PROJECTION_MATRIX);
				float linear_depth = max(-view_position.z, 0.0);
				output_color = vec3(clamp(linear_depth / max(debug_depth_range, 0.001), 0.0, 1.0));
			}
		} else {
			vec3 center_position = reconstruct_view_position(SCREEN_UV, raw_depth, INV_PROJECTION_MATRIX);
			float occlusion = contact_occlusion(
				SCREEN_UV,
				raw_depth,
				center_position,
				INV_PROJECTION_MATRIX,
				PROJECTION_MATRIX,
				VIEWPORT_SIZE
			);

			if (display_mode == MODE_OCCLUSION_MASK) {
				output_color = vec3(1.0 - occlusion);
			} else if (display_mode == MODE_COMPOSITE) {
				output_color = scene_color * (1.0 - occlusion * strength);
			}
		}
	}

	ALBEDO = output_color;
}
