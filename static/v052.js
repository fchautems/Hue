/* Hue Lab v0.5.2 — second profil : courbe simple, sans modifier la courbe personnalisée. */
"use strict";
(() => {
  const card = document.querySelector('.profile-card');
  const container = document.querySelector('#v052-simple-editor');
  const lampSelect = document.querySelector('#profile-light');
  const customRoot = document.querySelector('#point-rows');
  if (!card || !container || !lampSelect || !customRoot) return;

  const DEFAULT = {wake:375, morning_end:780, evening_start:1080, bed:1380,
                   min_brightness:10, max_brightness:85};
  const keys = Object.keys(DEFAULT);
  const clockKeys = ['wake','morning_end','evening_start','bed'];
  const buttons = [...document.querySelectorAll('.v052-mode')];
  const fields = Object.fromEntries(keys.map(key => [key, document.querySelector(`#v052-${key}`)]));
  const target = document.querySelector('#profile-target');
  const typeStatus = document.querySelector('#v052-type-status');
  const formError = document.querySelector('#v052-error');
  const save = document.querySelector('#v052-save');
  const cancel = document.querySelector('#v052-cancel');
  const activateCustom = document.querySelector('#v052-activate-custom');
  const originalLoad = loadProfile;
  const originalRender = renderChart;
  const originalTick = tickClock;
  let activeType = 'custom';
  let viewType = 'custom';
  let params = {...DEFAULT};
  let saved = {...DEFAULT};
  let loading = false;
  let saving = false;
  let chosenLamp = null;
  let simpleDirty = false;

  const fmt = n => `${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`;
  const parseTime = value => {
    const match = /^(\d{2}):(\d{2})$/.exec(value);
    if (!match) return NaN;
    const h = Number(match[1]), m = Number(match[2]);
    return h < 24 && m < 60 ? h*60 + m : NaN;
  };
  const ease = raw => {const t = Math.max(0,Math.min(1,raw));return t*t*t*(t*(6*t-15)+10)};
  function validate(p) {
    if (keys.some(k => !Number.isInteger(p[k]))) return 'Renseigne toutes les valeurs.';
    if (!(0 <= p.wake && p.wake < p.morning_end && p.morning_end <= p.evening_start &&
          p.evening_start < p.bed && p.bed < 1440))
      return 'Les horaires doivent suivre : lever, fin de montée, début de descente, coucher.';
    if (p.morning_end-p.wake < 30 || p.bed-p.evening_start < 30)
      return 'Prévois au moins 30 minutes pour monter et pour descendre.';
    if (!(1 <= p.min_brightness && p.min_brightness < p.max_brightness && p.max_brightness <= 100))
      return 'Le minimum doit être inférieur au maximum, entre 1 et 100 %.';
    return '';
  }
  function level(p, minute) {
    const m = ((minute%1440)+1440)%1440;
    const lo=p.min_brightness, hi=p.max_brightness;
    if(m<=p.wake || m>=p.bed)return lo;
    if(m<p.morning_end)return lo+(hi-lo)*ease((m-p.wake)/(p.morning_end-p.wake));
    if(m<=p.evening_start)return hi;
    return hi-(hi-lo)*ease((m-p.evening_start)/(p.bed-p.evening_start));
  }
  function draw() {
    const svg = document.querySelector('#v052-chart');
    if (!svg) return;
    const left=35, right=820, top=14, bottom=222;
    const x=m=>left+m/1440*(right-left);
    const y=v=>bottom-v/100*(bottom-top);
    const error=validate(params);
    const grid = [0,25,50,75,100].map(v=>`<line x1="${left}" x2="${right}" y1="${y(v)}" y2="${y(v)}" stroke="#384d60" stroke-dasharray="3 6"/><text x="5" y="${y(v)+4}" fill="#a8bac9" font-size="12">${v}</text>`).join('')+
      [0,360,720,1080,1440].map(m=>`<line x1="${x(m)}" x2="${x(m)}" y1="${top}" y2="${bottom}" stroke="#384d60" opacity=".55"/>`).join('');
    let path='';
    if(!error) for(let m=0;m<=1440;m+=5)path+=`${m?'L':'M'}${x(m).toFixed(2)},${y(level(params,m)).toFixed(2)} `;
    const fill=error?'':`<path d="${path}L${right},${bottom} L${left},${bottom}Z" fill="url(#v052-area)"/>`;
    svg.innerHTML=`<defs><linearGradient id="v052-area" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#85d5c0" stop-opacity=".25"/><stop offset="100%" stop-color="#85d5c0" stop-opacity="0"/></linearGradient></defs>${grid}${fill}<path d="${path}" fill="none" stroke="#85d5c0" stroke-width="3.5" vector-effect="non-scaling-stroke"/>`;
    formError.textContent=error;
    formError.hidden=!error;
    target.textContent=error?'Cible — %':`Cible ${Math.round(level(params,currentMinute()))} %`;
    updateUI(error);
  }
  function updateUI(error='') {
    simpleDirty = viewType !== activeType || keys.some(k=>params[k]!==saved[k]);
    buttons.forEach(b=>{const chosen=b.dataset.type===viewType;b.classList.toggle('active',chosen);b.setAttribute('aria-pressed',String(chosen));});
    card.dataset.v052View = viewType;
    container.hidden=viewType!=='simple';
    activateCustom.hidden=viewType!=='custom' || activeType==='custom';
    typeStatus.textContent = loading?'Chargement…':
      simpleDirty?'● Modifications non enregistrées — les lampes ne changent pas avant validation':
      (activeType==='simple'?'✓ Profil simple actif':'✓ Profil personnalisé actif');
    typeStatus.classList.toggle('unsaved',simpleDirty);
    save.disabled=saving||loading||!selectedId||viewType!=='simple'||!simpleDirty||!!error;
    cancel.disabled=saving||loading||!simpleDirty;
    activateCustom.disabled=saving||loading||profileDirty;
    for(const field of Object.values(fields)) field.disabled=saving||loading;
  }
  function fillFields() {
    for(const key of keys){
      fields[key].value=clockKeys.includes(key)?fmt(params[key]):String(params[key]);
    }
    for(const key of ['min_brightness','max_brightness'])
      document.querySelector(`#v052-${key}-value`).textContent=`${params[key]} %`;
  }
  async function fetchProfile() {
    const id=selectedId;
    if(!id)return;
    chosenLamp=id;loading=true;updateUI();
    try {
      const data=await api(`/api/profile/simple/${encodeURIComponent(id)}`);
      if(selectedId!==id)return;
      activeType=data.type;
      viewType=data.type;
      saved={...data.params};params={...saved};
      fillFields();draw();
    } catch(error) {
      if(selectedId===id)showToast(`Profil simple : ${error.message}`,true);
    } finally {
      if(selectedId===id){loading=false;updateUI(validate(params));}
    }
  }
  loadProfile = async function() {
    await originalLoad();
    await fetchProfile();
  };
  // v0.5.1 garde le graphique de la courbe personnalisée ; masquer seulement sa présentation.
  renderChart = function() {
    originalRender();
    if(viewType==='simple' && !validate(params))target.textContent=`Cible ${Math.round(level(params,currentMinute()))} %`;
  };
  tickClock = function() {
    originalTick();
    if(viewType==='simple' && !validate(params))target.textContent=`Cible ${Math.round(level(params,currentMinute()))} %`;
  };

  for(const [key,field] of Object.entries(fields)) {
    field.addEventListener(clockKeys.includes(key)?'change':'input',()=>{
      const value=clockKeys.includes(key)?parseTime(field.value):Number(field.value);
      params[key]=value;
      if(!clockKeys.includes(key))document.querySelector(`#v052-${key}-value`).textContent=`${value} %`;
      draw();
    });
  }
  buttons.forEach(btn=>btn.addEventListener('click',()=>{
    if(loading||saving||viewType===btn.dataset.type)return;
    if(profileDirty || simpleDirty){
      showToast('Enregistre ou annule les modifications avant de changer de type de courbe.',true);return;
    }
    viewType=btn.dataset.type;
    if(viewType==='simple')draw();else updateUI();
  }));
  cancel.onclick=()=>{
    if(saving)return;
    params={...saved};viewType=activeType;fillFields();draw();
    showToast('Modifications annulées.');
  };
  save.onclick=()=>safe(async()=>{
    if(saving||loading||viewType!=='simple'||!selectedId)return;
    const error=validate(params);if(error){draw();throw Error(error)}
    const id=selectedId; saving=true;updateUI();
    try{
      await api(`/api/profile/simple/${encodeURIComponent(id)}`,'PUT',{params});
      if(selectedId!==id)return;
      saved={...params};activeType='simple';viewType='simple';
      showToast('Courbe simple enregistrée et activée.');
      draw();await refresh();
      window.HueRGB?.reloadIfClean(id);
    } finally {saving=false;updateUI(validate(params));}
  });
  activateCustom.onclick=()=>safe(async()=>{
    if(saving||loading||viewType!=='custom'||profileDirty||!selectedId)return;
    const id=selectedId;saving=true;updateUI();
    try{
      await api(`/api/profile/type/${encodeURIComponent(id)}`,'POST',{type:'custom'});
      if(selectedId===id){activeType='custom';viewType='custom';showToast('Courbe personnalisée réactivée.');await refresh();window.HueRGB?.reloadIfClean(id);}
    } finally {saving=false;updateUI();}
  });
  const previousLampChange=lampSelect.onchange;
  lampSelect.onchange=e=>{
    if(simpleDirty && !window.confirm('Modifications de la courbe simple non enregistrées. Les abandonner ?')){
      e.target.value=selectedId;return;
    }
    simpleDirty=false;
    previousLampChange?.call(lampSelect,e);
  };
  document.querySelector('.nav')?.addEventListener('click',e=>{
    const btn=e.target.closest?.('.nav-item');
    if(!btn || btn.dataset.tab==='profiles' || activeTab!=='profiles' || !simpleDirty)return;
    if(!window.confirm('Modifications de la courbe simple non enregistrées. Les abandonner ?')){
      e.preventDefault();e.stopImmediatePropagation();return;
    }
    simpleDirty=false;
  },true);
  window.addEventListener('beforeunload',e=>{if(simpleDirty){e.preventDefault();e.returnValue='';}});
  window.HueProfiles={
    hasUnsaved:()=>simpleDirty||profileDirty,
    reload:()=>loadProfile()
  };
  fillFields();updateUI();
})();
