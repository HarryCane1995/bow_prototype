// Read-only production catalog; selecting an entry uses the regular editor,
// seed, A/B, favorites and export flow rather than introducing another schema.
export function mountMaterialLibrary(config, onSelect) {
  const host=document.createElement('details');host.id='material-library';
  host.innerHTML='<summary>INDUSTRIAL LIBRARY · 50 RECIPES</summary><label for="material-category">Material family</label><select id="material-category"><option value="all">All 50 materials</option><option value="wall">Wall / panel · 12</option><option value="floor">Floor / walkway · 12</option><option value="ceiling">Ceiling · 6</option><option value="wrap">Cylinder wrap · 10</option><option value="accent">Specialized / accent · 10</option></select><div class="material-library-grid"></div><p class="note">Choose a recipe, edit its seed / structure / finish, then export. Thumbnails are the authored production baseline.</p>';
  document.querySelector('.controls-panel .panel-title').after(host);
  const grid=host.querySelector('.material-library-grid');
  const render=()=>{
    const category=host.querySelector('select').value;grid.replaceChildren();
    for(const item of config.material_library.filter(r=>category==='all'||r.category===category)){
      const button=document.createElement('button');button.type='button';button.className='material-library-card';
      button.title=item.description;const img=new Image();img.src=item.thumbnail;img.loading='lazy';img.alt=item.description;
      const label=document.createElement('span');label.textContent=item.name.replace(/^(WALL|FLOOR|CEILING|WRAP|ACCENT)_/,'').replaceAll('_',' ');
      button.append(img,label);button.addEventListener('click',()=>{onSelect(item.name);host.open=false;});grid.append(button);
    }
  };
  host.querySelector('select').addEventListener('change',render);render();
}
