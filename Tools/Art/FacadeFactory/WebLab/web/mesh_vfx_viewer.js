import * as THREE from 'three';
import { VFXViewer } from './vfx_viewer.js?v=1';

const vertex=`varying vec2 vUv; varying vec3 vNormal; varying vec3 vPosition; varying vec3 vLight;
uniform float wobble;uniform float effectTime;
void main(){vec3 p=position+normalize(position+vec3(0.0001))*sin(dot(position,vec3(11.,7.,13.))+floor(effectTime*12.)*.45)*wobble;
vUv=uv;vNormal=normalize(normalMatrix*normal);vPosition=(modelViewMatrix*vec4(p,1.)).xyz;vLight=normalize(mat3(viewMatrix)*vec3(-.4,.85,.5));
gl_Position=projectionMatrix*vec4(vPosition,1.);}`;
const fragment=`varying vec2 vUv;varying vec3 vNormal;varying vec3 vPosition;varying vec3 vLight;
uniform vec3 colorA;uniform vec3 colorB;uniform float opacity;uniform float emission;uniform float lifeAlpha;uniform float tintMix;
uniform float shadeLevels;uniform float quantization;uniform float ditherStrength;uniform float softAlpha;uniform bool unshaded;uniform bool ditherMode;
float threshold(vec2 xy){int x=int(mod(xy.x,4.)),y=int(mod(xy.y,4.));
if(y==0){if(x==0)return .5/16.;if(x==1)return 8.5/16.;if(x==2)return 2.5/16.;return 10.5/16.;}
if(y==1){if(x==0)return 12.5/16.;if(x==1)return 4.5/16.;if(x==2)return 14.5/16.;return 6.5/16.;}
if(y==2){if(x==0)return 3.5/16.;if(x==1)return 11.5/16.;if(x==2)return 1.5/16.;return 9.5/16.;}
if(x==0)return 15.5/16.;if(x==1)return 7.5/16.;if(x==2)return 13.5/16.;return 5.5/16.;}
void main(){vec3 n=normalize(vNormal);float light=max(dot(n,normalize(vLight))*.5+.5,0.);
float shade=unshaded?1.:.32+.68*floor(light*shadeLevels)/shadeLevels;
vec3 c=mix(colorA,colorB,clamp(vUv.x*.6+tintMix*.4,0.,1.));c=mix(c,floor(c*12.+.5)/12.,quantization);
float a=opacity*lifeAlpha*mix(1.,pow(abs(dot(n,normalize(-vPosition))),.5),softAlpha);
if(ditherMode){if(a<mix(.5,threshold(gl_FragCoord.xy),ditherStrength))discard;a=1.;}
gl_FragColor=vec4(c*(shade+emission),a);
#include <colorspace_fragment>
}`;

function darken(hex,factor){return '#'+[1,3,5].map(i=>Math.round(parseInt(hex.slice(i,i+2),16)*factor).toString(16).padStart(2,'0')).join('');}

export class MeshVFXViewer extends VFXViewer {
  constructor(host,onTime){
    super(host,()=>{});
    this.renderer.setAnimationLoop(null);
    // Share only the neutral review stage and orbit controls. Remove the legacy quad.
    this.scene.remove(this.quad);this.quad.geometry.dispose();this.material.dispose();this.quad=null;
    this.renderer.domElement.setAttribute('aria-label','Procedural mesh VFX 3D realtime preview');
    this.effect=new THREE.Group();this.scene.add(this.effect);this.parts=[];this.onTime=onTime;this.view='FREE';
    this.controls.maxDistance=80;this.previous=performance.now();
    this.renderer.setAnimationLoop(now=>{
      const dt=Math.min((now-this.previous)/1000,.1);this.previous=now;
      if(!this.visible||!this.data)return;
      this.controls.update();
      if(this.playing){this.time+=dt;if(this.time>=this.data.duration+(this.loop?.65:0)){if(this.loop)this.time=0;else this.playing=false;}}
      this.applyTime(Math.min(this.time,this.data.duration));this.renderer.render(this.scene,this.camera);
    });
  }

