import { VFXViewer } from './vfx_viewer.js?v=1';
import { createMeshVFX } from './mesh_vfx_app.js?v=1';

const $ = id => document.getElementById(id);
let config, state, viewer, current, revision=0, currentRevision=-1, busy=false, pending=false, timer, exporting=false;
let started;
let meshApp, meshStarting;
let effectMode=new URLSearchParams(location.search).get('vfx')||'MESH_EXPLOSION_3D';
const fields = new Map();

function status(message,error=false){$('vfx-status').textContent=message;$('vfx-status').classList.toggle('error',error);}
async function api(route,data){
  const response=await fetch(`/api/vfx/${route}`,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Facade-Token':config.token},body:JSON.stringify(data)});
  const result=await response.json();if(!response.ok)throw new Error(result.error||'VFX request failed');return result;
}
function ready(){
  const isReady=!!current&&!busy&&!pending&&currentRevision===revision;
  $('vfx-export').disabled=!isReady||exporting;$('vfx-save-recipe').disabled=!isReady;
  $('vfx-play').disabled=$('vfx-restart').disabled=$('vfx-scrub').disabled=!current;
  $('vfx-sprite-panel').dataset.phase=isReady?'ready':'generating';
}
function download(doc,name){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(doc,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

function shell(){
  $('vfx-tab').innerHTML='<div id="vfx-sprite-panel"></div><div id="vfx-mesh-panel" hidden></div>';
  $('vfx-sprite-panel').innerHTML=`
    <header class="vfx-toolbar">
      <div class="vfx-brand"><strong>VFX FACTORY</strong><small>BOWPROTOTYPE / LOCAL STUDY 01</small></div>
      <label>VFX MODE<select id="vfx-effect"><option>PSX_EXPLOSION</option><option>MESH_EXPLOSION_3D</option></select></label>
      <label>SEED<input id="vfx-seed" type="number" min="0" max="2147483647" value="99"></label>
      <button id="vfx-random" class="accent">↻ RANDOMIZE SEED</button>
      <span class="vfx-frame-count" id="vfx-count">32 FRAMES · 128 × 128</span>
    </header>
    <div class="vfx-layout">
      <section class="vfx-workspace" aria-label="VFX preview">
        <div class="vfx-preview-bar"><span>PREVIEW / BILLBOARD QUAD</span><select id="vfx-background" aria-label="VFX preview background"><option value="SCENE">IN-SCENE DARK · 1 m CUBE</option><option value="BLACK">BLACK</option><option value="GRAY">NEUTRAL GRAY</option><option value="CHECKER">TRANSPARENCY CHECKER</option></select></div>
        <div id="vfx-viewport"><div class="vfx-caption"><span>01 / PSX EXPLOSION</span><h1>Fire. Then smoke.</h1><p>A quick flash, a broken fire mass, a lingering silhouette. Every frame comes from the same seed.</p></div><div class="vfx-preview-note">DRAG TO ORBIT · SCROLL TO ZOOM · CAMERA-FACING SPRITE</div></div>
        <div id="vfx-filmstrip" class="vfx-filmstrip" aria-label="Explosion keyframes"></div>
        <div class="vfx-playback"><button id="vfx-play" disabled>PAUSE</button><button id="vfx-restart" disabled>RESTART</button><input id="vfx-scrub" type="range" min="0" max="31" step="1" value="0" aria-label="VFX frame scrubber" disabled><label><input id="vfx-loop" type="checkbox" checked> LOOP</label><output id="vfx-frame-label">FRAME 00 / 32</output></div>
        <div id="vfx-status" class="vfx-statusbar" role="status">Preparing VFX…</div>
      </section>
      <aside class="vfx-sidebar" aria-label="VFX controls"><span class="eyebrow">AUTHORING / PSX EXPLOSION</span><h2>Shape the burst.</h2>
        <div class="vfx-recipe-actions"><button id="vfx-reset">RESET EFFECT</button><button id="vfx-load">LOAD RECIPE ↑</button></div><input id="vfx-file" type="file" accept=".json,application/json" hidden>
        <section class="vfx-palette"><h3>COLOR / PALETTE</h3><select id="vfx-palette" aria-label="VFX palette"></select><div id="vfx-colors" class="vfx-colors"></div></section>
        <div id="vfx-control-groups"></div>
        <section class="vfx-export"><h3>EXPORT</h3><label for="vfx-resolution">FRAME RESOLUTION · PREVIEW = EXPORT</label><select id="vfx-resolution"><option value="64">64 × 64</option><option value="128" selected>128 × 128</option><option value="256">256 × 256</option></select>
          <label for="vfx-export-name">ASSET NAME</label><input id="vfx-export-name" maxlength="64" pattern="[a-zA-Z][a-zA-Z0-9_-]{0,63}" value="psx_explosion_99">
          <label for="vfx-export-format">OUTPUT</label><select id="vfx-export-format"><option value="BOTH">SPRITE SHEET + PNG SEQUENCE</option><option value="FLIPBOOK">SPRITE SHEET</option></select>
          <label class="check-row"><input id="vfx-export-emission" type="checkbox" checked> INCLUDE EMISSION</label>
          <p>RGBA · straight alpha · nearest filtering<br>Godot material + one-shot effect + review scene</p>
          <button id="vfx-export" class="export-button full" disabled>EXPORT TO PROJECT ↗</button><button id="vfx-save-recipe" class="full subtle" disabled>SAVE RECIPE JSON ↓</button>
          <p>Assets/VFX/Explosions/PSXExplosion/<br>Existing exports are preserved as separate revisions.</p><div id="vfx-export-result" class="vfx-export-result" role="status"></div>
        </section>
      </aside>
    </div>`;
}

function buildControls(){
  for(const [id,colors] of Object.entries(config.palettes))$('vfx-palette').add(new Option(id.replaceAll('_',' '),id));
  for(const [key,label] of Object.entries({primary:'Primary fire',secondary:'Secondary fire',smoke:'Smoke',accent:'Accent / emissive'})){
    const row=document.createElement('label'),input=document.createElement('input');input.type='color';input.id=`vfx-color-${key}`;input.setAttribute('aria-label',`VFX ${label} color`);
    row.append(input,document.createTextNode(label));$('vfx-colors').append(row);
    input.addEventListener('input',()=>{state.colors[key]=input.value;queue();});
  }
  const groups=new Map();
  for(const [key,[low,high,step,initial,label,group]] of Object.entries(config.controls)){
    if(!groups.has(group)){
      const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=group;
      details.open=['TIMING','SHAPE'].includes(group);details.append(summary);$('vfx-control-groups').append(details);groups.set(group,details);
    }
    const row=document.createElement('div');row.className='vfx-field';
    const labelElement=document.createElement('label');labelElement.textContent=label;labelElement.htmlFor=`vfx-${key}`;
    const number=document.createElement('input'),range=document.createElement('input');number.type='number';range.type='range';range.id=`vfx-${key}`;
    for(const input of [number,range]){input.min=low;input.max=high;input.step=step;input.value=initial;input.setAttribute('aria-label',`VFX ${label}${input===number?' numeric value':''}`);}
    row.append(labelElement,number,range);groups.get(group).append(row);fields.set(key,{number,range});
    const change=input=>{if(input.value===''||!input.validity.valid)return;state.parameters[key]=Number(input.value);number.value=range.value=input.value;queue();};
    range.addEventListener('input',()=>change(range));number.addEventListener('input',()=>change(number));
    number.addEventListener('blur',()=>{if(number.value===''||!number.validity.valid)number.value=state.parameters[key];});
  }
}

function sync(){
  $('vfx-seed').value=state.seed;$('vfx-palette').value=state.palette;$('vfx-resolution').value=state.resolution;
  for(const [key,value] of Object.entries(state.colors))$(`vfx-color-${key}`).value=value;
  for(const [key,{number,range}] of fields)number.value=range.value=state.parameters[key];
  $('vfx-export-name').value=`psx_explosion_${state.seed}`;
}

function queue(delay=220){
  revision++;pending=true;clearTimeout(timer);ready();status('Generating coherent frames…');
  $('vfx-count').textContent=`${Math.max(2,Math.round(state.parameters.duration*state.parameters.fps))} FRAMES · ${state.resolution} × ${state.resolution}`;
  timer=setTimeout(pump,delay);
}

async function pump(){
  if(busy||!pending)return;busy=true;pending=false;const version=revision,snapshot=structuredClone(state);ready();
  try{
    const result=await api('preview',snapshot);
    if(version!==revision)return;
    const bundle=await viewer.prepare(result);
    if(version!==revision){bundle.dispose();return;}
    current=result;currentRevision=version;state=structuredClone(result.recipe);
    $('vfx-scrub').max=result.metadata.frame_count-1;viewer.show(bundle);filmstrip(bundle);
    $('vfx-count').textContent=`${result.metadata.frame_count} FRAMES · ${state.resolution} × ${state.resolution} · ${result.metadata.cols} × ${result.metadata.rows} ATLAS`;
    status(`Ready · ${result.cached?'cache hit':result.elapsed_ms+' ms'} · ${result.metadata.playback_duration.toFixed(2)} s · seed ${state.seed}`);
  }catch(error){status(error.message,true);}
  finally{busy=false;ready();if(pending)pump();}
}

function filmstrip(bundle){
  $('vfx-filmstrip').replaceChildren();
  const m=bundle.metadata;
  for(let slot=0;slot<8;slot++){
    const index=Math.round(slot*(m.frame_count-1)/7),b=document.createElement('button'),canvas=document.createElement('canvas'),caption=document.createElement('span');
    b.type='button';b.setAttribute('aria-label',`View explosion frame ${index}`);canvas.width=canvas.height=m.frame_size;
    const [x,y,w,h]=m.rectangles[index];canvas.getContext('2d').drawImage(bundle.color.image,x,y,w,h,0,0,w,h);
    caption.textContent=`${String(index).padStart(2,'0')} · ${(index/m.fps).toFixed(2)}s`;b.append(canvas,caption);
    b.addEventListener('click',()=>viewer.scrub(index));$('vfx-filmstrip').append(b);
  }
}

function wire(){
  $('vfx-effect').addEventListener('change',()=>selectEffect($('vfx-effect').value));
  $('vfx-seed').addEventListener('change',()=>{const input=$('vfx-seed');if(input.value===''||!input.validity.valid){input.value=state.seed;return;}state.seed=Number(input.value);$('vfx-export-name').value=`psx_explosion_${state.seed}`;queue(0);});
  $('vfx-random').addEventListener('click',()=>{state.seed=crypto.getRandomValues(new Uint32Array(1))[0]%2147483648;sync();queue(0);});
  $('vfx-reset').addEventListener('click',()=>{const seed=state.seed;state=structuredClone(config.defaults);state.seed=seed;sync();queue(0);});
  $('vfx-palette').addEventListener('change',()=>{state.palette=$('vfx-palette').value;state.colors=structuredClone(config.palettes[state.palette]);sync();queue();});
  $('vfx-resolution').addEventListener('change',()=>{state.resolution=Number($('vfx-resolution').value);queue();});
  $('vfx-background').addEventListener('change',()=>viewer.background($('vfx-background').value));
  $('vfx-play').addEventListener('click',()=>viewer.toggle());$('vfx-restart').addEventListener('click',()=>viewer.restart());
  $('vfx-loop').addEventListener('change',()=>viewer.loop=$('vfx-loop').checked);
  $('vfx-scrub').addEventListener('input',()=>viewer.scrub(Number($('vfx-scrub').value)));
  $('vfx-save-recipe').addEventListener('click',()=>download({...current.recipe,generator_fingerprint:config.generator_fingerprint},`psx_explosion_${current.recipe.seed}.vfx.json`));
  $('vfx-load').addEventListener('click',()=>$('vfx-file').click());
  $('vfx-file').addEventListener('change',async()=>{
    try{const file=$('vfx-file').files[0];if(!file)return;const restored=await api('recipe/load',JSON.parse(await file.text()));state=restored;sync();queue(0);}
    catch(error){status(`Recipe not loaded: ${error.message}`,true);}finally{$('vfx-file').value='';}
  });
  $('vfx-export').addEventListener('click',async()=>{
    const name=$('vfx-export-name');if(!name.value||!name.reportValidity())return;
    const snapshot={recipe:structuredClone(current.recipe),name:name.value,format:$('vfx-export-format').value,emission:$('vfx-export-emission').checked};
    exporting=true;ready();$('vfx-export-result').textContent='Writing complete asset set…';
    try{const result=await api('export',snapshot);$('vfx-export-result').textContent=`SAVED ${result.name}\n${result.files.length} files · ${result.metadata.frame_count} frames\n${result.directory}\nOpen review.tscn in Godot.\nR: restart · Space: pause`;status(`Exported ${result.name}. Recipe and Godot review scene saved.`);}
    catch(error){$('vfx-export-result').textContent=error.message;status(error.message,true);}
    finally{exporting=false;ready();}
  });
}

async function start(){
  shell();config=await api('config');state=structuredClone(config.defaults);buildControls();sync();
  viewer=new VFXViewer($('vfx-viewport'),(index,playing)=>{
    $('vfx-scrub').value=index;$('vfx-play').textContent=playing?'PAUSE':'PLAY';
    const count=current?.metadata.frame_count||32;$('vfx-frame-label').textContent=`FRAME ${String(index).padStart(2,'0')} / ${count} · ${(index/(current?.metadata.fps||16)).toFixed(2)}s`;
  });
  viewer.visible=false;wire();await selectEffect(effectMode);
}

async function selectEffect(mode){
  effectMode=mode==='PSX_EXPLOSION'?'PSX_EXPLOSION':'MESH_EXPLOSION_3D';
  const mesh=effectMode==='MESH_EXPLOSION_3D';
  $('vfx-sprite-panel').hidden=mesh;$('vfx-mesh-panel').hidden=!mesh;
  const url=new URL(location.href);url.searchParams.set('vfx',effectMode);history.replaceState(null,'',url);
  viewer.visible=!mesh&&!$('vfx-tab').hidden;
  if(mesh&&!meshStarting){meshStarting=createMeshVFX($('vfx-mesh-panel'),selectEffect);meshApp=await meshStarting;}
  if(meshStarting)await meshStarting;
  if(meshApp)meshApp.setVisible(mesh&&!$('vfx-tab').hidden);
  if(!mesh){$('vfx-effect').value='PSX_EXPLOSION';viewer.resize();if(!current)queue(0);}
}

async function selectTab(name){
  const vfx=name==='vfx';
  for(const key of ['surface','vfx','billboard']){$(key+'-tab').hidden=key!==name;$(key+'-workspace-tab').setAttribute('aria-selected',String(key===name));}
  window.dispatchEvent(new CustomEvent('factory-tab',{detail:name}));
  const url=new URL(location.href);url.searchParams.set('tab',name);history.replaceState(null,'',url);
  if(vfx&&!started){started=start();started.catch(error=>{if($('vfx-status'))status(error.message,true);});}
  if(started)await started.catch(()=>{});
  if(viewer){viewer.visible=vfx&&effectMode==='PSX_EXPLOSION';if(viewer.visible)viewer.resize();}
  if(meshApp)meshApp.setVisible(vfx&&effectMode==='MESH_EXPLOSION_3D');
}
const workspaceNames=['surface','vfx','billboard'];
for(const [i,name] of workspaceNames.entries()){
  const button=$(name+'-workspace-tab');button.addEventListener('click',()=>selectTab(name));
  button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const next=workspaceNames[(i+(event.key==='ArrowRight'?1:2))%3];selectTab(next);$(next+'-workspace-tab').focus();}});
}
const initialTab=new URLSearchParams(location.search).get('tab');
selectTab(workspaceNames.includes(initialTab)?initialTab:'surface');
async function storageStatus(){try{const r=await fetch('/api/storage'),s=await r.json();$('storage-state').textContent=Number.isFinite(s.free_gib)?`DISK ${s.free_gib.toFixed(1)} GiB FREE · ${s.mode}`:'DISK RESERVE LOW';$('storage-state').classList.toggle('storage-warning',s.mode!=='NORMAL'||!r.ok);$('storage-state').title='Below 25 GiB: conserve. Below 15 GiB: generation stops.';}catch{}}
storageStatus();setInterval(storageStatus,30000);
