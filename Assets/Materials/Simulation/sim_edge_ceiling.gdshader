shader_type spatial;
render_mode cull_back, depth_draw_opaque;

uniform vec4 edge_color : source_color = vec4(0.0, 0.55, 0.82, 1.0);
uniform float emission_strength : hint_range(0.0, 8.0, 0.05) = 3.2;

void fragment() {
	ALBEDO = edge_color.rgb * 0.035;
	METALLIC = 0.15;
	ROUGHNESS = 0.5;
	EMISSION = edge_color.rgb * emission_strength;
}
