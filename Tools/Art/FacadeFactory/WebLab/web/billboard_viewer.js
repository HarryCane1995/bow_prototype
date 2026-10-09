import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

export class BillboardViewer {
  constructor(host){
    this.host=host;this.visible=true;this.revision=0;this.textures=[];
    this.renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.outputColorSpace=THREE.SRGBColorSpace;
    this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.0;
    this.renderer.domElement.setAttribute('aria-label','Billboard plane and wall realtime preview');host.prepend(this.renderer.domElement);
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#101a20');
    this.camera=new THREE.PerspectiveCamera(38,1,.1,60);this.controls=new OrbitControls(this.camera,this.renderer.domElement);
    this.controls.enableDamping=true;this.controls.minDistance=2;this.controls.maxDistance=15;this.controls.enablePan=false;
    this.scene.add(new THREE.HemisphereLight(0xbfdbe3,0x27303b,2));
    const key=new THREE.DirectionalLight(0xedede0,2.5);key.position.set(-3,4,6);this.scene.add(key);
    this.group=new THREE.Group();this.scene.add(this.group);
    this.wall=new THREE.Mesh(new THREE.BoxGeometry(8,5,.2),new THREE.MeshStandardMaterial({color:'#27343a',roughness:.9}));
    this.wall.position.z=-.24;this.scene.add(this.wall);
    const grid=new THREE.GridHelper(14,14,0x35434b,0x202b32);grid.position.y=-2.65;this.scene.add(grid);
    this.frame();new ResizeObserver(()=>this.resize()).observe(host);
    this.renderer.setAnimationLoop(()=>{if(this.visible){this.controls.update();this.renderer.render(this.scene,this.camera);}});
  }
  resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h)return;this.renderer.setSize(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();}
  frame(){this.camera.position.set(.9,.3,6);this.controls.target.set(0,0,0);this.controls.update();}
  setWall(on){this.wall.visible=on;}
  async show(payload){
    const rev=++this.revision,loader=new THREE.TextureLoader();
    const textures=await Promise.all(['albedo','emission','orm'].map(k=>loader.loadAsync(payload.maps[k])));
    if(rev!==this.revision){textures.forEach(t=>t.dispose());return;}
    this.textures.forEach(t=>t.dispose());this.textures=textures;
    for(const child of [...this.group.children]){child.geometry.dispose();child.material.dispose();this.group.remove(child);}
    textures.forEach((t,i)=>{t.colorSpace=i<2?THREE.SRGBColorSpace:THREE.NoColorSpace;t.magFilter=THREE.NearestFilter;});
    const r=payload.recipe,aspect=r.parameters.aspect,w=aspect>=1?3:3*aspect,h=aspect>=1?3/aspect:3;
    const material=new THREE.MeshStandardMaterial({map:textures[0],emissive:0xffffff,emissiveMap:textures[1],
      emissiveIntensity:r.parameters.emission_strength,roughnessMap:textures[2],roughness:1,metalnessMap:textures[2],metalness:1,
      transparent:r.archetype==='HOLOGRAM',depthWrite:r.archetype!=='HOLOGRAM',side:THREE.DoubleSide});
    const panel=new THREE.Mesh(new THREE.PlaneGeometry(w,h),material);panel.position.z=.062;this.group.add(panel);
    if(r.support_frame)this.group.add(new THREE.Mesh(new THREE.BoxGeometry(w+.09,h+.09,.10),new THREE.MeshStandardMaterial({color:'#11171a',metalness:.7,roughness:.65})));
    this.renderer.domElement.dataset.recipeKey=payload.key;this.renderer.render(this.scene,this.camera);
  }
  capture(){this.renderer.render(this.scene,this.camera);return this.renderer.domElement.toDataURL('image/png');}
}
