export class PaletteControls {
  constructor(config, onChange) {
    this.config=config;this.change=onChange;
    const dropdown=document.querySelector('#palette-preset');
    for(const name of Object.keys(config.palette_presets))dropdown.add(new Option(name.replaceAll('_',' '),name));
    const labels=['Base','Secondary','Dark','Accent','Glass','Emission 1','Emission 2','Grime'];
    config.palette_roles.forEach((role,i)=>{
      const row=document.createElement('div');row.className='palette-swatch';
      row.innerHTML=`<label for="color-${role}">${labels[i]}</label><input id="color-${role}" type="color" aria-label="${labels[i]} color picker"><input id="hex-${role}" class="hex-color" aria-label="${labels[i]} hex color" pattern="#[0-9a-fA-F]{6}" maxlength="7"><label class="swatch-lock" title="Lock ${labels[i]}"><input id="lock-${role}" type="checkbox" aria-label="Lock ${labels[i]}"><span>LOCK</span></label>`;
      document.querySelector('#palette-swatches').append(row);
      row.querySelector('[type=color]').addEventListener('input',e=>onChange('colors',role,e.target.value));
      row.querySelector('.hex-color').addEventListener('input',e=>{if(/^#[0-9a-f]{6}$/i.test(e.target.value))onChange('colors',role,e.target.value.toLowerCase());});
      row.querySelector('[type=checkbox]').addEventListener('change',e=>onChange('locks',role,e.target.checked));
    });
  }
  restore(palette) {
    document.querySelector('#palette-preset').value=palette.preset;
    document.querySelector('#palette-enabled').checked=palette.enabled;
    document.querySelector('#palette-fields').hidden=!palette.enabled;
    for(const role of this.config.palette_roles){
      document.querySelector('#color-'+role).value=palette.colors[role];
      document.querySelector('#hex-'+role).value=palette.colors[role];
      document.querySelector('#lock-'+role).checked=palette.locks[role];
    }
    const changed=JSON.stringify(palette.colors)!==JSON.stringify(this.config.palette_presets[palette.preset].colors);
    document.querySelector('#palette-note').textContent=(changed?'Custom colors · ':'')+'Semantic colors only. Normal / height stay fixed. Locked swatches survive randomization.';
  }
}
