shader_type spatial;

uniform vec4 plate : source_color = vec4(0.13, 0.19, 0.22, 1.0);
uniform vec4 etch : source_color = vec4(0.65, 0.74, 0.74, 1.0);
uniform vec4 amber : source_color = vec4(1.0, 0.52, 0.16, 1.0);
uniform vec4 confirmation : source_color = vec4(0.54, 1.0, 0.85, 1.0);
uniform vec2 contact = vec2(0.0);
uniform float hit_progress : hint_range(0.0, 1.0) = 1.0;

float band(float distance_to_center, float radius, float half_width, float softness) {
	return 1.0 - smoothstep(half_width, half_width + softness, abs(distance_to_center - radius));
}

void fragment() {
	vec2 p = vec2(UV.x - 0.5, 0.5 - UV.y) * 2.0;
	float r = length(p);
	if (r > 1.0) discard;
	float aa = max(fwidth(r), 0.002);
	float angle = atan(p.y, p.x);
	float calibration_ticks = smoothstep(0.68, 0.90, cos(32.0 * angle)) * band(r, 0.927, 0.026, aa);
	float engraving = max(max(band(r, 0.79, 0.010, aa), band(r, 0.36, 0.008, aa)), calibration_ticks);
	float center = 1.0 - smoothstep(0.12, 0.12 + aa, r);
	float sight_ring = band(r, 0.575, 0.045, aa);
	float marks = max(center, sight_ring);
	vec3 base = mix(plate.rgb, etch.rgb, engraving * 0.75);
	float flash = 1.0 - hit_progress;
	float wave = band(length(p - contact), hit_progress * 2.2, 0.09, aa + 0.06) * flash;
	vec3 ring_color = mix(amber.rgb, confirmation.rgb, smoothstep(0.04, 0.45, flash));
	ALBEDO = mix(base, ring_color, marks);
	ROUGHNESS = 0.82;
	METALLIC = 0.15;
	EMISSION = etch.rgb * engraving * 0.22 + ring_color * marks * (0.90 + flash * 1.4) + confirmation.rgb * wave;
}