  show(data){
    const previousScale=this.data?.recipe.parameters.overall_scale,previousEffect=this.data?.recipe.effect;
    for(const {mesh} of this.parts){this.effect.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();}
    this.parts=[];this.data=data;const p=data.recipe.parameters;
    this.effect.scale.setScalar(p.overall_scale);
    for(const d of data.parts){
      const layer=data.recipe.layers[d.layer],source=data.meshes[d.mesh];
      const geometry=new THREE.BufferGeometry();
      geometry.setAttribute('position',new THREE.Float32BufferAttribute(source.positions,3));
      geometry.setAttribute('normal',new THREE.Float32BufferAttribute(source.normals,3));
      geometry.setAttribute('uv',new THREE.Float32BufferAttribute(source.uvs,2));geometry.computeBoundingSphere();
      const factor=d.layer==='smoke'?1-p.smoke_darkness*.7:1;
      const material=new THREE.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,
        transparent:layer.blend!=='DITHER',depthWrite:layer.depth_write,side:layer.cull_back?THREE.FrontSide:THREE.DoubleSide,
        blending:layer.blend==='ADDITIVE'?THREE.AdditiveBlending:THREE.NormalBlending,
        uniforms:{colorA:{value:new THREE.Color(darken(layer.color,factor))},colorB:{value:new THREE.Color(darken(layer.color_b,factor))},
          opacity:{value:layer.opacity},emission:{value:layer.emission*(d.layer==='core'?p.core_brightness:1)},
          lifeAlpha:{value:0},effectTime:{value:0},tintMix:{value:d.tint},wobble:{value:p.vertex_wobble},
          shadeLevels:{value:p.posterization},quantization:{value:p.palette_quantization},ditherStrength:{value:p.alpha_dithering},
          softAlpha:{value:layer.soft_alpha},unshaded:{value:layer.unshaded},ditherMode:{value:layer.blend==='DITHER'}}});
      const mesh=new THREE.Mesh(geometry,material);mesh.name=d.name;this.effect.add(mesh);
      this.parts.push({mesh,d,layer,rotation:new THREE.Quaternion(...d.rotation)});
    }
    if(previousScale!==p.overall_scale||previousEffect!==data.recipe.effect)this.setView(this.view);
    this.time=0;this.playing=true;this.applyTime(0);
    this.renderer.domElement.dataset.recipeKey=data.key;
    this.renderer.domElement.dataset.meshCount=String(data.stats.mesh_count);
  }

  applyTime(seconds){
    for(const {mesh,d,layer,rotation} of this.parts){
      const u=(seconds-d.start)/d.life;
      mesh.visible=layer.enabled&&u>=0&&u<1&&seconds<this.data.duration;if(!mesh.visible)continue;
      const growth=(1-Math.exp(-4*d.speed*u))/(1-Math.exp(-4*d.speed));
      mesh.scale.fromArray(d.scale0).lerp(new THREE.Vector3(...d.scale1),growth);
      mesh.position.fromArray(d.origin).addScaledVector(new THREE.Vector3(...d.travel),growth);mesh.position.y-=d.gravity*u*u;
      mesh.quaternion.copy(rotation).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),d.spin*u));
      let fade=Math.max(0,Math.min(1,(u-d.fade_start)/(1-d.fade_start)));
      if(layer.fade_curve==='EASE_OUT')fade=1-(1-fade)**2;else if(layer.fade_curve==='SMOOTH')fade=fade*fade*(3-2*fade);
      mesh.material.uniforms.lifeAlpha.value=(1-fade)*Math.min(1,u/.04+.15);mesh.material.uniforms.effectTime.value=seconds;
    }
    this.renderer.domElement.dataset.time=seconds.toFixed(3);this.onTime(seconds,this.playing);
  }

  setView(mode){
    this.view=mode;const p=this.data?.recipe.parameters||{overall_scale:1,ring_radius:3.3,petal_length:1.8};
    const classic=!this.data||this.data.recipe.effect==='MESH_EXPLOSION_3D';
    const extent=classic?Math.max(p.ring_radius,p.petal_length):Math.max(p.effect_radius,p.effect_length*.65);
    const distance=Math.max(7,extent*2.5)*p.overall_scale;
    const kind=this.data?.recipe.effect;
    const target=new THREE.Vector3(0,p.overall_scale*(kind==='DIRECTIONAL_LIGHTNING'?p.effect_length*.45:1),kind==='PROJECTILE_TRAIL'?-p.effect_length*.3*p.overall_scale:0);this.controls.target.copy(target);
    const offset=mode==='TOP'?new THREE.Vector3(.001,distance,0):mode==='SIDE'?new THREE.Vector3(distance,.15,0):
      mode==='GAMEPLAY'?new THREE.Vector3(distance*.3,distance*.15,distance*1.45):new THREE.Vector3(distance*.55,distance*.37,distance*.82);
    this.camera.position.copy(target).add(offset);this.controls.update();
  }
  snapshot(seconds){
    const previous=this.time;this.applyTime(Math.min(seconds,this.data.duration*.5));this.renderer.render(this.scene,this.camera);
    const canvas=document.createElement('canvas');canvas.width=256;canvas.height=176;
    canvas.getContext('2d').drawImage(this.renderer.domElement,0,0,256,176);const result=canvas.toDataURL('image/webp',.75);
    this.applyTime(previous);return result;
  }
  seek(seconds){this.time=seconds;this.playing=false;this.applyTime(seconds);}
  restart(){this.time=0;this.playing=true;if(this.data)this.applyTime(0);}
  toggle(){if(!this.playing&&this.time>=this.data.duration)this.restart();else this.playing=!this.playing;this.onTime(Math.min(this.time,this.data.duration),this.playing);}
}
