import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

export class VFXViewer {
  constructor(host, onFrame) {
    this.host = host; this.onFrame = onFrame; this.visible = true;
    this.renderer = new THREE.WebGLRenderer({antialias: false});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.prepend(this.renderer.domElement);
    this.renderer.domElement.setAttribute('aria-label', 'PSX explosion billboard preview');
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(43, 1, .1, 80);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true; this.controls.enablePan = false;
    this.controls.minDistance = 3; this.controls.maxDistance = 20; this.controls.maxPolarAngle = Math.PI * .49;
    this.scene.add(new THREE.HemisphereLight(0xcddadc, 0x283238, 2));
    const light = new THREE.DirectionalLight(0xffefdc, 2); light.position.set(-3, 8, 5); this.scene.add(light);
    this.set = new THREE.Group(); this.scene.add(this.set);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({color: 0x1b262d, roughness: 1}));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -.03; this.set.add(floor);
    const grid = new THREE.GridHelper(30, 30, 0x526064, 0x2e3c40); grid.position.y = -.02; this.set.add(grid);
    const cube = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({color: 0x687579, roughness: .9}));
    cube.position.set(-2.7, .5, 0); this.set.add(cube);
    this.material = new THREE.ShaderMaterial({transparent: true, depthWrite: false, side: THREE.DoubleSide,
      uniforms: {colorSheet: {value: null}, emissionSheet: {value: null}, grid: {value: new THREE.Vector2(1,1)},
        frameSize: {value: 128}, frameIndex: {value: 0}, emissionStrength: {value: 1}},
      vertexShader: 'varying vec2 vUv; void main(){vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
      fragmentShader: `uniform sampler2D colorSheet; uniform sampler2D emissionSheet; uniform vec2 grid;
        uniform float frameSize; uniform float frameIndex; uniform float emissionStrength; varying vec2 vUv;
        void main(){float cell=frameSize+4.0; vec2 tile=vec2(mod(frameIndex,grid.x),floor(frameIndex/grid.x));
          vec2 uv=(tile*cell+2.5+vec2(vUv.x,1.0-vUv.y)*(frameSize-1.0))/(grid*cell);
          vec4 c=texture2D(colorSheet,uv); vec4 e=texture2D(emissionSheet,uv);
          gl_FragColor=vec4(c.rgb+e.rgb*e.a/max(c.a,0.001)*emissionStrength,c.a);
          #include <colorspace_fragment>
        }`,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(1,1), this.material); this.quad.visible = false; this.scene.add(this.quad);
    this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(host);
    this.playing = true; this.loop = true; this.time = 0; this.index = 0; this.previous = performance.now();
    this.background('SCENE');
    this.renderer.setAnimationLoop(now => {
      const dt = Math.min((now - this.previous) / 1000, .1); this.previous = now;
      if (!this.visible || !this.bundle) return;
      this.controls.update(); this.quad.quaternion.copy(this.camera.quaternion);
      if (this.playing) {
        this.time += dt;
        const m = this.bundle.metadata;
        if (this.time >= m.playback_duration + (this.loop ? .6 : 0)) {
          if (this.loop) this.time = 0; else this.playing = false;
        }
        this.frame(Math.min(m.frame_count - 1, Math.floor(this.time * m.fps)));
      }
      this.renderer.render(this.scene, this.camera);
    });
  }

  resize() {
    const w = this.host.clientWidth, h = this.host.clientHeight; if (!w || !h) return;
    this.renderer.setSize(w,h,false); this.camera.aspect = w/h; this.camera.updateProjectionMatrix();
  }

  background(mode) {
    this.set.visible = mode === 'SCENE';
    this.scene.background = new THREE.Color(mode === 'BLACK' ? '#000000' : mode === 'GRAY' ? '#5c6064' : '#111b22');
    if (mode === 'CHECKER') {
      if (!this.checker) {
        const canvas = document.createElement('canvas'); canvas.width=canvas.height=64;
        const ctx=canvas.getContext('2d'); ctx.fillStyle='#30363b'; ctx.fillRect(0,0,64,64);
        ctx.fillStyle='#444b50'; ctx.fillRect(0,0,32,32); ctx.fillRect(32,32,32,32);
        this.checker=new THREE.CanvasTexture(canvas); this.checker.colorSpace=THREE.SRGBColorSpace;
        this.checker.wrapS=this.checker.wrapT=THREE.RepeatWrapping; this.checker.repeat.set(12,8);
      }
      this.scene.background=this.checker;
    }
    this.controls.target.set(0,1.25,0);
    this.camera.position.set(mode==='SCENE'?4.5:0,mode==='SCENE'?3.1:1.25,7.5);
    this.controls.update();
  }

  async prepare(result) {
    const loader = new THREE.TextureLoader(), textures=[];
    const loaded = await Promise.allSettled(['color_sheet','emission_sheet'].map(async name=>{
      const texture=await loader.loadAsync(result.images[name]); textures.push(texture);
      texture.colorSpace=THREE.SRGBColorSpace; texture.flipY=false;
      texture.minFilter=texture.magFilter=THREE.NearestFilter; texture.generateMipmaps=false;
      return texture;
    }));
    if(loaded.some(r=>r.status==='rejected')){textures.forEach(t=>t.dispose());throw new Error('Could not load the VFX atlas.');}
    return {...result, color:loaded[0].value, emission:loaded[1].value, dispose(){textures.forEach(t=>t.dispose());}};
  }

  show(bundle) {
    this.bundle?.dispose(); this.bundle=bundle;
    const m=bundle.metadata,u=this.material.uniforms,size=m.canvas_world_size;
    u.colorSheet.value=bundle.color; u.emissionSheet.value=bundle.emission;
    u.grid.value.set(m.cols,m.rows); u.frameSize.value=m.frame_size;
    this.quad.scale.set(size,size,1); this.quad.position.y=size*.32; this.quad.visible=true;
    this.time=0; this.playing=true; this.frame(0);
    this.renderer.domElement.dataset.recipeKey=bundle.key;
  }

  frame(index) {
    this.index=index; this.material.uniforms.frameIndex.value=index;
    this.renderer.domElement.dataset.frame=String(index);
    this.onFrame(index,this.playing);
  }

  scrub(index) {if(!this.bundle)return;this.playing=false;this.time=index/this.bundle.metadata.fps;this.frame(index);}
  restart() {this.time=0;this.playing=true;this.frame(0);}
  toggle() {if(!this.playing&&this.index===this.bundle?.metadata.frame_count-1)this.restart();else this.playing=!this.playing;this.onFrame(this.index,this.playing);}
}
