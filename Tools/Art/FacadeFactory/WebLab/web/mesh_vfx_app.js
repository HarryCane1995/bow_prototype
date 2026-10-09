import { MeshVFXViewer } from './mesh_vfx_viewer.js?v=2';

export async function createMeshVFX(host,onMode){
  const $=id=>document.getElementById(id);
  if(!document.getElementById('mesh-family-style')){const css=document.createElement('link');css.id='mesh-family-style';css.rel='stylesheet';css.href='./mesh_vfx.css?v=2';document.head.append(css);}
  host.innerHTML=`<header class="vfx-toolbar"><div class="vfx-brand"><strong>VFX FACTORY</strong><small>BOWPROTOTYPE / TEN MESH ARCHETYPES</small></div>
    <label>VFX MODE<select id="mesh-mode"><option value="MESH_EXPLOSION_3D">3D MESH EFFECTS</option><option>PSX_EXPLOSION</option></select></label>
    <label>ARCHETYPE<select id="mesh-effect" aria-label="VFX archetype"></select></label><label>SEED<input id="mesh-seed" aria-label="Mesh seed" type="number" min="0" max="2147483647" value="99"></label><button id="mesh-random" class="accent">↻ RANDOMIZE SEED</button><span id="mesh-stats" class="vfx-frame-count"></span></header>
    <div class="vfx-layout"><section class="mesh-workspace" aria-label="3D effect realtime preview">
      <div class="vfx-preview-bar"><span>REALTIME / MESH LAYERS</span><div class="mesh-preview-selects"><select id="mesh-view" aria-label="Mesh camera view"><option value="FREE">FREE ORBIT</option><option value="SIDE">SIDE</option><option value="TOP">TOP</option><option value="GAMEPLAY">GAMEPLAY DISTANCE</option></select><select id="mesh-background" aria-label="Mesh background"><option value="SCENE">IN-GAME DARK / FLOOR + CUBE</option><option value="BLACK">BLACK</option><option value="GRAY">NEUTRAL GRAY</option></select></div></div>
      <div id="mesh-viewport"><div class="vfx-caption"><span id="mesh-family-caption">3D / PROCEDURAL EFFECTS</span><h1 id="mesh-family-title">Industrial burst</h1><p id="mesh-family-description"></p></div><div class="vfx-preview-note">DRAG TO ORBIT · WHEEL TO ZOOM · REFERENCE CUBE = 1 m</div></div>
      <div class="vfx-playback"><button id="mesh-play" disabled>PAUSE</button><button id="mesh-restart" disabled>RESTART</button><input id="mesh-time" aria-label="Mesh effect time" type="range" min="0" max="2.4" step="0.01" value="0" disabled><label><input id="mesh-loop" type="checkbox" checked> LOOP</label><output id="mesh-time-label">0.00 / 2.40 s</output></div>
      <div id="mesh-status" class="vfx-statusbar" role="status">Building mesh layers…</div>
    </section><aside class="vfx-sidebar" aria-label="3D effect controls"><span class="eyebrow">AUTHORING / SHAPE + MATERIALS</span><h2>Shape the effect.</h2><div class="vfx-recipe-actions"><button id="mesh-reset">RESET EFFECT</button><button id="mesh-load">LOAD RECIPE ↑</button></div><input id="mesh-file" type="file" accept=".json,application/json" hidden><div class="vfx-recipe-actions mesh-variation-actions"><button id="mesh-vary">VARY WITHIN PRESET</button><button id="mesh-favorite">SAVE TO LIBRARY</button></div><details id="mesh-library-panel"><summary>RECIPE LIBRARY / 10 ARCHETYPES</summary><div id="mesh-library" class="mesh-library"></div></details><div id="mesh-control-groups"></div>
    <section class="vfx-export"><h3>RUNTIME EXPORT</h3><label for="mesh-export-name">ASSET NAME</label><input id="mesh-export-name" value="mesh_explosion_99" maxlength="64" pattern="[a-zA-Z][a-zA-Z0-9_-]{0,63}"><p>Triangle meshes · per-layer materials<br>Animated .tscn effect + orbit review scene</p><button id="mesh-export" class="export-button full" disabled>EXPORT MESH EFFECT ↗</button><button id="mesh-save" class="full subtle" disabled>SAVE MESH RECIPE ↓</button><p>Assets/ProceduralArt/VFX/<br>Existing exports receive a new revision.</p><div id="mesh-export-result" class="vfx-export-result" role="status"></div></section></aside></div>`;
  let config,state,current,revision=0,currentRevision=-1,busy=false,pending=false,timer,exporting=false;
  const controls=new Map(),materialControls=new Map();
  const status=(text,error=false)=>{$('mesh-status').textContent=text;$('mesh-status').classList.toggle('error',error);};
  async function api(route,data){const r=await fetch(`/api/mesh-vfx/${route}`,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Facade-Token':config.token},body:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw new Error(result.error||'Mesh generation failed');return result;}
  config=await api('config');state=structuredClone(config.defaults);
  for(const [id,meta] of Object.entries(config.effects))$('mesh-effect').add(new Option(meta.label,id));
  let favorites=[];try{favorites=JSON.parse(localStorage.getItem('bow.mesh-vfx.favorites.v2')||'[]');if(!Array.isArray(favorites))favorites=[];}catch{}
  const naming=()=>`${config.effects[state.effect].slug}_${state.seed}`;
  function applyRecipe(recipe){state=structuredClone(recipe);sync();queue(0);}
  function library(){const grid=$('mesh-library');grid.replaceChildren();for(const item of [...Object.entries(config.effects).map(([id,m])=>({label:m.label,recipe:m.recipe,thumbnail:m.thumbnail})),...favorites]){
    const button=document.createElement('button');button.className='mesh-recipe-card';button.type='button';button.title=item.label;
    if(item.thumbnail){const img=document.createElement('img');img.src=item.thumbnail;img.alt=item.label;img.loading='lazy';button.append(img);}
    const label=document.createElement('span');label.textContent=item.label;button.append(label);button.addEventListener('click',()=>applyRecipe(item.recipe));grid.append(button);}}
  const viewer=new MeshVFXViewer($('mesh-viewport'),(time,playing)=>{$('mesh-time').value=time;$('mesh-time-label').textContent=`${time.toFixed(2)} / ${(current?.duration||state.parameters.duration).toFixed(2)} s`;$('mesh-play').textContent=playing?'PAUSE':'PLAY';});
  function ready(){const ok=!!current&&!busy&&!pending&&revision===currentRevision;$('mesh-export').disabled=!ok||exporting;$('mesh-save').disabled=!ok;host.dataset.phase=ok?'ready':'generating';for(const id of ['mesh-play','mesh-restart','mesh-time'])$(id).disabled=!current;}
  function queue(delay=140){revision++;pending=true;clearTimeout(timer);ready();status('Updating geometry and layer materials…');timer=setTimeout(pump,delay);}
  async function pump(){
    if(busy||!pending)return;busy=true;pending=false;const version=revision,snapshot=structuredClone(state);ready();
    try{const result=await api('preview',snapshot);if(version!==revision)return;
      const retain=!!current&&current.recipe.seed===result.recipe.seed&&current.recipe.effect===result.recipe.effect,playing=viewer.playing,time=viewer.time;
      current=result;state=structuredClone(result.recipe);currentRevision=version;$('mesh-time').max=result.duration;viewer.show(result);
      if(retain){viewer.time=Math.min(time,result.duration);viewer.playing=playing;viewer.applyTime(viewer.time);}
      $('mesh-stats').textContent=`${result.stats.mesh_count} MESHES · ${result.stats.triangle_count.toLocaleString()} TRIANGLES`;
      status(`Ready · ${result.elapsed_ms} ms · ${result.duration.toFixed(2)} s · seed ${state.seed} · real 3D geometry`);
    }catch(error){status(error.message,true);}finally{busy=false;ready();if(pending)pump();}
  }
  const groups=new Map();
  for(const group of ['GLOBAL','EFFECT SHAPE',...new Set(Object.values(config.controls).map(v=>v[5]).filter(v=>!['GLOBAL','EFFECT SHAPE'].includes(v)))]){
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=group;
    details.open=['GLOBAL','PETALS / FIRE'].includes(group);details.append(summary);groups.set(group,details);$('mesh-control-groups').append(details);
  }
  for(const [key,[low,high,step,value,label,group]] of Object.entries(config.controls)){
    const row=document.createElement('div');row.className='vfx-field';const text=document.createElement('label');text.textContent=label;text.htmlFor=`mesh-${key}`;
    const number=document.createElement('input'),range=document.createElement('input');number.type='number';range.type='range';range.id=`mesh-${key}`;
    for(const input of [number,range]){Object.assign(input,{min:low,max:high,step,value});input.setAttribute('aria-label',`Mesh ${label}${input===number?' numeric value':''}`);}
    const change=input=>{if(input.value===''||!input.validity.valid)return;state.parameters[key]=Number(input.value);number.value=range.value=input.value;queue();};
    range.addEventListener('input',()=>change(range));number.addEventListener('input',()=>change(number));number.addEventListener('blur',()=>{if(!number.validity.valid||number.value==='')number.value=state.parameters[key];});
    controls.set(key,{number,range,row});row.append(text,number,range);groups.get(group).append(row);
  }
  for(const [layer,group] of Object.entries(config.layer_groups)){
    const parent=groups.get(group),fields=new Map();materialControls.set(layer,fields);
    function check(key,label,container=parent){const row=document.createElement('label');row.className='mesh-check';const input=document.createElement('input');input.type='checkbox';input.setAttribute('aria-label',`${layer} ${label}`);row.append(input,document.createTextNode(label));container.append(row);fields.set(key,input);input.addEventListener('change',()=>{state.layers[layer][key]=input.checked;queue();});return row;}
    const enabled=check('enabled','Enable layer');parent.insertBefore(enabled,parent.children[1]);
    const colorRow=document.createElement('div');colorRow.className='vfx-colors';parent.append(colorRow);
    for(const [key,label] of [['color','Color A'],['color_b','Color B']]){const row=document.createElement('label'),input=document.createElement('input');input.type='color';input.setAttribute('aria-label',`${layer} ${label}`);row.append(input,document.createTextNode(label));colorRow.append(row);fields.set(key,input);input.addEventListener('input',()=>{state.layers[layer][key]=input.value;queue();});}
    function scalar(key,label,high,container=parent){const row=document.createElement('label');row.className='mesh-material-field';row.textContent=label;const input=document.createElement('input');Object.assign(input,{type:'range',min:0,max:high,step:.01});input.setAttribute('aria-label',`${layer} ${label}`);const value=document.createElement('output');row.append(value,input);container.append(row);fields.set(key,input);input.addEventListener('input',()=>{state.layers[layer][key]=Number(input.value);value.textContent=Number(input.value).toFixed(2);queue();});}
    scalar('opacity','Opacity',1);scalar('emission','Emission',5);
    function select(key,label,options,container=parent){const row=document.createElement('label');row.className='mesh-material-select';row.textContent=label;const input=document.createElement('select');input.setAttribute('aria-label',`${layer} ${label}`);for(const o of options)input.add(new Option(o.replaceAll('_',' '),o));row.append(input);container.append(row);fields.set(key,input);input.addEventListener('change',()=>{state.layers[layer][key]=input.value;if(key==='blend'){state.layers[layer].depth_write=input.value==='DITHER';fields.get('depth_write').checked=state.layers[layer].depth_write;}queue();});}
    select('blend','Blend mode',['ALPHA','DITHER','ADDITIVE']);
    const extra=document.createElement('details');extra.className='mesh-material-extra';const caption=document.createElement('summary');caption.textContent='Material response';extra.append(caption);parent.append(extra);
    select('fade_curve','Fade curve',['LINEAR','EASE_OUT','SMOOTH'],extra);scalar('soft_alpha','Soft gradient alpha',1,extra);
    check('unshaded','Unshaded',extra);check('depth_write','Write depth',extra);check('cull_back','Cull back faces',extra);
  }
  function sync(){
    $('mesh-seed').value=state.seed;$('mesh-export-name').value=naming();$('mesh-effect').value=state.effect;
    const meta=config.effects[state.effect],classic=state.effect==='MESH_EXPLOSION_3D';
    $('mesh-family-title').textContent=meta.label.slice(5);$('mesh-family-description').textContent=meta.description;
    for(const [group,node] of groups)node.hidden=!['GLOBAL','RETRO STYLE'].includes(group)&&group!=='EFFECT SHAPE'&&!classic&&!Object.entries(config.layer_groups).some(([layer,g])=>g===group&&state.layers[layer].enabled);
    groups.get('EFFECT SHAPE').hidden=classic;groups.get('EFFECT SHAPE').open=!classic;
    groups.get('PETALS / FIRE').open=classic;
    for(const [key,control] of controls){const group=config.controls[key][5];control.row.hidden=group==='EFFECT SHAPE'?!meta.shape_controls.includes(key):!classic&&!['GLOBAL','RETRO STYLE'].includes(group)&&!(state.effect==='SMOKE_BURST'&&['smoke_puff_size','smoke_darkness'].includes(key))&&!(state.effect==='ENERGY_ORB'&&['core_size','core_lifetime'].includes(key));}
    for(const [key,{number,range}] of controls)number.value=range.value=state.parameters[key];
    for(const [layer,fields] of materialControls)for(const [key,input] of fields){if(input.type==='checkbox')input.checked=state.layers[layer][key];else input.value=state.layers[layer][key];if(input.type==='range')input.previousElementSibling.textContent=Number(input.value).toFixed(2);}
  }
  function download(doc){const url=URL.createObjectURL(new Blob([JSON.stringify(doc,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=`${config.effects[doc.effect].slug}_${doc.seed}.meshvfx.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  $('mesh-effect').addEventListener('change',()=>applyRecipe(config.effects[$('mesh-effect').value].recipe));
  $('mesh-favorite').addEventListener('click',()=>{if(!current||busy||pending)return;favorites.unshift({label:`${config.effects[state.effect].label} / ${state.seed}`,recipe:structuredClone(current.recipe),thumbnail:viewer.snapshot(config.effects[state.effect].sample_time)});favorites=favorites.slice(0,12);try{localStorage.setItem('bow.mesh-vfx.favorites.v2',JSON.stringify(favorites));library();status('Recipe and thumbnail saved in this browser library. SAVE MESH RECIPE gives a portable JSON.');}catch(error){status('Browser library is full; use SAVE MESH RECIPE.',true);}});
  $('mesh-vary').addEventListener('click',()=>{const meta=config.effects[state.effect];state.seed=crypto.getRandomValues(new Uint32Array(1))[0]%2147483648;let seed=state.seed;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};const keys=meta.shape_controls.length?meta.shape_controls:['petal_count','petal_length','petal_width','petal_curl','ring_radius','shard_count'];for(const key of keys){const [lo,hi,step]=config.controls[key];const base=meta.recipe.parameters[key],value=base*(.8+random()*.4);state.parameters[key]=Number((Math.max(lo,Math.min(hi,Math.round(value/step)*step))).toFixed(5));}sync();queue(0);});
  $('mesh-mode').addEventListener('change',()=>onMode($('mesh-mode').value));
  $('mesh-seed').addEventListener('change',()=>{const i=$('mesh-seed');if(i.value===''||!i.validity.valid){i.value=state.seed;return;}state.seed=Number(i.value);$('mesh-export-name').value=naming();queue(0);});
  $('mesh-random').addEventListener('click',()=>{state.seed=crypto.getRandomValues(new Uint32Array(1))[0]%2147483648;sync();queue(0);});
  $('mesh-reset').addEventListener('click',()=>{const seed=state.seed;state=structuredClone(config.effects[state.effect].recipe);state.seed=seed;sync();queue(0);});
  $('mesh-view').addEventListener('change',()=>viewer.setView($('mesh-view').value));
  $('mesh-background').addEventListener('change',()=>{viewer.background($('mesh-background').value);viewer.setView($('mesh-view').value);});
  $('mesh-play').addEventListener('click',()=>viewer.toggle());$('mesh-restart').addEventListener('click',()=>viewer.restart());$('mesh-time').addEventListener('input',()=>viewer.seek(Number($('mesh-time').value)));$('mesh-loop').addEventListener('change',()=>viewer.loop=$('mesh-loop').checked);
  $('mesh-save').addEventListener('click',()=>download({...current.recipe,generator_fingerprint:config.generator_fingerprint}));
  $('mesh-load').addEventListener('click',()=>$('mesh-file').click());$('mesh-file').addEventListener('change',async()=>{try{const file=$('mesh-file').files[0];if(!file)return;state=await api('recipe/load',JSON.parse(await file.text()));sync();queue(0);}catch(error){status(error.message,true);}finally{$('mesh-file').value='';}});
  $('mesh-export').addEventListener('click',async()=>{
    const name=$('mesh-export-name');if(!name.value||!name.reportValidity())return;const snapshot={name:name.value,recipe:structuredClone(current.recipe)};exporting=true;ready();$('mesh-export-result').textContent='Writing mesh scene and materials…';
    try{const result=await api('export',snapshot);$('mesh-export-result').textContent=`SAVED ${result.name}\n${result.stats.mesh_count} active meshes · ${result.stats.triangle_count} triangles\n${result.directory}\nOpen review.tscn · reusable effect.tscn`;status(`Exported ${result.name}. Meshes, materials, player and recipe saved.`);}
    catch(error){$('mesh-export-result').textContent=error.message;status(error.message,true);}finally{exporting=false;ready();}
  });
  library();sync();queue(0);
  return {setVisible(visible){viewer.visible=visible;if(visible){$('mesh-mode').value='MESH_EXPLOSION_3D';viewer.resize();}}};
}
