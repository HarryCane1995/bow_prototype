shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_always, cull_disabled;
uniform vec4 color_a : source_color = vec4(1.0);
uniform vec4 color_b : source_color = vec4(1.0);
uniform float opacity = 0.7;
uniform float emission_strength = 0.3;
uniform float wobble = 0.02;
uniform float shade_levels = 5.0;
uniform float quantization = 0.35;
uniform float dither_strength = 0.7;
uniform float soft_alpha = 0.15;
uniform bool flat_unshaded = false;
uniform bool dither_mode = false;
instance uniform float life_alpha = 0.0;
instance uniform float effect_time = 0.0;
instance uniform float tint_mix = 0.5;
varying vec3 view_normal;
varying vec3 view_position;
void vertex() {
    VERTEX += normalize(VERTEX + vec3(0.0001)) * sin(dot(VERTEX,vec3(11.0,7.0,13.0))+floor(effect_time*12.0)*0.45)*wobble;
    view_normal = normalize(MODELVIEW_NORMAL_MATRIX * NORMAL);
    view_position = (MODELVIEW_MATRIX * vec4(VERTEX,1.0)).xyz;
}
void fragment() {
    vec3 normal = normalize(view_normal);
    vec3 light_dir = normalize((VIEW_MATRIX*vec4(-0.4,0.85,0.5,0.0)).xyz);
    float light = max(dot(normal,light_dir)*0.5+0.5,0.0);
    float shade = flat_unshaded ? 1.0 : 0.32+0.68*floor(light*shade_levels)/shade_levels;
    vec3 color = mix(color_a.rgb,color_b.rgb,clamp(UV.x*0.6+tint_mix*0.4,0.0,1.0));
    color = mix(color,floor(color*12.0+0.5)/12.0,quantization);
    float alpha = opacity*life_alpha*mix(1.0,pow(abs(dot(normal,normalize(-view_position))),0.5),soft_alpha);
    if(dither_mode) {
        int x=int(mod(FRAGCOORD.x,4.0)); int y=int(mod(FRAGCOORD.y,4.0));
        float bayer[16] = float[16](0.0,8.0,2.0,10.0,12.0,4.0,14.0,6.0,3.0,11.0,1.0,9.0,15.0,7.0,13.0,5.0);
        float threshold=mix(0.5,(bayer[y*4+x]+0.5)/16.0,dither_strength);
        if(alpha<threshold){discard;} alpha=1.0;
    }
    ALBEDO=color*(shade+emission_strength);
    ALPHA=alpha;
}
