import { FacadeViewer } from './facade_viewer.js?v=0.4';
import { ParameterControls } from './controls.js?v=0.4';
import { PaletteControls } from './palette_controls.js?v=0.4';
import { renderFavoriteThumbnail } from './favorite_thumbnail.js?v=1';
import { mountMaterialLibrary } from './material_library.js?v=1';

const $ = id => document.getElementById(id);
const copy = value => structuredClone(value);
const directions = {
  CORPORATE_MONOLITH: ['01', 'Quiet authority.', 'Vertical bays. Precise mullions. Restrained emission.'],
  MEGABLOCK: ['02', 'A city in a block.', 'Heavy floor bands. Deep voids. Occupied clusters.'],
  INDUSTRIAL_TOWER: ['03', 'Service & structure.', 'Utility bays. Continuous ducts. Controlled light.'],
  EXOSKELETON_TOWER: ['04', 'Structure on the outside.', 'Diagonal braces. Inset windows. Large structural bays.'],
  OFFICE_GRID: ['05', 'Order, then variation.', 'Dense window grids. Occupancy patterns. Dark floors.'],
  LANDMARK_TECH: ['06', 'A signal in the skyline.', 'Asymmetric zones. Light spines. Vertical rhythm.'],
};
let config, controls, viewer, state, current, pinned, showA = false;
let paletteControls, comparisonViewers=[], comparing=false, comparisonGeneration=0;
let revision = 0, currentRevision = -1, busy = false, pending = null, timer;
let exportSnapshot, lastExport, cleanRestore = null;
let savingFavorite = false;
let preferredExportSize = [512, 1024];
const timings = [];
const modeState=new Map();

function status(message, error = false) {
  $('status').textContent = message;
  document.querySelector('.statusbar').classList.toggle('error', error);
}

