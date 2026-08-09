shader_type spatial;
render_mode blend_add, depth_draw_never, cull_back, shadows_disabled;

uniform sampler2D logo_texture : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 emission_color : source_color = vec4(0.72, 0.94, 1.0, 1.0);
uniform float emission_intensity : hint_range(0.0, 16.0, 0.1) = 4.0;
uniform float opacity : hint_range(0.0, 1.0, 0.01) = 0.9;


void fragment() {
	vec4 logo_sample = texture(logo_texture, UV);
	float mask = logo_sample.a;
	ALBEDO = vec3(0.0);
	EMISSION = emission_color.rgb * emission_intensity * mask;
	ALPHA = mask * opacity;
}
