import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

export class FacadeViewer {
  constructor(host) {
    this.host = host;
    this.renderer = new THREE.WebGLRenderer({antialias: true, alpha: false});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.35;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.domElement.setAttribute('aria-label', 'Three.js facade preview');
    host.prepend(this.renderer.domElement);
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#111c21');
    this.scene.fog = new THREE.Fog('#111c21', 32, 90);
    this.camera = new THREE.PerspectiveCamera(39, 1, .1, 120);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = .08;
    this.controls.enablePan = false;
    this.controls.mouseButtons = {LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE};
    this.controls.minDistance = 5;
    this.controls.maxDistance = 55;
    this.controls.maxPolarAngle = Math.PI * .51;
    const room = new RoomEnvironment();
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.environment = pmrem.fromScene(room, .04);
    this.scene.environment = this.environment.texture;
    room.dispose(); pmrem.dispose();
    this.scene.add(new THREE.HemisphereLight(0xdfe9ed, 0x263730, 1.0));
    const key = new THREE.DirectionalLight(0xf1f4ec, 3.0);
    key.position.set(-7, 15, 9); key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.left = -17; key.shadow.camera.right = 17;
    key.shadow.camera.top = 24; key.shadow.camera.bottom = -16;
    key.shadow.normalBias = .04; key.shadow.bias = -.0001;
    this.scene.add(key);
    const rim = new THREE.DirectionalLight(0xc2e0df, 1.9);
    rim.position.set(8, 12, -6); this.scene.add(rim);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), new THREE.MeshStandardMaterial({color: '#1b272c', roughness: 1}));
    floor.rotation.x = -Math.PI / 2; floor.position.y = -.2; floor.receiveShadow = true;
    this.scene.add(floor);
    const grid = new THREE.GridHelper(80, 40, '#3e5358', '#283b40');
    grid.position.y = -.19;
    grid.material.transparent = true; grid.material.opacity = .28;
    this.scene.add(grid);
    this.material = new THREE.MeshStandardMaterial({color: 0xffffff, metalness: 1, roughness: 1,
      emissive: 0xffffff, emissiveIntensity: 1.15, normalScale: new THREE.Vector2(.55, .55),
      envMapIntensity: .45, aoMapIntensity: .65});
    this.cap = new THREE.MeshStandardMaterial({color: '#3a4647', roughness: .84, metalness: .18});
    this.debugColor = new THREE.MeshBasicMaterial({toneMapped: false});
    // Data maps are shown as their stored RGB bytes, without an sRGB conversion.
    this.debugData = new THREE.ShaderMaterial({
      uniforms: {map: {value: null}, uvRepeat: {value: new THREE.Vector2(1,1)}, channel: {value: -1}},
      vertexShader: 'varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: 'uniform sampler2D map; uniform vec2 uvRepeat; uniform int channel; varying vec2 vUv; void main(){vec2 uv=vUv*uvRepeat; vec3 c=texture2D(map,uv).rgb; if(channel==1)c=vec3(c.g); if(channel==2){float f=fract(uv.x); float seam=1.0-step(0.018,min(f,1.0-f)); c=mix(c,vec3(1.0,0.35,0.06),seam*0.85);} gl_FragColor=vec4(c,1.0);}',
    });
    this.options = {map: 'material', uvX: 1, uvY: 1, emissionOn: true, emissionStrength: 1.15, breakupOn:true};
    this.setShape('BOX');
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(host);
    const clock = new THREE.Clock();
    this.renderer.setAnimationLoop(() => {
      this.controls.update(Math.min(clock.getDelta(), .1));
      this.renderer.render(this.scene, this.camera);
    });
    this.renderer.domElement.addEventListener('webglcontextlost', e => {
      e.preventDefault();
      if(this.destroying)return;
      host.dispatchEvent(new CustomEvent('viewer-error', {detail: 'WebGL context lost. Reload the page to restore the preview.'}));
    });
  }

  resize() {
    const width = this.host.clientWidth, height = this.host.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  setShape(shape) {
    if (this.mesh) {this.scene.remove(this.mesh); this.mesh.traverse(object=>object.geometry?.dispose());this.mesh=null;}
    this.surfaceMeshes=[];
    if (['PLANE','FLOOR_PATCH','WALL_CORNER','CYLINDER','COLUMN_CLUSTER'].includes(shape)) {
      if(this.plinth){this.scene.remove(this.plinth);this.plinth.geometry.dispose();this.plinth=null;}
      this.mesh=new THREE.Group();this.scene.add(this.mesh);
      const add=(geometry,position,rotation=0,cylinder=false)=>{
        geometry.setAttribute('uv1',geometry.attributes.uv.clone());
        const object=new THREE.Mesh(geometry,cylinder?[this.material,this.cap,this.cap]:this.material);
        object.position.set(...position);object.rotation.y=rotation;object.castShadow=true;object.receiveShadow=true;
        object.userData.cylinder=cylinder;this.mesh.add(object);this.surfaceMeshes.push(object);return object;
      };
      this.material.side=THREE.DoubleSide;this.debugColor.side=THREE.DoubleSide;this.debugData.side=THREE.DoubleSide;
      if(shape==='PLANE') add(new THREE.PlaneGeometry(13,13),[0,6.5,0]);
      if(shape==='FLOOR_PATCH'){const floor=add(new THREE.PlaneGeometry(18,18),[0,0,0]);floor.rotation.x=-Math.PI/2;}
      if(shape==='WALL_CORNER'){add(new THREE.PlaneGeometry(10,12),[-5,6,0]);add(new THREE.PlaneGeometry(10,12),[0,6,5],-Math.PI/2);}
      if(shape==='CYLINDER')add(new THREE.CylinderGeometry(3.3,3.3,14,96),[0,7,0],0,true);
      if(shape==='COLUMN_CLUSTER')for(const [x,z] of [[-4,1],[1,-3],[4,3]])add(new THREE.CylinderGeometry(1.55,1.55,12,64),[x,6,z],0,true);
      this.shape=shape;this.height=shape==='FLOOR_PATCH'?1:14;this.width=shape==='FLOOR_PATCH'?18:12;
      this.applyOptions();this.frame();this.renderer.domElement.dataset.shape=shape;return;
    }
    const sizes = {BOX: [4.6, 11, 4.6], TALL_TOWER: [3.8, 17, 3.8], WIDE_MEGABLOCK: [8.8, 7, 4.6], TAPERED_TOWER: [5.2, 14, 5.2]};
    const [x, y, z] = sizes[shape];
    if (this.plinth) { this.scene.remove(this.plinth); this.plinth.geometry.dispose(); }
    const geometry = new THREE.BoxGeometry(x, y, z);
    if (shape === 'TAPERED_TOWER') {
      const positions = geometry.attributes.position;
      for (let i = 0; i < positions.count; i++) {
        if (positions.getY(i) > 0) { positions.setX(i, positions.getX(i) * .55); positions.setZ(i, positions.getZ(i) * .55); }
      }
      positions.needsUpdate = true; geometry.computeVertexNormals();
    }
    // Independent, full-sheet UVs on each vertical face; caps use a neutral material.
    geometry.setAttribute('uv1', geometry.attributes.uv.clone());
    this.mesh = new THREE.Mesh(geometry, [this.material, this.material, this.cap, this.cap, this.material, this.material]);
    this.mesh.position.y = y / 2; this.mesh.castShadow = true; this.mesh.receiveShadow = true;
    this.scene.add(this.mesh);
    this.plinth = new THREE.Mesh(new THREE.BoxGeometry(x + .5, .25, z + .5), this.cap);
    this.plinth.position.y = -.09; this.plinth.receiveShadow = true;
    this.scene.add(this.plinth);
    this.shape = shape; this.height = y; this.width = x;
    this.applyOptions(); this.frame();
    this.renderer.domElement.dataset.shape = shape;
  }

  frame() {
    const h = this.height;
    this.controls.target.set(0, h * .49, 0);
    const distance = Math.max(h * 1.65, this.width * 2.1);
    this.camera.position.set(distance * .47, h * .62 + 2.3, distance * .91);
    if(this.shape==='PLANE')this.camera.position.set(2,8,26);
    if(this.shape==='WALL_CORNER'){this.controls.target.set(-2,6,2);this.camera.position.set(-19,12,24);}
    if(this.shape==='FLOOR_PATCH'){this.controls.target.set(0,0,0);this.camera.position.set(10,20,16);}
    if(this.shape==='CYLINDER'){this.controls.target.set(0,7,0);this.camera.position.set(.2,9,28);}
    this.controls.update();
  }

  async prepareMaps(response) {
    const loader = new THREE.TextureLoader();
    const textures = {};
    const urls={...response.maps,...Object.fromEntries(Object.entries(response.preview_maps||{}).map(([k,v])=>['preview_'+k,v]))};
    const loaded = await Promise.allSettled(Object.entries(urls).map(async ([key, url]) => {
      const texture = await loader.loadAsync(url);
      textures[key] = texture;
      texture.colorSpace = ['albedo', 'emission', 'preview_albedo'].includes(key) ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      texture.anisotropy = Math.min(8, this.renderer.capabilities.getMaxAnisotropy());
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.NearestFilter;
      texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
      if (key === 'orm') texture.channel = 0;
      return texture;
    }));
    if (loaded.some(r => r.status === 'rejected')) {
      Object.values(textures).forEach(t => t.dispose());
      throw new Error('Could not load all texture maps. Try another change to regenerate.');
    }
    return {...response, textures, dispose() { Object.values(textures).forEach(t => t.dispose()); }};
  }

  show(bundle) {
    this.bundle = bundle;
    if(!bundle.textures[this.options.map] && !['material','roughness','seam'].includes(this.options.map))this.options.map='material';
    this.renderer.toneMappingExposure=bundle.recipe.surface_mode==='UNIQUE_FACADE'?1.35:.95;
    const t = bundle.textures;
    Object.assign(this.material, {map: t.albedo, emissiveMap: t.emission, normalMap: t.normal,
      aoMap: t.orm, roughnessMap: t.orm, metalnessMap: t.orm});
    this.material.needsUpdate = true;
    this.applyOptions();
    this.renderer.domElement.dataset.recipeKey = bundle.key;
    this.renderer.domElement.dataset.mapsLoaded = Object.keys(t).join(',');
    this.renderer.domElement.dataset.structureHash=bundle.structure_hash||'';
  }

  setOptions(options) { Object.assign(this.options, options); this.applyOptions(); }

  applyOptions() {
    const {map, uvX, uvY, emissionOn, emissionStrength} = this.options;
    this.material.emissiveIntensity = emissionOn ? emissionStrength : 0;
    if (this.bundle) {
      const t=this.bundle.textures;
      const optional=this.options.breakupOn && !!t.preview_albedo;
      Object.assign(this.material,{map:optional?t.preview_albedo:t.albedo,normalMap:optional?t.preview_normal:t.normal,
        aoMap:optional?t.preview_orm:t.orm,roughnessMap:optional?t.preview_orm:t.orm,metalnessMap:optional?t.preview_orm:t.orm});
      this.material.needsUpdate=true;
      for (const texture of Object.values(this.bundle.textures)) {
        texture.repeat.set(uvX, uvY);
        texture.wrapS = texture.wrapT = (uvX === 1 && uvY === 1) ? THREE.ClampToEdgeWrapping : THREE.RepeatWrapping;
        texture.needsUpdate = true;
      }
    }
    let visible = this.material;
    if (map !== 'material' && this.bundle) {
      if (map === 'albedo' || map === 'emission') {
        this.debugColor.map = this.bundle.textures[map];
        this.debugColor.needsUpdate = true;
        visible = this.debugColor;
      } else {
        this.debugData.uniforms.map.value = this.bundle.textures[map === 'roughness' ? 'orm' : map === 'seam' ? 'albedo' : map];
        this.debugData.uniforms.uvRepeat.value.set(uvX, uvY);
        this.debugData.uniforms.channel.value = map === 'roughness' ? 1 : map==='seam'?2:-1;
        visible = this.debugData;
      }
    }
    if(this.surfaceMeshes?.length){for(const object of this.surfaceMeshes)object.material=object.userData.cylinder?[visible,this.cap,this.cap]:visible;}
    else if (this.mesh) this.mesh.material = [visible, visible, this.cap, this.cap, visible, visible];
    if (this.renderer) this.renderer.domElement.dataset.mapMode = map;
  }

  async screenshot() {
    this.renderer.render(this.scene, this.camera);
    return new Promise((resolve, reject) => this.renderer.domElement.toBlob(blob => blob ? resolve(blob) : reject(new Error('Screenshot failed')), 'image/png'));
  }

  dispose(){
    this.destroying=true;this.renderer.setAnimationLoop(null);this.resizeObserver.disconnect();this.controls.dispose();
    const geometries=new Set(),materials=new Set();
    this.scene.traverse(object=>{if(object.geometry)geometries.add(object.geometry);for(const m of Array.isArray(object.material)?object.material:[object.material])if(m)materials.add(m);});
    geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());this.bundle?.dispose();this.environment.dispose();this.renderer.dispose();this.renderer.forceContextLoss();this.renderer.domElement.remove();
  }
}
