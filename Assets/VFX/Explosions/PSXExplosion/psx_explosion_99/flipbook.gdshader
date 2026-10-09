shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_never, fog_disabled;

uniform sampler2D color_sheet : source_color, filter_nearest, repeat_disable;
uniform sampler2D emission_sheet : source_color, filter_nearest, repeat_disable;
uniform vec2 atlas_grid = vec2(6.0, 6.0);
uniform float frame_size = 128.0;
uniform float gutter = 2.0;
uniform float frame_index = 0.0;
uniform float emission_strength : hint_range(0.0, 4.0) = 1.0;
uniform bool use_emission = true;

void vertex() {
	// Camera-facing quad; atlas animation remains explicitly instance-controlled.
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		vec4(INV_VIEW_MATRIX[0].xyz * length(MODEL_MATRIX[0].xyz), 0.0),
		vec4(INV_VIEW_MATRIX[1].xyz * length(MODEL_MATRIX[1].xyz), 0.0),
		vec4(INV_VIEW_MATRIX[2].xyz * length(MODEL_MATRIX[2].xyz), 0.0), MODEL_MATRIX[3]);
}

void fragment() {
	float cell = frame_size + gutter * 2.0;
	vec2 tile = vec2(mod(frame_index, atlas_grid.x), floor(frame_index / atlas_grid.x));
	vec2 uv = (tile * cell + gutter + 0.5 + UV * (frame_size - 1.0)) / (atlas_grid * cell);
	vec4 color = texture(color_sheet, uv);
	vec4 light = texture(emission_sheet, uv);
	ALBEDO = color.rgb;
	ALPHA = color.a;
	// Divide by composite alpha: the emission map already has its own alpha.
	EMISSION = use_emission ? light.rgb * light.a / max(color.a, 0.001) * emission_strength : vec3(0.0);
}
