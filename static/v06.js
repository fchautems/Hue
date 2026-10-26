/* Hue Lab v0.6 — editor RGB mobile, enregistrement explicite. */
"use strict";
(() => {
  const root = document.querySelector('#tab-colors');
  if (!root) return;
  const $ = selector => root.querySelector(selector);
  const $$ = selector => [...root.querySelectorAll(selector)];
  const phaseKeys = ['morning','day','evening','night'];
  const timeKeys = ['wake','morning_end','evening_start','bed'];
  const rgbSelect = $('#rgb-light');
  const saveButton = $('#rgb-save');
  const revertButton = $('#rgb-revert');
  let uid = null, saved = null, draft = null, capable = false, loading = false, saving = false, selectedPhase = 'evening';
  let nonce = 0;
  const clone = value => JSON.parse(JSON.stringify(value));
  const fmt = m => `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
  const parseClock = txt => { const match=/^(\d{2}):(\d{2})$/.exec(txt);if(!match)return NaN;const h=Number(match[1]),m=Number(match[2]);return h<24&&m<60?h*60+m:NaN; };
  const ease = x => {const t=Math.max(0,Math.min(1,x));return t*t*t*(t*(6*t-15)+10)};
  const wrap = h => ((h%360)+360)%360;
  function mix(a,b,t) {
    const k=ease(t),delta=((b.h-a.h+180)%360+360)%360-180;
    return {h:wrap(a.h+delta*k),s:a.s+(b.s-a.s)*k};
  }
  function colourAt(m) {
    const p=draft.simple_params,c=draft.colors;
    const {wake,morning_end,evening_start,bed}=p;
    const mmid=(wake+morning_end)/2,emid=(evening_start+bed)/2;
    if(m<=wake||m>=bed)return c.night;
    if(m<mmid)return mix(c.night,c.morning,(m-wake)/(mmid-wake));
    if(m<morning_end)return mix(c.morning,c.day,(m-mmid)/(morning_end-mmid));
    if(m<=evening_start)return c.day;
    if(m<emid)return mix(c.day,c.evening,(m-evening_start)/(emid-evening_start));
    return mix(c.evening,c.night,(m-emid)/(bed-emid));
  }
  function brightnessAt(m) {
    const p=draft.simple_params,low=p.min_brightness,high=p.max_brightness;
    if(m<=p.wake||m>=p.bed)return low;
    if(m<p.morning_end)return low+(high-low)*ease((m-p.wake)/(p.morning_end-p.wake));
    if(m<=p.evening_start)return high;
    return high-(high-low)*ease((m-p.evening_start)/(p.bed-p.evening_start));
  }
  function rgb(h,s,l) {
    h=wrap(h)/360;s=s/100;l=l/100;
    if(!s){const v=Math.round(l*255);return [v,v,v]}
    const q=l<.5?l*(1+s):l+s-l*s,p=2*l-q;
    const f=t=>{if(t<0)t+=1;if(t>1)t-=1;if(t<1/6)return p+(q-p)*6*t;if(t<.5)return q;if(t<2/3)return p+(q-p)*(2/3-t)*6;return p};
    return [f(h+1/3),f(h),f(h-1/3)].map(v=>Math.round(v*255));
  }
  function hex(h,s,l=55){return '#'+rgb(h,s,l).map(x=>x.toString(16).padStart(2,'0')).join('').toUpperCase()}
  const selected = () => draft.mode==='manuel' ? draft.manual : draft.colors[selectedPhase];
  function hasChanges() {return !!saved&&!!draft&&(JSON.stringify(draft)!==JSON.stringify(saved.data)||(!saved.enabled&&draft.mode==='auto'));}
  function errorMessage(){
    if(!draft)return 'Aucune lampe sélectionnée.';
    const p=draft.simple_params;
    if(timeKeys.some(k=>!Number.isInteger(p[k])))return 'Heure invalide : utilise HH:MM.';
    if(!(0<=p.wake&&p.wake<p.morning_end&&p.morning_end<=p.evening_start&&p.evening_start<p.bed&&p.bed<1440))return 'Les quatre horaires doivent être dans le bon ordre.';
    if(p.morning_end-p.wake<30||p.bed-p.evening_start<30)return 'Prévois au moins 30 minutes pour chaque transition.';
    if(!Number.isInteger(p.min_brightness)||!Number.isInteger(p.max_brightness)||!(1<=p.min_brightness&&p.min_brightness<p.max_brightness&&p.max_brightness<=100))return 'Le minimum doit être inférieur au maximum (1 à 100 %).';
    return '';
  }
  function setFeedback(message,failed=false){$('#rgb-feedback').textContent=message;$('#rgb-feedback').classList.toggle('error',failed)}
  function drawCurve(){
    const p=draft.simple_params;
    if(errorMessage())return;
    let line=''; const y=n=>103-n*.88;
    for(let m=0;m<=1440;m+=5){line+=`${m?'L':'M'}${(m/1440*600).toFixed(2)},${y(brightnessAt(m)).toFixed(2)} `;}
    $('#rgb-curve-line').setAttribute('d',line);
    $('#rgb-curve-area').setAttribute('d',line+'L600,105 L0,105Z');
    const markers=$('#rgb-time-markers');markers.replaceChildren();
    const ns='http://www.w3.org/2000/svg';
    for(const key of timeKeys){
      const mark=document.createElementNS(ns,'line'),pos=p[key]/1440*600;
      for(const [k,v] of Object.entries({x1:pos,x2:pos,y1:10,y2:103,stroke:'#96b5c6','stroke-opacity':'0.46','stroke-dasharray':'3 5'}))mark.setAttribute(k,v);
      markers.appendChild(mark);
    }
    const stops=[];
    for(let m=0;m<=1440;m+=30){const c=colourAt(m);stops.push(`${hex(c.h,c.s)} ${(m/1440*100).toFixed(2)}%`);}
    $('#rgb-color-gradient').style.background=`linear-gradient(90deg,${stops.join(',')})`;
    $('#rgb-hours-summary').textContent=timeKeys.map(k=>fmt(p[k])).join(' → ');
  }
  function render(){
    if(!draft){saveButton.disabled=true;revertButton.disabled=true;return;}
    const p=selected(); const angle=wrap(p.h)*Math.PI/180,r=p.s*.42;
    $('#rgb-wheel-cursor').style.left=`${50+Math.sin(angle)*r}%`;
    $('#rgb-wheel-cursor').style.top=`${50-Math.cos(angle)*r}%`;
    $('#rgb-wheel-cursor').style.setProperty('--cursor',hex(p.h,p.s));
    $('#rgb-wheel').setAttribute('aria-valuenow',String(Math.round(p.h)));
    const level=draft.mode==='manuel'?draft.manual.b:draft.simple_params.max_brightness;
    $('#rgb-preview').style.setProperty('--preview',hex(p.h,p.s,18+level*.49));
    $('#rgb-hex').textContent=hex(p.h,p.s);
    $('#rgb-sat').value=String(p.s);$('#rgb-sat-value').textContent=`${p.s} %`;
    $('#rgb-bright').value=String(level);$('#rgb-bright-value').textContent=`${level} %`;
    $('#rgb-bright-label').textContent=draft.mode==='manuel'?'Luminosité manuelle':'Luminosité maximale';
    $$('.rgb-seg button').forEach(button=>{const active=button.dataset.mode===draft.mode;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    $$('.rgb-phase').forEach(button=>{const key=button.dataset.phase;button.classList.toggle('active',key===selectedPhase);button.setAttribute('aria-pressed',String(key===selectedPhase));button.style.setProperty('--dot',hex(draft.colors[key].h,draft.colors[key].s));});
    $('#rgb-auto-phases').hidden=draft.mode==='manuel';
    $('#rgb-auto-settings').hidden=draft.mode==='manuel';
    $('#rgb-mode-advisory').textContent=draft.mode==='auto'
      ? 'Enregistrer active la courbe Simple et les couleurs automatiques ; l’ancienne courbe personnalisée reste conservée.'
      : 'Enregistrer applique la couleur seulement si la lampe est déjà allumée ; sinon elle sera mémorisée pour le prochain allumage via Hue Lab.';
    const e=errorMessage();const err=$('#rgb-validation');err.textContent=e;err.hidden=!e;
    $('#rgb-min-value').textContent=`${draft.simple_params.min_brightness} %`;
    $('#rgb-max-value').textContent=`${draft.simple_params.max_brightness} %`;
    for(const key of timeKeys){const input=$(`#rgb-${key}`);if(document.activeElement!==input&&Number.isInteger(draft.simple_params[key]))input.value=fmt(draft.simple_params[key]);}
    $('#rgb-min').value=String(draft.simple_params.min_brightness);
    $('#rgb-max').value=String(draft.simple_params.max_brightness);
    const dirty=hasChanges();const canAct=dirty&&!e&&!loading&&!saving&&capable&&!!uid;
    saveButton.disabled=!canAct;revertButton.disabled=!dirty||saving;
    saveButton.textContent=draft.mode==='auto'?'Enregistrer et activer Auto':'Appliquer et enregistrer';
    $('#rgb-status').textContent=loading?'Chargement…':!capable?'RGB indisponible':dirty?'● Modifications non enregistrées':'✓ Configuration enregistrée';
    $('#rgb-status').classList.toggle('unsaved',dirty);
    $('#rgb-auto-settings').classList.toggle('rgb-invalid',!!e);
    $$('#rgb-presets button').forEach(button=>button.classList.toggle('active',Number(button.dataset.h)===Math.round(p.h)&&Number(button.dataset.s)===p.s));
    if(!e)drawCurve();
  }
  function touchColour(e){
    if(!draft||!capable)return;
    const rect=$('#rgb-wheel').getBoundingClientRect();
    const dx=(e.clientX-rect.left-rect.width/2)/(rect.width/2),dy=(e.clientY-rect.top-rect.height/2)/(rect.height/2);
    const p=selected();p.h=Math.round(wrap(Math.atan2(dx,-dy)*180/Math.PI))%360;p.s=Math.min(100,Math.round(Math.hypot(dx,dy)*100));
    setFeedback('Modifications en attente d’enregistrement.');render();
  }
  const wheel=$('#rgb-wheel');
  wheel.addEventListener('pointerdown',e=>{if(!draft||!capable)return;e.preventDefault();wheel.setPointerCapture(e.pointerId);touchColour(e)});
  wheel.addEventListener('pointermove',e=>{if(draft&&capable&&wheel.hasPointerCapture(e.pointerId))touchColour(e)});
  wheel.addEventListener('keydown',e=>{if(!draft||!capable)return;if(['ArrowRight','ArrowUp','ArrowLeft','ArrowDown'].includes(e.key)){e.preventDefault();selected().h=wrap(selected().h+(e.key==='ArrowRight'||e.key==='ArrowUp'?5:-5));render();}});
  $$('.rgb-phase').forEach(button=>button.addEventListener('click',()=>{if(!draft)return;selectedPhase=button.dataset.phase;render()}));
  $$('.rgb-seg button').forEach(button=>button.addEventListener('click',()=>{if(!draft)return;draft.mode=button.dataset.mode;render()}));
  $$('#rgb-presets button').forEach(button=>button.addEventListener('click',()=>{if(!draft)return;selected().h=Number(button.dataset.h);selected().s=Number(button.dataset.s);render()}));
  $('#rgb-sat').addEventListener('input',e=>{if(!draft)return;selected().s=Number(e.target.value);render()});
  $('#rgb-bright').addEventListener('input',e=>{if(!draft)return;if(draft.mode==='manuel')draft.manual.b=Number(e.target.value);else draft.simple_params.max_brightness=Number(e.target.value);render()});
  $('#rgb-min').addEventListener('input',e=>{if(!draft)return;draft.simple_params.min_brightness=Number(e.target.value);render()});
  $('#rgb-max').addEventListener('input',e=>{if(!draft)return;draft.simple_params.max_brightness=Number(e.target.value);render()});
  for(const key of timeKeys){$(`#rgb-${key}`).addEventListener('change',e=>{if(!draft)return;const value=parseClock(e.target.value);if(Number.isNaN(value)){setFeedback('Heure invalide.',true);e.target.value=fmt(draft.simple_params[key]);return;}draft.simple_params[key]=value;render()});}
  $('#rgb-schedule-toggle').addEventListener('click',()=>{const button=$('#rgb-schedule-toggle');const show=button.getAttribute('aria-expanded')!=='true';button.setAttribute('aria-expanded',String(show));$('#rgb-schedule-chevron').textContent=show?'⌃':'⌄';$('#rgb-schedule-content').hidden=!show;});
  function listLights(){
    const lights=state?.lights||[];
    const existing=rgbSelect.value;
    rgbSelect.innerHTML=lights.filter(l=>l.capabilities?.color).map(l=>`<option value="${escapeHtml(l.id)}">${escapeHtml(l.name)}</option>`).join('');
    if(lights.some(l=>l.id===existing&&l.capabilities?.color))rgbSelect.value=existing;
    return lights.filter(l=>l.capabilities?.color);
  }
  function discardPrompt(){return !hasChanges()||window.confirm('Tu as des réglages RGB non enregistrés. Les abandonner ?');}
  async function loadLamp(id){
    const token=++nonce;uid=id;loading=true;saved=null;draft=null;capable=false;render();
    if(!id){$('#rgb-status').textContent='Aucune ampoule RGB détectée';loading=false;return;}
    try{
      const res=await api(`/api/rgb/${encodeURIComponent(id)}`);
      if(token!==nonce)return;
      capable=!!res.capable;
      const data={mode:res.mode,colors:clone(res.colors),simple_params:clone(res.simple_params),manual:clone(res.manual)};
      saved={data:clone(data),enabled:res.enabled};draft=data;
      setFeedback(!capable?'Le pont n’annonce pas la couleur RGB pour cette lampe.':'Sélectionne une couleur, puis enregistre pour l’appliquer.');
    }catch(e){if(token===nonce){$('#rgb-status').textContent='Chargement impossible';setFeedback(e.message,true)}}
    finally{if(token===nonce){loading=false;render();}}
  }
  function open(id){
    const list=listLights();const chosen=id&&list.some(l=>l.id===id)?id:list[0]?.id;
    if(!chosen){uid=null;$('#rgb-status').textContent='Aucune lampe RGB';setFeedback('Reconnecte le pont Hue pour détecter les lampes RGB.',true);return;}
    if(uid===chosen&&draft)return;
    if(!discardPrompt())return;
    rgbSelect.value=chosen;loadLamp(chosen);
  }
  rgbSelect.addEventListener('change',()=>{
    if(!discardPrompt()){rgbSelect.value=uid||'';return;}
    loadLamp(rgbSelect.value);
  });
  saveButton.addEventListener('click',()=>safe(async()=>{
    if(!hasChanges()||!draft||!uid||saving||loading||!capable)return;
    const e=errorMessage();if(e){setFeedback(e,true);return}
    saving=true;render();const id=uid;
    try{
      const result=await api(`/api/rgb/${encodeURIComponent(id)}`,'PUT',clone(draft));
      if(uid!==id)return;
      const next={mode:result.mode,colors:clone(result.colors),simple_params:clone(result.simple_params),manual:clone(result.manual)};
      saved={data:clone(next),enabled:result.enabled};draft=clone(next);
      setFeedback(result.mode==='auto'?'Profil Simple et couleurs automatiques activés.':'Couleur manuelle enregistrée.'+(!result.on?' Lampe éteinte : pas d’allumage automatique.':''));
      await refresh();
    }catch(error){setFeedback(error.message,true);showToast(error.message,true)}
    finally{saving=false;render()}
  }));
  revertButton.addEventListener('click',()=>{if(!saved||saving)return;draft=clone(saved.data);setFeedback('Modifications annulées.');render()});
  document.querySelector('.nav')?.addEventListener('click',e=>{
    const tab=e.target.closest?.('.nav-item')?.dataset.tab;
    if(!tab)return;
    if(activeTab==='colors'&&tab!=='colors'&&!discardPrompt()){e.preventDefault();e.stopImmediatePropagation();return;}
    if(tab==='colors')queueMicrotask(()=>open(uid));
  },true);
  window.addEventListener('beforeunload',e=>{if(activeTab==='colors'&&hasChanges()){e.preventDefault();e.returnValue=''}});
  window.HueRGB={open};
})();
