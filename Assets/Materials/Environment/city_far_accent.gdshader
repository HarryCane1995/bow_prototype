shader_type spatial;
render_mode unshaded, cull_back;

group_uniforms Accent;
uniform vec4 accent_color : source_color = vec4(0.02, 0.82, 1.0, 1.0);
uniform vec4 secondary_accent_color : source_color = vec4(0.56, 0.18, 1.0, 1.0);
uniform float accent_brightness : hint_range(0.0, 20.0, 0.1) = 5.5;
uniform float accent_color_variation : hint_range(0.0, 1.0, 0.01) = 0.32;
uniform float panel_pattern_strength : hint_range(0.0, 1.0, 0.01) = 0.18;

group_uniforms;

varying vec3 world_position;


float hash12(vec2 value) {
	vec3 value3 = fract(vec3(value.xyx) * 0.1031);
	value3 += dot(value3, value3.yzx + 33.33);
	return fract((value3.x + value3.y) * value3.z);
}


void vertex() {
	world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}


void fragment() {
	vec2 district_cell = floor(world_position.xz / 70.0);
	float color_random = hash12(district_cell + 47.31);
	float stripe = step(0.78, fract(world_position.y * 0.11 + color_random));
	vec3 varied_color = mix(accent_color.rgb, secondary_accent_color.rgb, color_random);
	vec3 final_color = mix(accent_color.rgb, varied_color, accent_color_variation);
	float pattern_brightness = mix(1.0, 1.35, stripe * panel_pattern_strength);

	ALBEDO = final_color * accent_brightness * 0.42 * pattern_brightness;
	EMISSION = final_color * accent_brightness * pattern_brightness;
}
