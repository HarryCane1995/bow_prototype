shader_type spatial;
render_mode cull_back, depth_draw_opaque;

group_uniforms Appearance;
uniform vec4 edge_color : source_color = vec4(0.0, 0.55, 0.82, 1.0);
uniform float emission_strength : hint_range(0.0, 8.0, 0.05) = 3.2;

group_uniforms Surface;
uniform float metallic : hint_range(0.0, 1.0, 0.01) = 0.15;
uniform float roughness : hint_range(0.0, 1.0, 0.01) = 0.5;
uniform float specular_strength : hint_range(0.0, 1.0, 0.01) = 0.5;

void fragment() {
	ALBEDO = edge_color.rgb * 0.035;
	METALLIC = metallic;
	ROUGHNESS = roughness;
	SPECULAR = specular_strength;
	EMISSION = edge_color.rgb * emission_strength;
}
