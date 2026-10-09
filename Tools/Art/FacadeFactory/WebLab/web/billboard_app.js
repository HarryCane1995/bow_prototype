import { BillboardViewer } from './billboard_viewer.js';
const $=id=>document.getElementById(id);
let started,viewer;

async function start(){
  const host=$('billboard-tab');
  host.innerHTML=`<header class="vfx-toolbar"><div class="vfx-brand"><strong>BILLBOARD FACTORY</strong><small>LOCAL / PROCEDURAL SIGNAGE</small></div>
    <label>ARCHETYPE<select id="sign-archetype"></select></label><label>SEED<input id="sign-seed" type="number" min="0" max="2147483647" value="99"></label>
    <button id="sign-random" class="accent">RANDOMIZE SEED</button><button id="sign-vary">VARY WITHIN PRESET</button></header>
  <div class="vfx-layout"><section class="sign-workspace"><div class="vfx-preview-bar"><span>ALBEDO / EMISSION / ORM</span><select id="sign-view" aria-label="Sign preview geometry"><option value="WALL">ON WALL</option><option value="PLANE">FREE PANEL</option></select><button id="sign-frame">FRAME</button></div>
    <div id="sign-viewport"><div class="vfx-caption"><span>PROCEDURAL / ORIGINAL LETTERING</span><h1 id="sign-title">Light with a purpose.</h1></div><div class="vfx-preview-note">DRAG TO ORBIT · WHEEL TO ZOOM · MAX DIMENSION = 3 m</div></div>
    <div class="sign-actions"><button id="sign-favorite" disabled>☆ FAVORITE</button><button id="sign-pin" disabled>PIN A</button><button id="sign-ab" disabled>SHOW A</button><button id="sign-capture" disabled>PREVIEW PNG ↓</button></div><div id="sign-status" class="vfx-statusbar" role="status">Preparing signs…</div></section>
    <aside class="vfx-sidebar"><span class="eyebrow">AUTHORING / MANUFACTURED LIGHT</span><h2>Shape the sign.</h2><div class="vfx-recipe-actions"><button id="sign-reset">RESET PRESET</button><button id="sign-load">LOAD RECIPE ↑</button></div><input id="sign-file" type="file" accept=".json" hidden>
    <section><h3>PALETTE</h3><select id="sign-palette"></select><div id="sign-colors" class="vfx-colors"></div></section><div id="sign-controls"></div>
    <label class="mesh-check"><input id="sign-support" type="checkbox"> SUPPORT FRAME</label><label class="mesh-check"><input id="sign-hazard" type="checkbox"> HAZARD STRIPE</label>
    <section class="vfx-export"><h3>EXPORT TO PROJECT</h3><label for="sign-name">ASSET NAME</label><input id="sign-name" maxlength="64" pattern="[a-zA-Z][a-zA-Z0-9_-]{0,63}" value="sign_99">
    <label for="sign-resolution">LONG EDGE</label><select id="sign-resolution"><option value="512">512 px / compact</option><option value="1024">1024 px / hero sign</option></select><button id="sign-export" class="export-button full" disabled>EXPORT SIGN ↗</button><button id="sign-save" class="full subtle" disabled>SAVE RECIPE ↓</button><p>PNG albedo / emission / ORM · .tres · sign.tscn<br>Assets/ProceduralArt/Billboards/</p><div id="sign-result" role="status"></div></section>
    <section><h3>RECIPE LIBRARY</h3><div id="sign-library" class="sign-library"></div></section></aside></div>`;
  let config,state,current,busy=false,pending=false,revision=0,shown=-1,timer,exporting=false,pinned=null,other=null,showA=false;
  const fields=new Map(),colors=new Map();
  const status=(msg,error=false)=>{$('sign-status').textContent=msg;$('sign-status').classList.toggle('error',error);};
  async function api(route,data){const response=await fetch('/api/billboard/'+route,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Facade-Token':config.token},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error);return result;}
  config=await api('config');state=structuredClone(config.defaults);viewer=new BillboardViewer($('sign-viewport'));
  function ready(){const ok=!!current&&!busy&&!pending&&revision===shown;host.dataset.phase=ok?'ready':'generating';for(const k of ['favorite','pin','capture','export','save'])$('sign-'+k).disabled=!ok||exporting;$('sign-ab').disabled=!ok||!pinned;}
  async function pump(){if(busy||!pending)return;busy=true;pending=false;const rev=revision,snapshot=structuredClone(state);ready();
    try{const result=await api('preview',snapshot);if(rev!==revision)return;await viewer.show(result);if(rev!==revision)return;current=result;state=structuredClone(result.recipe);shown=rev;
      $('sign-title').textContent=config.archetypes[state.archetype].label;status(`Ready · ${result.elapsed_ms} ms · seed ${state.seed} · ${result.cached?'cache':'local generation'}`);
    }catch(e){status(e.message,true);}finally{busy=false;ready();if(pending)pump();}}
  function queue(){revision++;pending=true;clearTimeout(timer);ready();timer=setTimeout(pump,120);}
  function sync(){$('sign-archetype').value=state.archetype;$('sign-seed').value=state.seed;$('sign-palette').value=state.palette;
    for(const [k,input] of fields){input.value=state.parameters[k];input.previousElementSibling.textContent=Number(input.value).toFixed(2);}
    for(const [k,input] of colors)input.value=state.colors[k];$('sign-support').checked=state.support_frame;$('sign-hazard').checked=state.hazard;
    fields.get('glyph_scale').closest('label').hidden=!['VERTICAL_NEON','GLYPH_MONOLITH'].includes(state.archetype);
    $('sign-name').value=state.archetype.toLowerCase()+'_'+state.seed;}
  function use(recipe){state=structuredClone(recipe);showA=false;$('sign-ab').textContent='SHOW A';sync();queue();}
  for(const [key,item] of Object.entries(config.archetypes))$('sign-archetype').add(new Option(item.label,key));
  for(const key of Object.keys(config.palettes))$('sign-palette').add(new Option(key.replaceAll('_',' '),key));
  for(const key of Object.keys(state.colors)){const label=document.createElement('label'),input=document.createElement('input');input.type='color';input.setAttribute('aria-label','Sign '+key+' color');label.append(input,document.createTextNode(key));$('sign-colors').append(label);colors.set(key,input);input.addEventListener('input',()=>{state.colors[key]=input.value;queue();});}
  for(const [key,[min,max,step,value,label]] of Object.entries(config.controls)){const row=document.createElement('label');row.className='mesh-material-field';row.textContent=label;const input=document.createElement('input');Object.assign(input,{type:'range',min,max,step,value});input.setAttribute('aria-label',label);row.append(document.createElement('output'),input);$('sign-controls').append(row);fields.set(key,input);input.addEventListener('input',()=>{state.parameters[key]=Number(input.value);input.previousElementSibling.textContent=Number(input.value).toFixed(2);queue();});}
  async function library(items){items=items||await api('library');$('sign-library').replaceChildren();for(const item of items){const button=document.createElement('button');button.className='sign-card';const image=new Image();image.src=item.thumbnail;image.alt=item.label;image.loading='lazy';const label=document.createElement('span');label.textContent=item.label;button.append(image,label);button.onclick=()=>use(item.recipe);$('sign-library').append(button);}}
  $('sign-archetype').onchange=()=>{const seed=state.seed;use({...config.archetypes[$('sign-archetype').value].recipe,seed});};
  $('sign-palette').onchange=()=>{state.palette=$('sign-palette').value;state.colors=structuredClone(config.palettes[state.palette]);sync();queue();};
  $('sign-seed').onchange=()=>{const input=$('sign-seed');if(!input.validity.valid||input.value===''){sync();return;}state.seed=Number(input.value);sync();queue();};
  const random=()=>crypto.getRandomValues(new Uint32Array(1))[0]%2147483648;
  $('sign-random').onclick=()=>{state.seed=random();sync();queue();};
  $('sign-vary').onclick=()=>{state.seed=random();for(const k of ['density','wear','grime']){const base=config.archetypes[state.archetype].recipe.parameters[k];state.parameters[k]=Math.min(1,Math.max(0,base+(random()/2147483648-.5)*.3));}sync();queue();};
  $('sign-reset').onclick=()=>use({...config.archetypes[state.archetype].recipe,seed:state.seed});
  for(const [id,key] of [['support','support_frame'],['hazard','hazard']])$('sign-'+id).onchange=()=>{state[key]=$('sign-'+id).checked;queue();};
  $('sign-view').onchange=()=>viewer.setWall($('sign-view').value==='WALL');$('sign-frame').onclick=()=>viewer.frame();
  const download=(data,name)=>{const a=document.createElement('a');a.href=data;a.download=name;a.click();};
  $('sign-capture').onclick=()=>download(viewer.capture(),'sign-preview.png');
  $('sign-pin').onclick=()=>{pinned=structuredClone(current.recipe);showA=false;$('sign-ab').textContent='SHOW A';ready();status('A pinned. Edit the live recipe, then compare.');};
  $('sign-ab').onclick=()=>{if(!showA){other=structuredClone(state);state=structuredClone(pinned);}else state=other;showA=!showA;$('sign-ab').textContent=showA?'SHOW B':'SHOW A';sync();queue();};
  $('sign-favorite').onclick=async()=>{try{const result=await api('favorites',current.recipe);await library(result.library);status('Recipe and compact thumbnail saved.');}catch(e){status(e.message,true);}};
  $('sign-save').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({...current.recipe,generator_fingerprint:config.generator_fingerprint},null,2)],{type:'application/json'}));download(url,$('sign-name').value+'.billboard.json');setTimeout(()=>URL.revokeObjectURL(url),1000);};
  $('sign-load').onclick=()=>$('sign-file').click();$('sign-file').onchange=async()=>{try{const f=$('sign-file').files[0];if(f)use(await api('recipe/load',JSON.parse(await f.text())));}catch(e){status(e.message,true);}finally{$('sign-file').value='';}};
  $('sign-export').onclick=async()=>{if(!$('sign-name').value||!$('sign-name').reportValidity())return;exporting=true;ready();try{const result=await api('export',{name:$('sign-name').value,resolution:Number($('sign-resolution').value),recipe:current.recipe});$('sign-result').textContent='Saved '+result.scene;status('Exported sign, material, maps and recipe.');}catch(e){status(e.message,true);}finally{exporting=false;ready();}};
  await library();sync();queue();
}

window.addEventListener('factory-tab',async event=>{const visible=event.detail==='billboard';if(visible&&!started)started=start().catch(e=>{$('billboard-tab').textContent=e.message;});if(started)await started;if(viewer){viewer.visible=visible;if(visible)viewer.resize();}});
