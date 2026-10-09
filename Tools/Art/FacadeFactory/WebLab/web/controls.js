export class ParameterControls {
  constructor(config, onChange) {
    this.rows = new Map();
    this.onChange = onChange;
    for (const [key, schema] of Object.entries(config.parameters)) {
      this.add(key, schema, 'parameters', document.querySelector(`#${schema[4]}-controls`));
    }
    for (const fields of [config.surface_parameters,config.cylinder_parameters]) {
      for (const [key,schema] of Object.entries(fields)) this.add(key,schema,'parameters',document.querySelector(`#${schema[4]}-controls`));
    }
    for (const [key,schema] of Object.entries(config.art_controls)) this.add(key,schema,'art',document.querySelector('#art-controls'));
    for (const [key,schema] of Object.entries(config.breakup_controls)) this.add(key,schema,'breakup',document.querySelector('#breakup-controls'));
    for (const [key,schema] of Object.entries(config.palette_influences)) this.add(key,schema,'palette_mix',document.querySelector('#palette-influences'));
    this.add('material_mix',[0,1,.01,'Illustration ↔ Material'],'meta',document.querySelector('#meta-controls'));
    this.add('weathering',[0,1,.01,'Clean ↔ Weathered'],'meta',document.querySelector('#meta-controls'));
    for (const [key, schema] of Object.entries(config.style)) {
      this.add(key, schema, 'style', document.querySelector('#style-controls'));
    }
  }

  add(key, [min, max, step, label], section, parent) {
    const row = document.createElement('div');
    row.className = 'slider-row';
    const id = `${section}-${key}`;
    row.innerHTML = `<div class="slider-top"><label for="${id}">${label}</label><input class="slider-value" aria-label="${label} numeric value" type="number" min="${min}" max="${max}" step="${step}"><button type="button" class="reset-knob" title="Reset ${label} to preset default" aria-label="Reset ${label}">↺</button></div><input id="${id}" type="range" min="${min}" max="${max}" step="${step}" aria-label="${label}">`;
    parent.append(row);
    const range = row.querySelector('[type=range]');
    const number = row.querySelector('[type=number]');
    const precision = step < 1 ? 2 : 0;
    const data = {range, number, min, max, step, defaultValue: 0};
    data.update = (value, formatNumber = true) => {
      range.value = value;
      if (formatNumber) number.value = Number(value).toFixed(precision);
      range.style.setProperty('--progress', `${(value - min) / (max - min) * 100}%`);
    };
    const emit = (value, formatNumber = true) => {
      value = Math.max(min, Math.min(max, Number(value)));
      value = Math.round(value / step) * step;
      value = Number(value.toFixed(4));
      data.update(value, formatNumber);
      this.onChange(section, key, value);
    };
    range.addEventListener('input', () => emit(range.value));
    number.addEventListener('input', () => {
      if (number.value !== '' && number.validity.valid) emit(number.value, false);
    });
    number.addEventListener('change', () => {
      if (number.value === '' || !Number.isFinite(Number(number.value))) data.update(Number(range.value));
      else if (Number(number.value) !== Number(range.value)) emit(number.value);
    });
    row.querySelector('button').addEventListener('click', () => emit(data.defaultValue));
    range.addEventListener('dblclick', () => emit(data.defaultValue));
    this.rows.set(`${section}.${key}`, data);
  }

  restore(recipe, defaults) {
    for (const [path, data] of this.rows) {
      const [section, key] = path.split('.');
      const values=section==='art' ? recipe.art.controls : section==='meta' ? recipe.art : recipe[section];
      const base=section==='art' ? defaults.art.controls : section==='meta' ? defaults.art : defaults[section];
      if (!values || values[key]===undefined) continue;
      data.defaultValue = base?.[key] ?? values[key];
      data.update(values[key]);
    }
  }
}