async function api(path, data) {
  const response = await fetch(`/api/${path}`, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json', 'X-Facade-Token': config.token},
    body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

function defaults(name = state.preset) { return config.presets.find(p => p.name === name).defaults; }
function active() { return showA ? pinned : current; }

function readyButtons() {
  const ready = !!active() && (showA || (!busy && !pending && currentRevision === revision));
  for (const id of ['export', 'favorite', 'capture', 'pin']) $(id).disabled = !ready;
  $('favorite').disabled = !ready || savingFavorite;
  $('compare').disabled = !pinned || !current;
  document.body.dataset.phase = ready ? 'ready' : 'generating';
}

function syncControls() {
  paletteControls.restore(state.palette_mix);
  $('palette').hidden=state.palette_mix.enabled;
  $('palette').previousElementSibling.hidden=state.palette_mix.enabled;
  $('surface-mode').value=state.surface_mode;
  const options=config.presets.filter(p=>p.defaults.surface_mode===state.surface_mode);
  $('preset').replaceChildren(...options.map(p=>new Option(p.name,p.name)));
  $('preset').value = state.preset;
  $('seed').value = state.seed;
  $('palette').value = state.palette;
  controls.restore(state, defaults());
  $('art-profile').value=state.art.profile;
  const layered=state.breakup.mode==='LAYERED';
  $('breakup-mode').value=state.breakup.mode;
  $('detail-export-mode').value=state.breakup.export_mode;
  $('detail-export-mode').disabled=!layered;
  $('breakup-controls').hidden=!layered;
  $('breakup-preview').disabled=!layered;
  $('clean-base').textContent=cleanRestore?'RESTORE LAYERS':'CLEAN BASE';
  $('breakup-note').textContent=layered?'Main normal = structural height. Separate exports keep base maps clean; detail sources remain reusable at zero.':'Exact original baked renderer. Switch to layered mode to control decoration independently.';
  for(const id of ['parameters-macro_variation','parameters-surface_wear'])$(id).closest('.slider-row').hidden=layered;
  const unique=state.surface_mode==='UNIQUE_FACADE';
  $('art-profile').querySelector('[value="LEGACY"]').disabled=!unique;
  $('meta-controls').hidden=state.art.profile==='LEGACY';
  $('art-controls').closest('details').hidden=state.art.profile==='LEGACY';
  $('art-compare').hidden=!unique;
  $('primary-controls').hidden=!unique;$('facade-advanced').hidden=!unique;$('material-controls').hidden=!unique;
  $('surface-controls').hidden=state.surface_mode!=='TILEABLE_SURFACE';
  $('cylinder-controls').hidden=state.surface_mode!=='CYLINDER_WRAP';
  $('tile-mode-field').hidden=unique;
  $('tile-mode').value=state.tile_mode;
  $('tile-mode').disabled=state.surface_mode==='TILEABLE_SURFACE';
  $('surface-review').hidden=unique;
  document.querySelector('.preview-controls .note:not(#seam-qa)').textContent=unique?'Unique sheets. Tiling exposes repetition; PNGs stay unchanged.':'Periodic maps. Review buttons show 3×3 tiles or one cylinder wrap.';
  document.querySelector('.panel-title h2').textContent=unique?'Shape the facade':'Shape the surface';
}

function describe(bundle) {
  const r = bundle.recipe, direction = directions[r.preset] || ['SF',r.preset.replaceAll('_',' ').toLowerCase()+'.',r.surface_mode==='TILEABLE_SURFACE'?'A continuous material. Repeat in both directions.':'One continuous circumference. Inspect the wrap seam.'];
  $('scene-index').textContent = `${direction[0]} / ${r.preset.replaceAll('_', ' ')}`;
  $('scene-title').textContent = direction[1];
  $('scene-description').textContent = direction[2];
  $('recipe-title').textContent = `${r.preset} · ${r.seed}`;
  $('compare-tag').textContent = `${showA ? 'A' : 'B'} / ${r.breakup.mode==='LEGACY_BAKED'?'LEGACY BAKED':Object.keys(config.breakup_controls).every(k=>r.breakup[k]===0)?'CLEAN + SEPARATE':'LAYERED'}`;
  $('compare').textContent = showA ? 'SHOW B' : 'SHOW A';
  $('compare').classList.toggle('pinned', showA);
  $('generation-info').textContent = `${r.resolution.join(' × ')} preview · ${bundle.cached ? 'cache hit' : `${Math.round(bundle.generation_ms)} ms generation`}`;
  $('hash-info').textContent = `RECIPE ${bundle.key.slice(0, 12)} / ${Object.keys(bundle.maps).length} MAPS`;
  $('thumbs').replaceChildren();
  for (const [channel, url] of Object.entries(bundle.maps)) {
    const button = document.createElement('button');
    button.className = 'map-thumb';
    button.title = `View ${channel} map`;
    const img = new Image(); img.src = url; img.alt = `${channel} texture`;
    const label = document.createElement('span'); label.textContent = channel.toUpperCase();
    button.append(img, label); button.addEventListener('click', () => setMap(channel));
    $('thumbs').append(button);
  }
  viewer.setOptions({emissionStrength: r.parameters.emission_strength??1.15});
  $('seam-qa').textContent=bundle.seam_qa ? `SEAM QA ${bundle.seam_qa.passed?'PASS':'FAIL'} · ${bundle.seam_qa.axes.join(' + ')} · ${Object.keys(bundle.seam_qa.channels).length} maps · boundary Δ 0` : 'Unique sheet · no tiling claim';
  viewer.show(bundle);
}

function schedulePreview(delay = 120) {
  closePaletteComparison();
  revision++;
  showA = false;
  clearTimeout(timer);
  pending = null;
  $('loading').textContent = 'GENERATING…';
  $('loading').classList.remove('hidden');
  status('Generating a preview — editing remains available.');
  readyButtons();
  timer = setTimeout(() => { pending = {recipe: copy(state), revision}; pump(); }, delay);
}

async function pump() {
  if (busy || !pending) return;
  const job = pending; pending = null; busy = true; readyButtons();
  let prepared;
  try {
    const response = await api('preview', job.recipe);
    if (job.revision !== revision) return;
    prepared = await viewer.prepareMaps(response);
    if (job.revision !== revision) { prepared.dispose(); return; }
    const previous = current;
    current = prepared; currentRevision = job.revision;
    state=copy(response.recipe); syncControls();
    describe(current);
    if (previous && previous !== pinned) previous.dispose();
    if (!response.cached) timings.push(response.generation_ms);
    $('loading').classList.add('hidden');
    status(response.cached ? 'Ready · cached recipe restored.' : `Ready · ${Math.round(response.generation_ms)} ms · Python → ${Object.keys(response.maps).length} maps → WebGL`);
  } catch (error) {
    if (job.revision === revision) {
      status(error.message, true); $('loading').textContent = 'PREVIEW ERROR';
      document.body.dataset.phase = 'error';
    }
  } finally {
    busy = false; readyButtons();
    if (pending) pump();
  }
}

function setMap(mode) {
  document.querySelectorAll('[data-map]').forEach(button => button.classList.toggle('active', button.dataset.map === mode));
  viewer.setOptions({map: mode});
  $('view-mode-label').textContent = mode === 'material' ? 'MATERIAL / PBR' : `${mode.toUpperCase()} / MAP DEBUG`;
}

function setSeed(value) {
  if (!Number.isSafeInteger(value) || value < 0 || value > 2147483647) {
    $('seed').value = state.seed; status('Seed must be an integer from 0 to 2147483647.', true); return;
  }
  if (state.seed === value) return;
  state.seed = value; $('seed').value = value; schedulePreview();
}

function randomUnit() { return crypto.getRandomValues(new Uint32Array(1))[0] / 4294967296; }

function setUV(x, y) {
  if (![x, y].every(v => Number.isFinite(v) && v >= .25 && v <= 32)) {
    status('UV scale must be between 0.25 and 32.', true); return;
  }
  $('uv-x').value = x; $('uv-y').value = y;
  document.querySelectorAll('[data-tile]').forEach(b => b.classList.toggle('active', Number(b.dataset.tile) === x && x === y));
  viewer.setOptions({uvX: x, uvY: y});
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

async function restoreRecipe(doc) {
  const restored = await api('recipe/load', doc);
  cleanRestore=null;
  if (restored.resolution[0] >= 512) preferredExportSize = [...restored.resolution];
  const changedMode=state.surface_mode!==restored.surface_mode;
  state = {...restored, resolution: [...config.preview_resolutions[restored.surface_mode]]};
  syncControls(); if(changedMode)resetGeometry(); else if(state.surface_mode==='TILEABLE_SURFACE')setUV(3*state.parameters.tile_scale,3*state.parameters.tile_scale); schedulePreview(0);
}

function resetGeometry(){
  const mode=state.surface_mode;
  const shape=mode==='UNIQUE_FACADE'?'BOX':mode==='TILEABLE_SURFACE'?'FLOOR_PATCH':'CYLINDER';
  const scale=mode==='TILEABLE_SURFACE'?3*state.parameters.tile_scale:1;
  $('shape').value=shape;viewer.setShape(shape);setUV(scale,scale);
  setMap('material');
}

async function artComparison(){
  if(busy || pending)return;
  $('art-compare').disabled=true;
  const snapshot=copy(state), jobRevision=revision;
  status('Preparing A from the identical structural recipe…');
  try{
    const legacy=await api('preview',{...snapshot,art:{profile:'LEGACY'},breakup:{...snapshot.breakup,mode:'LEGACY_BAKED'},palette_mix:{...snapshot.palette_mix,enabled:false}});
    const bundle=await viewer.prepareMaps(legacy);
    if(jobRevision!==revision){bundle.dispose();return;}
    if(pinned && pinned!==current)pinned.dispose();pinned=bundle;
    state={...snapshot,art:copy(config.art_default)};
    $('pin').textContent='A / LEGACY PINNED';syncControls();schedulePreview(0);
  }catch(error){status(error.message,true);}finally{$('art-compare').disabled=false;}
}

async function breakupComparison(){
  if(busy || pending)return;
  $('breakup-compare').disabled=true;
  const snapshot=copy(state), jobRevision=revision;
  status('Preparing A / original baked noise from this exact layout and seed…');
  try{
    const result=await api('preview',{...snapshot,breakup:{...snapshot.breakup,mode:'LEGACY_BAKED',export_mode:'BAKED'},palette_mix:{...snapshot.palette_mix,enabled:false}});
    const bundle=await viewer.prepareMaps(result);
    if(jobRevision!==revision){bundle.dispose();return;}
    if(pinned && pinned!==current)pinned.dispose();pinned=bundle;
    cleanRestore=Object.fromEntries(Object.keys(config.breakup_controls).map(k=>[k,snapshot.breakup[k]]));
    state={...snapshot,palette_mix:{...snapshot.palette_mix,enabled:false},breakup:{...snapshot.breakup,mode:'LAYERED',export_mode:'SEPARATE',...Object.fromEntries(Object.keys(config.breakup_controls).map(k=>[k,0]))}};
    $('pin').textContent='A / BAKED PINNED';
    syncControls();schedulePreview(0);
  }catch(error){status(error.message,true);}finally{$('breakup-compare').disabled=false;}
}

function closePaletteComparison(){
  comparisonGeneration++;
  for(const item of comparisonViewers)item.dispose();comparisonViewers=[];
  $('palette-comparison').hidden=true;
  $('palette-compare-cards').replaceChildren();
}

async function paletteComparison(){
  if(busy||pending||comparing)return;
  comparing=true;$('compare-palettes').disabled=true;
  const snapshot=copy(state), jobRevision=revision;
  const variants=['NEUTRAL_COLD','INDUSTRIAL_GREEN','WARNING_ORANGE'];
  closePaletteComparison();status('Preparing three palettes from the same structural recipe…');
  const generation=comparisonGeneration;
  try{
    const results=[];
    for(const name of variants)results.push(await api('preview',{...snapshot,breakup:{...snapshot.breakup,mode:'LAYERED'},palette_mix:copy(config.palette_presets[name])}));
    if(jobRevision!==revision||generation!==comparisonGeneration)return;
    const normalMatch=results.every(r=>r.sha256.normal===results[0].sha256.normal);
    const heightMatch=results.every(r=>r.sha256.height===results[0].sha256.height);
    if(!normalMatch||!heightMatch)throw new Error('Palette comparison failed structure invariance QA');
    $('palette-comparison').hidden=false;
    $('palette-comparison').dataset.normalMatch=String(normalMatch);$('palette-comparison').dataset.heightMatch=String(heightMatch);
    $('palette-proof').textContent=`${snapshot.preset} · SEED ${snapshot.seed} · IDENTICAL NORMAL + HEIGHT · SAME CAMERA / UV`;
    for(let i=0;i<results.length;i++){
      const result=results[i], card=document.createElement('article');card.className='palette-card';card.dataset.recipeKey=result.key;
      card.dataset.normalHash=result.sha256.normal;card.dataset.heightHash=result.sha256.height;
      const header=document.createElement('header');header.innerHTML=`<strong>${'ABC'[i]} / ${variants[i].replaceAll('_',' ')}</strong>`;
      const swatches=document.createElement('div');swatches.className='compare-swatches';
      for(const [role,color] of Object.entries(result.recipe.palette_mix.colors)){const chip=document.createElement('i');chip.style.background=color;chip.title=role+' '+color;swatches.append(chip);}
      header.append(swatches);const host=document.createElement('div');host.className='palette-card-viewport';
      const edit=document.createElement('button');edit.textContent=`EDIT / EXPORT ${'ABC'[i]}`;
      edit.addEventListener('click',()=>{state=copy(result.recipe);syncControls();schedulePreview(0);});
      card.append(header,host,edit);$('palette-compare-cards').append(card);
      const small=new FacadeViewer(host);comparisonViewers.push(small);small.setShape('PLANE');small.setOptions({uvX:1,uvY:1,breakupOn:true});small.resize();
      const bundle=await small.prepareMaps(result);
      if(jobRevision!==revision||generation!==comparisonGeneration){bundle.dispose();closePaletteComparison();return;}
      small.show(bundle);small.controls.target.set(0,6.5,0);
      const distance=13/(2*Math.tan(small.camera.fov*Math.PI/360)*Math.min(small.camera.aspect,1))*1.12;
      small.camera.position.set(0,6.5,distance);small.controls.update();
    }
    status('A/B/C ready · normal + height byte-identical. Select EDIT / EXPORT for a variant.');
  }catch(error){closePaletteComparison();status(error.message,true);}
  finally{comparing=false;$('compare-palettes').disabled=false;}
}

async function loadFavorites() {
  const entries = await api('favorites');
  $('favorites').replaceChildren();
  if (!entries.length) {
    const note = document.createElement('p'); note.className = 'note'; note.textContent = 'Star a recipe to keep it here.'; $('favorites').append(note);
  }
  for (const entry of entries) {
    const b = document.createElement('button'); b.className = 'favorite-item';
    b.dataset.favoriteId = entry.id;
    const thumbnail = document.createElement('div'); thumbnail.className = 'favorite-thumbnail';
    const placeholder = document.createElement('span'); placeholder.className = 'favorite-placeholder';
    placeholder.setAttribute('aria-hidden', 'true');
    placeholder.textContent = 'NO PREVIEW'; thumbnail.append(placeholder);
    if (entry.thumbnail_url) {
      const image = document.createElement('img');
      image.alt = `${entry.recipe.preset} material preview`; image.width = 256; image.height = 160;
      image.loading = 'lazy'; image.decoding = 'async';
      image.addEventListener('error', () => image.remove(), {once: true});
      image.src = entry.thumbnail_url; thumbnail.append(image);
    }
    const metadata = document.createElement('div'); metadata.className = 'favorite-metadata';
    const title = document.createElement('strong'); title.textContent = `★ ${entry.recipe.preset} · ${entry.recipe.seed}`;
    const resolution = document.createElement('span'); resolution.textContent = entry.recipe.resolution.join(' × ');
    const timestamp = document.createElement('time'); timestamp.dateTime = entry.recipe.created_at;
    timestamp.textContent = new Date(entry.recipe.created_at).toLocaleString(undefined,
      {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
    metadata.append(title, resolution, timestamp); b.append(thumbnail, metadata);
    b.addEventListener('click', () => restoreRecipe(entry.recipe).catch(e => status(e.message, true)));
    $('favorites').append(b);
  }
}

function wireEvents() {
  $('palette-enabled').addEventListener('change',()=>{state.palette_mix.enabled=$('palette-enabled').checked;if(state.palette_mix.enabled)state.breakup.mode='LAYERED';syncControls();schedulePreview();});
  $('palette-preset').addEventListener('change',()=>{state.palette_mix=copy(config.palette_presets[$('palette-preset').value]);state.breakup.mode='LAYERED';syncControls();schedulePreview();});
  $('reset-palette').addEventListener('click',()=>{state.palette_mix=copy(config.palette_presets[state.palette_mix.preset]);syncControls();schedulePreview();});
  $('random-palette').addEventListener('click',async()=>{
    const snapshot=copy(state.palette_mix),jobRevision=revision;$('random-palette').disabled=true;
    try{const palette=await api('palette/randomize',{palette_mix:snapshot,random_seed:crypto.getRandomValues(new Uint32Array(1))[0]});if(jobRevision===revision){state.palette_mix=palette;syncControls();schedulePreview();}}
    catch(error){status(error.message,true);}finally{$('random-palette').disabled=false;}
  });
  $('compare-palettes').addEventListener('click',paletteComparison);
  $('close-palette-comparison').addEventListener('click',closePaletteComparison);
  $('breakup-mode').addEventListener('change',()=>{state.breakup.mode=$('breakup-mode').value;if(state.breakup.mode==='LEGACY_BAKED')state.palette_mix.enabled=false;cleanRestore=null;syncControls();schedulePreview();});
  $('detail-export-mode').addEventListener('change',()=>{state.breakup.export_mode=$('detail-export-mode').value;schedulePreview();});
  $('breakup-preview').addEventListener('change',()=>viewer.setOptions({breakupOn:$('breakup-preview').checked}));
  $('breakup-compare').addEventListener('click',breakupComparison);
  $('clean-base').addEventListener('click',()=>{
    state.breakup.mode='LAYERED';
    if(cleanRestore){Object.assign(state.breakup,cleanRestore);cleanRestore=null;}
    else{cleanRestore=Object.fromEntries(Object.keys(config.breakup_controls).map(k=>[k,state.breakup[k]]));for(const k of Object.keys(config.breakup_controls))state.breakup[k]=0;}
    syncControls();schedulePreview(0);
  });
  $('preset').addEventListener('change', () => {
    cleanRestore=null;
    const seed = state.seed, art=copy(state.art);
    state = copy(defaults($('preset').value)); state.seed = seed;state.art=art;
    syncControls(); schedulePreview(0);
  });
  $('surface-mode').addEventListener('change',()=>{
    cleanRestore=null;
    modeState.set(state.surface_mode,copy(state));const mode=$('surface-mode').value,seed=state.seed;
    state=copy(modeState.get(mode)||config.presets.find(p=>p.defaults.surface_mode===mode).defaults);state.seed=seed;
    preferredExportSize=[...config.export_resolutions_by_mode[mode][0]];
    syncControls();resetGeometry();schedulePreview(0);
  });
  $('tile-mode').addEventListener('change',()=>{state.tile_mode=$('tile-mode').value;schedulePreview();});
  $('art-profile').addEventListener('change',()=>{state.art=copy(config.art_default);state.art.profile=$('art-profile').value;syncControls();schedulePreview();});
  $('art-compare').addEventListener('click',artComparison);
  $('palette').addEventListener('change', () => { state.palette = $('palette').value; schedulePreview(); });
  $('seed').addEventListener('change', () => setSeed(Number($('seed').value)));
  $('seed').addEventListener('input', () => {
    if ($('seed').value !== '' && $('seed').validity.valid) setSeed(Number($('seed').value));
  });
  $('previous').addEventListener('click', () => setSeed((state.seed - 1 + 2147483648) % 2147483648));
  $('next').addEventListener('click', () => setSeed((state.seed + 1) % 2147483648));
  $('random-seed').addEventListener('click', () => setSeed(Math.floor(randomUnit() * 2147483648)));
  $('random-parameters').addEventListener('click', () => {
    const ranges = config.presets.find(p => p.name === state.preset).random_ranges;
    for (const [key, [low, high]] of Object.entries(ranges)) {
      const fields=state.surface_mode==='UNIQUE_FACADE'?config.parameters:state.surface_mode==='TILEABLE_SURFACE'?config.surface_parameters:config.cylinder_parameters;
      const step = fields[key][2];
      state.parameters[key] = Number((Math.round((low + (high-low) * randomUnit()) / step) * step).toFixed(4));
    }
    syncControls(); schedulePreview(0);
  });
  $('reset-all').addEventListener('click', () => {
    const seed = state.seed,art=copy(state.art); state = copy(defaults()); state.seed = seed;state.art=art;
    syncControls(); schedulePreview(0);
  });
  $('shape').addEventListener('change', () => viewer.setShape($('shape').value));
  document.querySelectorAll('[data-review]').forEach(button=>button.addEventListener('click',()=>{
    $('shape').value=button.dataset.review;viewer.setShape(button.dataset.review);
    const scale=button.dataset.review==='CYLINDER'?1:3;setUV(scale,scale);
  }));
  $('frame').addEventListener('click', () => viewer.frame());
  document.querySelectorAll('[data-map]').forEach(button => button.addEventListener('click', () => setMap(button.dataset.map)));
  document.querySelectorAll('[data-tile]').forEach(button => button.addEventListener('click', () => setUV(Number(button.dataset.tile), Number(button.dataset.tile))));
  for (const id of ['uv-x', 'uv-y']) $(id).addEventListener('change', () => setUV(Number($('uv-x').value), Number($('uv-y').value)));
  $('emission-toggle').addEventListener('change', () => viewer.setOptions({emissionOn: $('emission-toggle').checked}));
  $('capture').addEventListener('click', async () => {
    try {
      const recipe = active().recipe;
      download(await viewer.screenshot(), `${recipe.preset.toLowerCase()}_${recipe.seed}_3d_preview.png`);
      status('Downloaded the Three.js building preview PNG.');
    } catch (error) { status(error.message, true); }
  });
  $('pin').addEventListener('click', () => {
    const next = active();
    if (pinned && pinned !== current && pinned !== next) pinned.dispose();
    pinned = next; $('pin').textContent = 'A PINNED'; readyButtons();
    status('A pinned. New edits create B; SHOW A / SHOW B compares them.');
  });
  $('compare').addEventListener('click', () => {
    showA = !showA; describe(active()); readyButtons();
    status(showA ? 'Viewing pinned A. Favorite / export use the displayed A recipe.' : 'Viewing live B.');
  });
  $('favorite').addEventListener('click', async () => {
    if (savingFavorite) return;
    const source = active();
    const snapshot = copy({recipe: source.recipe, maps: source.maps, preview_maps: source.preview_maps, key: source.key});
    savingFavorite = true; readyButtons(); status('Rendering favorite thumbnail…');
    try {
      const thumbnail = await renderFavoriteThumbnail(snapshot);
      await api('favorites', {recipe: snapshot.recipe, thumbnail_data_url: thumbnail});
      await loadFavorites(); status('Recipe + material thumbnail saved in WebLab/favorites.');
    }
    catch (error) { status(error.message, true); }
    finally { savingFavorite = false; readyButtons(); }
  });
  $('load-recipe').addEventListener('click', () => $('recipe-file').click());
  $('recipe-file').addEventListener('change', async () => {
    try { const file = $('recipe-file').files[0]; if (file) await restoreRecipe(JSON.parse(await file.text())); }
    catch (error) { status(`Recipe not loaded: ${error.message}`, true); }
    finally { $('recipe-file').value = ''; }
  });
  $('export').addEventListener('click', () => {
    exportSnapshot = copy(active().recipe);
    $('export-name').value = `${exportSnapshot.preset.toLowerCase().replace('_tower', '')}_${exportSnapshot.seed}`;
    const sizes=config.export_resolutions_by_mode[exportSnapshot.surface_mode];
    $('export-resolution').replaceChildren(...sizes.map(size=>new Option(size.join(' × '),size.join(','))));
    if(!sizes.some(s=>s.join()===preferredExportSize.join()))preferredExportSize=[...sizes[0]];
    $('export-resolution').value = preferredExportSize.join(',');
    $('export-detail-mode').value=exportSnapshot.breakup.export_mode;
    $('export-detail-mode').disabled=exportSnapshot.breakup.mode==='LEGACY_BAKED';
    $('export-result').textContent = ''; $('export-result').className = '';
    $('confirm-export').disabled = false; $('confirm-export').textContent = 'EXPORT TO PROJECT ↗';
    $('download-recipe').hidden = true; lastExport = null;
    $('export-dialog').showModal(); $('export-name').select();
  });
  $('close-export').addEventListener('click', () => $('export-dialog').close());
  $('export-form').addEventListener('submit', async event => {
    event.preventDefault();
    if ($('confirm-export').disabled) return;
    const requestedName = $('export-name').value.trim();
    const resolution = $('export-resolution').value.split(',').map(Number);
    $('confirm-export').disabled = true; $('confirm-export').textContent = 'EXPORTING…';
    $('export-result').textContent = ''; $('export-result').className = '';
    try {
      const result = await api('export', {...exportSnapshot,breakup:{...exportSnapshot.breakup,export_mode:$('export-detail-mode').value}, name: requestedName, resolution, godot_material: $('export-material').checked});
      lastExport = result; preferredExportSize = resolution;
      $('export-result').textContent = `${result.revisioned ? `Name occupied → saved as ${result.name}.` : `Saved ${result.name}.`}\n${result.recipe.breakup.mode==='LAYERED'?'5 base + 3 detail maps':'5 maps'}${result.recipe.outputs.emission_mask?' + emission mask':''} + recipe${result.recipe.material ? ' + Godot material' : ''}${result.recipe.surface_mode!=='UNIQUE_FACADE'?' + 3 review PNGs':''} · ${resolution.join(' × ')} · ${Math.round(result.elapsed_ms)} ms`;
      $('download-recipe').hidden = false;
      $('confirm-export').textContent = 'EXPORTED ✓';
      status(`Exported ${result.name}. Existing assets preserved.`);
    } catch (error) {
      $('export-result').textContent = error.message; $('export-result').className = 'error';
      $('confirm-export').disabled = false; $('confirm-export').textContent = 'RETRY EXPORT ↗';
    }
  });
  $('download-recipe').addEventListener('click', () => {
    if (lastExport) download(new Blob([JSON.stringify(lastExport.recipe, null, 2)], {type: 'application/json'}), `${lastExport.name}.facade.json`);
  });
  $('viewport').addEventListener('viewer-error', e => status(e.detail, true));
}

async function start() {
  config = await api('config');
  for (const palette of config.palettes) $('palette').add(new Option(palette.label, palette.id));
  state = copy(config.presets.find(p => p.name === 'INDUSTRIAL_TOWER').defaults);
  state.seed = 99;
  viewer = new FacadeViewer($('viewport'));
  paletteControls=new PaletteControls(config,(group,role,value)=>{state.palette_mix[group][role]=value;syncControls();schedulePreview();});
  controls = new ParameterControls(config, (section, key, value) => {
    if(section==='meta'){state.art[key]=value;state.art.overrides={};}
    else if(section==='art'){state.art.overrides[key]=value;state.art.controls[key]=value;}
    else state[section][key] = value;
    if(section==='breakup')cleanRestore=null;
    if(key==='tile_scale')setUV(value*3,value*3);
    if (key === 'emission_strength') viewer.setOptions({emissionStrength: value});
    schedulePreview();
  });
  const requestedMode=new URLSearchParams(location.search).get('mode');
  if(requestedMode && config.preview_resolutions[requestedMode]){
    const requestedPreset=new URLSearchParams(location.search).get('preset');
    const pick=config.presets.find(p=>p.defaults.surface_mode===requestedMode && p.name===requestedPreset)||config.presets.find(p=>p.defaults.surface_mode===requestedMode);
    state=copy(pick.defaults);state.seed=99;
  }
  syncControls(); wireEvents(); await loadFavorites();
  mountMaterialLibrary(config,name=>{
    state=copy(defaults(name));cleanRestore=null;showA=false;
    preferredExportSize=[...config.export_resolutions_by_mode[state.surface_mode][0]];
    syncControls();resetGeometry();schedulePreview(0);
  });
  resetGeometry();
  $('export-destination').textContent = config.export_directory;
  const comparison=new URLSearchParams(location.search).get('compare');
  if(comparison==='breakup')await breakupComparison();
  else if(comparison==='palette'){
    for(const key of Object.keys(config.breakup_controls))state.breakup[key]=0;
    const result=await api('preview',state);current=await viewer.prepareMaps(result);currentRevision=revision;state=copy(result.recipe);syncControls();describe(current);readyButtons();$('loading').classList.add('hidden');
    await paletteComparison();
  }else schedulePreview(0);
}

start().catch(error => { status(error.message, true); $('loading').textContent = 'Could not start WebLab. Check the local server and WebGL.'; });
