"use strict";
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let state = null;
let selectedId = null;
let editingPoints = [];
let cardIds = null;
let lastStateAt = performance.now();
let activeTab = "rooms";
let powerupId = null;
let toastTimeout;
let seekDragging = false;
let simulationBusy = false;
let stateGeneration = 0;
let refreshBusy = false;
let profileDirty = false;
let setupInProgress = false;
let setupFirstShown = false;
let setupCancelled = false;
let setupInitDone = false;
let updaterWasBusy = false;
let setupIpEdited = false;
const pendingPower = new Map();
const lampControls = new WeakMap();
const DIM_INTERVAL_MS = 150;
const DIM_CONFIRM_MS = 3000;
const POWER_CONFIRM_MS = 12000;

function escapeHtml(text) { return String(text ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function mm(minute) { const m = ((Math.floor(minute) % 1440) + 1440) % 1440; return `${String(Math.floor(m/60)).padStart(2,"0")}:${String(m%60).padStart(2,"0")}`; }
function showToast(message, error=false) { const t = $("#toast"); t.textContent=message; t.className=`toast visible${error?' error':''}`; clearTimeout(toastTimeout); toastTimeout=setTimeout(()=>t.classList.remove("visible"),4000); }
async function api(url, method="GET", data=undefined, extraHeaders={}) {
  const r = await fetch(url, {method, headers:{...(data===undefined?{}:{"Content-Type":"application/json"}),...extraHeaders}, body:data===undefined?undefined:JSON.stringify(data), cache:"no-store"});
  const result=await r.json().catch(()=>({error:`Réponse HTTP ${r.status} non JSON`}));
  if (!r.ok || result.ok===false) throw new Error(result.error || `HTTP ${r.status}`);
  return result.data ?? result;
}
async function safe(fn) { try {await fn();} catch(e) {showToast(e.message,true);} }
function renderPower() {
  if(activeTab==='rooms')window.HueRooms?.render(state);
}
function confirmPower(snapshot) {
  if(state?.bridge_ip!==snapshot.bridge_ip){
    pendingPower.clear();
    return;
  }
  if(!snapshot.connected)return;
  for(const light of snapshot.lights){
    const command=pendingPower.get(light.id);
    if(command?.accepted && light.status!=='disconnected' && light.on===command.on)pendingPower.delete(light.id);
  }
}
async function changePower(ids, on) {
  if(!state?.connected || !ids.length || ids.some(id=>pendingPower.has(id)))return;
  const bridge=state.bridge_ip;
  const commands=ids.map(id=>{
    const command={on,accepted:false};
    pendingPower.set(id,command);
    setTimeout(()=>{
      if(pendingPower.get(id)!==command)return;
      pendingPower.delete(id);
      renderPower();
      showToast('État de la lampe non confirmé par le pont.',true);
    },POWER_CONFIRM_MS);
    return [id,command];
  });
  renderPower();
  let accepted, errors;
  try {
    if (ids.length === 1) {
      await api(`/api/light/${encodeURIComponent(ids[0])}/switch`,"POST",{on});
      accepted = ids;
      errors = {};
    } else {
      ({accepted, errors} = await api("/api/lights/switch", "POST", {on, light_ids: ids}));
    }
  } catch (error) {
    accepted = [];
    errors = Object.fromEntries(ids.map(id => [id, error.message]));
  }
  if (state.bridge_ip !== bridge) return;
  for (const [id, command] of commands) {
    if (pendingPower.get(id) !== command) continue;
    if (accepted.includes(id)) command.accepted = true;
    else pendingPower.delete(id);
  }
  if (accepted.length !== ids.length) {
    showToast(ids.length === 1 ? errors[ids[0]] :
      `${accepted.length}/${ids.length} commandes acceptées par le pont.`, true);
    renderPower();
  }
  await refresh();
}

function currentMinute() {
  if (!state) return 480;
  if (!state.simulation.enabled) {
    const light=state.lights.find(l=>l.id===selectedId);
    if(light?.profile_type==='solar'&&Number.isFinite(light.profile_minute))return (light.profile_minute+(performance.now()-lastStateAt)/60000)%1440;
    const now = new Date(); return now.getHours()*60+now.getMinutes()+now.getSeconds()/60;
  }
  const sim=state.simulation;
  return (sim.minute+(sim.running?(performance.now()-lastStateAt)/1000 *1440/sim.seconds_per_day:0))%1440;
}
function interpolation(points, minute) {
  if (!points?.length) return 0;
  let m=((minute%1440)+1440)%1440;
  let sorted=[...points].sort((a,b)=>a.minute-b.minute);
  let after=sorted.findIndex(p=>p.minute>m);
  let a,b,start,end;
  if (after===0 || after===-1) {a=sorted[sorted.length-1];b=sorted[0];start=a.minute;end=b.minute+1440;if(m<start)m+=1440;}
  else {a=sorted[after-1];b=sorted[after];start=a.minute;end=b.minute;}
  let t=(m-start)/(end-start); t=Math.max(0,Math.min(1,t));
  const smooth=t*t*(3-2*t);
  return a.brightness+(b.brightness-a.brightness)*smooth;
}
function initClockFace() {
  const ticks=$("#clock-ticks");
  for(let i=0;i<24;i++) {
    const a=i*2*Math.PI/24;
    const major=i%3===0;
    const x=Math.sin(a),y=-Math.cos(a);
    ticks.insertAdjacentHTML('beforeend', `<line class="clock-tick" x1="${160+x*(major?127:133)}" y1="${160+y*(major?127:133)}" x2="${160+x*140}" y2="${160+y*140}" stroke-width="${major?2.4:1}"/>${major?`<text class="clock-number" x="${160+x*109}" y="${160+y*109+5}" text-anchor="middle">${String(i).padStart(2,'0')}</text>`:''}`);
  }
}
function tickClock() {
  const minute=seekDragging?Number($('#time-slider').value):currentMinute();
  $("#hour-hand").setAttribute("transform", `rotate(${minute/1440*360} 160 160)`);
  $("#minute-hand").setAttribute("transform", `rotate(${(minute%60)/60*360} 160 160)`);
  $("#clock-digital").textContent=mm(minute);
  if(!seekDragging) $('#time-slider').value=Math.floor(minute);
  if(document.activeElement!==$('#seek-time')) $('#seek-time').value=mm(minute);
  const d=new Date(); $("#real-clock").textContent=d.toLocaleTimeString("fr-CH",{hour12:false});
  renderProfileTarget();
}
function renderProfileTarget() {
  // The saved active profile is evaluated by the server, never by an editor.
  const light=state?.lights.find(l=>l.id===selectedId);
  const target=$('#profile-target'),status=$('#profile-live-status');
  const label=light?.manual_override?'Cible au rallumage':'Cible active';
  target.textContent=Number.isFinite(light?.target)?`${label} ${Math.round(light.target)} %`:`${label} — %`;
  if(!status)return;
  if(!light){status.textContent='Choisis une lampe pour voir son état.';return;}
  const observed=Number.isFinite(light.brightness)?`${Math.round(light.brightness)} %`:'— %';
  const vacation=light.vacation_active;
  const reason=vacation?'Vacances prioritaire':light.manual_override?'Manuel temporaire · reprise au rallumage':light.control_mode!=='auto'?'Manuel · profil non appliqué':!light.on?'Éteinte · profil en attente':light.status!=='connected'?'Connexion à vérifier':'Auto · profil actif';
  status.textContent=`Lampe : ${observed} · ${reason}`;
  if(state.error)status.textContent+=' · lecture du pont indisponible';
}
function addLightCards(lights) {
  const ids=JSON.stringify([state.bridge_ip,lights.map(light=>light.id)]);
  if (ids===cardIds) return;
  cardIds=ids;
  $("#light-grid").innerHTML=lights.length?lights.map(light=>{
    const id=escapeHtml(light.id),name=escapeHtml(light.name);
    return `<article class="light-card mode-row" data-id="${id}">
      <span class="lamp-name">${name}</span>
      <div class="lamp-mode-buttons" role="group" aria-label="Pilotage de ${name}">
        <button type="button" class="lamp-mode-btn" data-control="auto" aria-pressed="false">Auto</button>
        <button type="button" class="lamp-mode-btn" data-control="manuel" aria-pressed="false">Manuel</button>
      </div>
      <div class="lamp-brightness" hidden>
        <label>Luminosité <output class="light-value">— %</output>
          <input class="range light-brightness" type="range" min="1" max="100" step="1" aria-label="Luminosité de ${name}">
        </label>
        <small class="brightness-status"></small>
      </div>
      <small class="lamp-override" hidden>Manuel jusqu’au rallumage</small>
    </article>`;
  }).join(''):'<div class="empty">Aucune ampoule trouvée.</div>';
  $$(".mode-row").forEach(bindLampControls);
  const select=$("#profile-light"); const was=selectedId;
  select.innerHTML=lights.map(l=>`<option value="${escapeHtml(l.id)}">${escapeHtml(l.name)}</option>`).join('');
  selectedId=lights.some(l=>l.id===was)?was:(lights[0]?.id||null);
  if(selectedId){select.value=selectedId;loadProfile();}
}
function bindLampControls(card) {
  const id=card.dataset.id;
  const bridge=state.bridge_ip;
  const path=`/api/light/${encodeURIComponent(id)}`;
  const slider=card.querySelector('.light-brightness');
  const value=card.querySelector('.light-value');
  const command={draft:null, queued:null, inFlight:null, timer:null, sentAt:-Infinity,
    confirmUntil:0, mode:null, flush:false};
  lampControls.set(card,command);

  function pump() {
    if(command.inFlight || command.queued===null)return;
    if(!card.isConnected || state.bridge_ip!==bridge || slider.disabled){
      command.queued=null;
      command.flush=false;
      return;
    }
    clearTimeout(command.timer);
    const delay=DIM_INTERVAL_MS-(performance.now()-command.sentAt);
    if(!command.flush && delay>0){
      command.timer=setTimeout(pump,delay);
      return;
    }
    const brightness=command.queued;
    command.queued=null;
    command.flush=false;
    command.sentAt=performance.now();
    command.inFlight=api(path+'/brightness','POST',{brightness,interactive:true});
    void command.inFlight.then(()=>{
      command.confirmUntil=performance.now()+DIM_CONFIRM_MS;
    },error=>{
      if(command.queued===null && !command.mode){
        command.draft=null;
        showToast(error.message,true);
      }
    }).finally(()=>{
      command.inFlight=null;
      if(command.queued!==null)pump();
      else if(!command.mode && card.isConnected){
        updateLights(state.lights);
        void refresh();
      }
    });
  }
  slider.oninput=()=>{
    command.draft=Number(slider.value);
    command.queued=command.draft;
    value.textContent=`${slider.value} %`;
    pump();
  };
  slider.onchange=()=>{
    if(command.queued===null)return;
    command.flush=true;
    pump();
  };
  card.querySelectorAll('.lamp-mode-btn').forEach(btn=>btn.onclick=()=>safe(async()=>{
    if(command.mode)return;
    command.mode=btn.dataset.control;
    command.queued=null;
    command.flush=false;
    clearTimeout(command.timer);
    updateLights(state.lights);
    try{
      await command.inFlight?.catch(()=>{});
      if(!card.isConnected || state.bridge_ip!==bridge)return;
      const result=await api(path+'/control-mode','POST',{mode:command.mode});
      if(!card.isConnected || state.bridge_ip!==bridge)return;
      stateGeneration++;
      const light=state.lights.find(item=>item.id===id);
      if(light){light.control_mode=result.mode;light.manual_override=false;}
    }finally{
      command.mode=null;
      command.draft=null;
      updateLights(state.lights);
      void refresh();
    }
  }));
}

function updateLights(lights) {
  const byId=new Map(lights.map(light=>[light.id,light]));
  for(const card of $$('.mode-row')){
    const light=byId.get(card.dataset.id);
    if(!light)continue;
    const command=lampControls.get(card);
    const brightness=card.querySelector('.lamp-brightness');
    const slider=card.querySelector('.light-brightness');
    const mode=command.mode??light.control_mode;
    brightness.hidden=mode==='auto'||!light.capabilities.dimming;
    const offline=!state.connected||light.status==='disconnected';
    const reason=offline?'Lampe hors ligne':!light.on?'Allume la lampe dans Pièces.':'';
    card.querySelector('.brightness-status').textContent=reason;
    const observed=light.brightness==null?null:Math.round(light.brightness);
    if(!command.inFlight && command.queued===null &&
        (observed===command.draft || performance.now()>=command.confirmUntil)){
      command.draft=null;
    }
    const shown=command.draft??observed;
    slider.value=Math.max(1,shown??1);
    card.querySelector('.light-value').textContent=shown===null?'— %':`${shown} %`;
    slider.disabled=brightness.hidden||!!reason||!!command.mode;
    card.querySelectorAll('.lamp-mode-btn').forEach(btn=>{
      const chosen=btn.dataset.control===mode;
      btn.disabled=!!command.mode;
      btn.classList.toggle('active',chosen);
      btn.setAttribute('aria-pressed',String(chosen));
    });
    card.querySelector('.lamp-override').hidden=!light.manual_override;
  }
}
function setTab(tab) {
  if(tab==="colors")tab="profiles";
  const inSettings=['settings','location','setup','diagnostics','presence','updates'].includes(tab);
  activeTab=tab;
  document.body.classList.toggle('rooms-page',tab==='rooms');
  $$('.tab').forEach(x=>x.classList.toggle('hidden', x.id!==`tab-${inSettings?'settings':tab}`));
  $$('.settings-panel').forEach(x=>x.classList.toggle('hidden',x.id!==`tab-${tab}`));
  $$('[data-tab]').forEach(x=>{
    const chosen=x.dataset.tab===tab || (x.dataset.tab==='settings'&&inSettings);
    x.classList.toggle('active',chosen);
    x.setAttribute('aria-current',chosen?'page':'false');
  });
  const titles={
    rooms:['Pièces','Commande une pièce ou une lampe.'],
    dashboard:['Automatisations',''],
    profiles:['Profil',''],
    simulation:['Simulation',''],
    settings:['Paramètres','']
  };
  const [title,subtitle]=titles[inSettings?'settings':tab];
  $('#page-title').textContent=title;
  $('#page-subtitle').textContent=subtitle;
  $('#page-subtitle').hidden=!subtitle;
  if(tab==='location')window.HueSolar?.openLocation();
  if(tab==='simulation')renderSimulationLamp();
  if(tab==='rooms' && state)window.HueRooms?.update(state);
  if(tab==='presence')window.HuePresence?.refresh();
  if(tab==='profiles' && state?.lights?.length)window.HueRGB?.open(selectedId,false,true);
  if(tab==='setup')safe(initializeSetup);
  if(tab==='diagnostics'){safe(refreshDiagnostics);safe(refreshLogs);safe(loadStartSceneGroups);}
  if(tab==='updates')safe(refreshUpdater);
  return true;
}

const soloSwitch = $("#solo-enabled");
let soloSaving = false;
let soloGeneration = 0;
soloSwitch.addEventListener("change", async () => {
  const enabled = soloSwitch.checked;
  soloSaving = true;
  soloGeneration++;
  soloSwitch.disabled = true;
  try {
    await api("/api/solo", "PUT", {enabled});
    showToast(enabled ? "Mode Solo activé." : "Mode Solo désactivé.");
  } catch (error) {
    soloSwitch.checked = !enabled;
    showToast(error.message, true);
  } finally {
    soloSaving = false;
    soloGeneration++;
    soloSwitch.disabled = false;
    await refresh();
  }
});

async function refresh() {
  if(refreshBusy)return; refreshBusy=true;
  const generation=stateGeneration;
  const soloRead=soloGeneration;
  try{
    const s=await api('/api/state');
    if(generation!==stateGeneration)return;
    confirmPower(s);
    state=s;lastStateAt=performance.now();
    window.HueDawn?.refresh(s.lights);
    if (!soloSaving && soloRead === soloGeneration) {
      soloSwitch.checked = s.solo_enabled;
      soloSwitch.disabled = false;
    }
    $('#bridge-dot').classList.toggle('online',s.connected);
    $('#bridge-label').textContent=s.connected?'Pont connecté':'Pont non connecté';
    $('#bridge-ip').textContent=s.bridge_ip??'Association requise';
    if(s.needs_setup && !setupFirstShown) {setupFirstShown=true;setTab('setup');}
    if(activeTab==='rooms')window.HueRooms?.update(s);
    $('#error-banner').classList.toggle('hidden', !s.error || s.needs_setup);
    $('#error-banner').textContent=s.error||'';
    if(document.activeElement!==$('#clock-source'))$('#clock-source').value=s.clock_mode;
    renderSimulationControls();
    $('#clock-mode').textContent=s.clock_mode==='accelere'?'TEMPS ACCÉLÉRÉ':'HEURE RÉELLE';
    $('#sim-notice').textContent=s.clock_mode==='accelere'?'L’horloge accélérée agit seulement sur les lampes en Auto.':'L’horloge réelle agit seulement sur les lampes en Auto.';
    addLightCards(s.lights);
    updateLights(s.lights);
    if(activeTab==='simulation')renderSimulationLamp();
    window.HueSolar?.refreshStatus();
    tickClock();
  } catch(e){$('#bridge-label').textContent='Serveur indisponible';$('#error-banner').classList.remove('hidden');$('#error-banner').textContent=e.message;}
  finally{refreshBusy=false;}
}
function renderSimulationLamp() {
  const light=state?.lights.find(l=>l.id===selectedId);
  const value=Number.isFinite(light?.target)?` · cible ${Math.round(light.target)} %`:'';
  $('#simulation-lamp').textContent=light?`Lampe sélectionnée · ${light.name}${value}`:'';
}
function renderSimulationControls() {
  const simulation=state?.simulation;
  const disabled=simulationBusy||!simulation?.enabled;
  $('#sim-play').textContent=simulation?.running?'Ⅱ Pause':'▶ Reprendre';
  for(const id of ['sim-play','sim-speed','time-slider','seek-time']) $('#'+id).disabled=disabled;
  $('#clock-source').disabled=simulationBusy;
  if(simulation) $('#sim-speed').value=simulation.seconds_per_day;
}

async function updateSimulation(change) {
  if(simulationBusy||!state?.simulation.enabled)return;
  simulationBusy=true;
  renderSimulationControls();
  try {
    const simulation=await api('/api/simulation','POST',change);
    stateGeneration++;
    state.simulation=simulation;
    lastStateAt=performance.now();
    await refresh();
  } finally {
    simulationBusy=false;
    seekDragging=false;
    $('#seek-time').value=mm(currentMinute());
    renderSimulationControls();
    tickClock();
    renderChart();
  }
}

async function loadProfile() {
  if(!selectedId)return;
  const id=selectedId;
  try {
    const points=await api(`/api/profile/${encodeURIComponent(id)}`);
    if(id!==selectedId)return;
    editingPoints=points;profileDirty=false;renderPointRows();renderChart();
  } catch(e){showToast(e.message,true);}
}
function readPoints() {
  return $$('.point-row').map(row=>{
    const time=row.querySelector('input[type="time"]').value;
    const [h,m]=time.split(':').map(Number);
    return {minute:h*60+m,brightness:Number(row.querySelector('input[type="number"]').value)};
  }).sort((a,b)=>a.minute-b.minute);
}
function renderPointRows() {
  $('#point-rows').innerHTML=editingPoints.map((p,i)=>`<div class="point-row" data-index="${i}"><label>Heure<br><input type="time" value="${mm(p.minute)}"></label><label>Luminosité<br><input type="number" min="1" max="100" step="1" value="${p.brightness}"> %</label><button title="Retirer le point" aria-label="Retirer le point">×</button></div>`).join('');
  $$('.point-row').forEach(row=>{
    row.querySelector('button').onclick=()=>{if(editingPoints.length<=2){showToast('Il faut au moins deux points',true);return;}editingPoints.splice(Number(row.dataset.index),1);profileDirty=true;renderPointRows();renderChart();};
    row.querySelectorAll('input').forEach(i=>i.addEventListener('change',()=>{editingPoints=readPoints();profileDirty=true;renderChart();}));
  });
}
function renderChart() {
  let points;
  try{points=readPoints();}catch{return;}
  if(!points.length)return;
  const svg=$('#profile-chart');const left=30,right=826,top=14,bottom=220;
  const x=minute=>left+minute/1440*(right-left);
  const y=b=>bottom-(b/100)*(bottom-top);
  const grid=[];
  for(let j=0;j<=4;j++) {let bright=j*25;grid.push(`<line x1="${left}" y1="${y(bright)}" x2="${right}" y2="${y(bright)}" stroke="#33475a" stroke-dasharray="4,6"/><text x="5" y="${y(bright)+4}" fill="#8799a9" font-size="11">${bright}</text>`);}
  for(let i=0;i<=4;i++)grid.push(`<line x1="${x(i*360)}" y1="${top}" x2="${x(i*360)}" y2="${bottom}" stroke="#2b4055"/>`);
  let path=''; for(let m=0;m<=1440;m+=6){let v=interpolation(points,m%1440);path+=`${m?'L':'M'}${x(m).toFixed(2)},${y(v).toFixed(2)} `;}
  const dots=points.map(p=>`<circle cx="${x(p.minute)}" cy="${y(p.brightness)}" r="5" fill="#efbf6d" stroke="#142235" stroke-width="3"/>`).join('');
  const current=currentMinute();
  svg.innerHTML=`<defs><linearGradient id="curve-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="#efbf6d" stop-opacity=".30"/><stop offset="100%" stop-color="#efbf6d" stop-opacity="0"/></linearGradient></defs>${grid.join('')}<path d="${path} L${right},${bottom} L${left},${bottom}Z" fill="url(#curve-fill)"/><path d="${path}" stroke="#efbf6d" fill="none" stroke-width="3" vector-effect="non-scaling-stroke"/>${dots}<line x1="${x(current)}" y1="${top}" x2="${x(current)}" y2="${bottom}" stroke="#80d4c5" stroke-width="2" stroke-dasharray="5,4"/><circle cx="${x(current)}" cy="${y(interpolation(points,current))}" r="6" fill="#80d4c5"/>`;
}
async function loadStartSceneGroups() {
  const select = $('#start-scene-group');
  const submit = $('#prepare-start-scenes');
  submit.disabled = true;
  select.replaceChildren();
  const groups = (await api('/api/lighting-groups')).filter(group => group.light_ids.length);
  select.add(new Option('Toutes les pièces et zones', 'all'));
  for (const group of groups) {
    select.add(new Option(group.name, JSON.stringify({group_id: group.id, kind: group.kind})));
  }
  submit.disabled = groups.length === 0;
}

$('#start-scenes-form')?.addEventListener('submit', async event => {
  event.preventDefault();
  const submit = $('#prepare-start-scenes');
  const select = $('#start-scene-group');
  const status = $('#start-scenes-status');
  const groups = select.value === 'all' ? [...select.options].slice(1) : [select.selectedOptions[0]];
  submit.disabled = select.disabled = true;
  status.textContent = 'Préparation sur le pont…';
  const prepared = [];
  const failed = [];
  try {
    for (const group of groups) {
      try {
        const scene = await api('/api/start-scenes', 'POST', JSON.parse(group.value));
        prepared.push(`${group.text} (${scene.name})`);
      } catch (error) {
        failed.push(`${group.text} — ${error.message}`);
      }
    }
    const messages = [];
    if (prepared.length) messages.push(`Scènes prêtes : ${prepared.join(', ')}.`);
    if (failed.length) messages.push(`À réessayer : ${failed.join(', ')}.`);
    status.textContent = messages.join(' ');
  } finally {
    submit.disabled = select.disabled = false;
  }
});

async function refreshDiagnostics(){
  const diag=await api('/api/diagnostics');
  $('#diag-meta').textContent=`Pont ${diag.bridge_ip??'inconnu'} · dernière lecture ${diag.last_poll??'jamais'} · ${diag.lights.length} ampoule(s) · événements Hue : ${diag.event_stream?.status??'inconnu'}`;
  $('#diag-lights').innerHTML=diag.lights.map(l=>`<div class="diag-item"><div class="diag-head"><div><h3>${escapeHtml(l.name)}</h3><small>${escapeHtml(l.manufacturer)} · ${escapeHtml(l.model)} · ${escapeHtml(l.status)}</small></div><div><button class="btn muted test-power-btn" data-id="${escapeHtml(l.id)}">Armer test secteur</button> <button class="btn muted powerup-btn" data-id="${escapeHtml(l.id)}" ${!l.capabilities.powerup?'disabled':''}>Démarrage / powerup</button></div></div><p><code>${escapeHtml(l.id)}</code></p><div class="capabilities">${Object.entries(l.capabilities).map(([k,v])=>`<span class="cap ${v?'':'no'}">${v?'✓':'–'} ${escapeHtml(k)}</span>`).join('')}</div><p>Powerup déclaré : <code>${escapeHtml(l.powerup?JSON.stringify(l.powerup):'non disponible')}</code></p><p>Test de coupure : <code>${escapeHtml(diag.power_tests?.[l.id]?.status||'non lancé')}${diag.power_tests?.[l.id]?.observed_offline_seconds != null ? ' · Zigbee hors ligne observé '+escapeHtml(diag.power_tests[l.id].observed_offline_seconds)+' s' : ''}</code></p></div>`).join('');
  $$('.powerup-btn').forEach(btn=>btn.onclick=()=>openPowerup(btn.dataset.id));
  $$('.test-power-btn').forEach(btn=>btn.onclick=()=>safe(async()=>{await api(`/api/power-test/${encodeURIComponent(btn.dataset.id)}/arm`,'POST',{});showToast('Test armé : coupe puis remets le courant avec l’interrupteur.');await refreshDiagnostics();}));
  await refreshLogs();
}
async function refreshLogs(){const lines=await api('/api/logs');$('#log-display').textContent=lines.length?lines.join('\n'):'Aucun événement enregistré.';}
function openPowerup(id){powerupId=id;const l=state?.lights.find(l=>l.id===id);$('#powerup-name').textContent=l?.name??id;$('#powerup-preset').value=l?.powerup?.preset||'custom';$('#powerup-brightness').value=l?.powerup?.preset==='custom'?(l.powerup?.dimming?.dimming?.brightness??10):10;updatePowerupVisibility();$('#powerup-dialog').showModal();}
function updatePowerupVisibility(){$('#powerup-brightness-wrap').classList.toggle('hidden',$('#powerup-preset').value!=='custom');}
function downloadJSON(data,name){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),3000);}
function setSetupStatus(message, isError=false) {
  const el = $('#setup-status');
  el.textContent = message;
  el.classList.toggle('bad',isError);
}
function setupSelection() {
  const input = $('#setup-ip');
  return input.value.trim() || $('#setup-bridges').value;
}
async function discoverHue() {
  const input=$('#setup-ip');
  const useDetected=$('#setup-use-detected');
  useDetected.hidden=true;
  setSetupStatus('Recherche du pont sur le réseau…');
  const button=$('#setup-discover');button.disabled=true;
  try {
    const info=await api('/api/setup/discover');
    const ips=info.bridges||[];
    const select=$('#setup-bridges');
    select.replaceChildren(new Option('Choisir un pont détecté…',''), ...ips.map(ip=>new Option(ip,ip)));
    select.hidden=ips.length<2;
    // Never overwrite a saved address or typing, including edits made while fetching.
    if(ips.length===1 && !input.value.trim() && !setupIpEdited)input.value=ips[0];
    if(ips.length===1 && input.value.trim()!==ips[0]){
      useDetected.textContent='Utiliser '+ips[0];
      useDetected.dataset.ip=ips[0];useDetected.hidden=false;
    }
    if(ips.length)setSetupStatus(ips.length===1
      ? `Pont détecté : ${ips[0]}. ${input.value.trim()!==ips[0]?'Adresse saisie conservée ; utilise le bouton pour choisir ce pont.':'Tu peux démarrer l’association si nécessaire.'}`
      : `${ips.length} ponts détectés. Choisis un pont ou conserve l’adresse saisie.`);
    else setSetupStatus('Aucun pont trouvé. Adresse saisie conservée. Vérifie le réseau ou saisis l’IP de ton pont.',true);
  } catch(e) {setSetupStatus(e.message,true);}
  finally {button.disabled=false;}
}
async function initializeSetup() {
  if(setupInitDone)return;
  setupInitDone=true;
  try {
    const cfg=await api('/api/setup/status');
    if(cfg.ip && !setupIpEdited && !$('#setup-ip').value.trim())$('#setup-ip').value=cfg.ip;
    if(cfg.paired){setSetupStatus('Une configuration existe. Si elle ne fonctionne plus, tu peux refaire l’association.');return;}
  } catch(e){setSetupStatus(e.message,true);}
  // A working stored configuration does not require a discovery or pairing.
  await discoverHue();
}
async function pairHue() {
  if(setupInProgress)return;
  const ip=setupSelection();
  if(!ip){setSetupStatus('Sélectionne un pont ou saisis son adresse IP.',true);return;}
  setupInProgress=true;setupCancelled=false;
  $('#setup-pair').disabled=true;$('#setup-ip').disabled=true;$('#setup-discover').disabled=true;$('#setup-bridges').disabled=true;$('#setup-use-detected').disabled=true;$('#setup-cancel').classList.remove('hidden');
  const stopAt=Date.now()+45000;
  try{
    while(Date.now()<stopAt && !setupCancelled){
      const sec=Math.ceil((stopAt-Date.now())/1000);
      setSetupStatus(`Appuie sur le bouton du pont Hue — en attente (${sec} s restantes)…`);
      try{
        const result=await api('/api/setup/pair','POST',{ip});
        if(result.paired){
          setSetupStatus(`Connexion réussie avec ${result.ip} ! ${result.lights} ampoule(s) trouvée(s).`);
          $('#setup-connected').classList.remove('hidden');
          $('#setup-connected').textContent=`✓ Pont connecté : ${result.ip} · ${result.lights} ampoule(s).`;
          await refresh();
          setTab('rooms');
          showToast('Pont connecté. Configuration enregistrée automatiquement.');
          return;
        }
      }catch(e){setSetupStatus(e.message,true);return;}
      if(!setupCancelled) await new Promise(resolve=>setTimeout(resolve,1500));
    }
    setSetupStatus(setupCancelled?'Association annulée.':'Délai écoulé. Relance l’association et appuie sur le bouton du pont.',!setupCancelled);
  }finally{setupInProgress=false;$('#setup-pair').disabled=false;$('#setup-ip').disabled=false;$('#setup-discover').disabled=false;$('#setup-bridges').disabled=false;$('#setup-use-detected').disabled=false;$('#setup-cancel').classList.add('hidden');}
}

function renderUpdateChanges(status){
  const title=$('#update-changes-title');
  const kind=$('#update-changes-type');
  const list=$('#update-changes-list');
  const pending=!!status.available;
  title.textContent=pending?'Dans la prochaine mise à jour':'Quoi de neuf dans la dernière installation ?';
  const changes=pending?status.changes:status.last_changes;
  const scope=pending?status.change_kind:status.last_change_kind;
  list.replaceChildren();
  if(scope==='internal'){
    kind.textContent='Mise à jour interne (calculs, tests ou documentation) : aucune différence visuelle attendue.';
  }else if(scope==='interface'){
    kind.textContent='Des fichiers de l’interface ont changé : des différences visuelles sont possibles.';
  }else{
    kind.textContent='Consulte les changements ci-dessous ou le journal complet.';
  }
  const notes=Array.isArray(changes)?changes.filter(s=>typeof s==='string').slice(0,8):[];
  if(!notes.length && !pending && status.latest_note){
    notes.push('Dernier cycle du journal : '+status.latest_note.replaceAll('**','').replaceAll('`',''));
  }
  if(!notes.length) notes.push(pending?'Détail indisponible pour cette version.':'Aucun historique d’installation disponible pour le moment.');
  for(const note of notes){
    const item=document.createElement('li');
    item.textContent=note;
    list.appendChild(item);
  }
}
async function refreshUpdater(){
  const status=await api('/api/update/status');
  const installed=$('#update-installed'),remote=$('#update-remote'),label=$('#update-status');
  installed.textContent=status.installed||'Archive / inconnue';
  remote.textContent=status.remote||'Pas encore vérifiée';
  const revision=status.installed;
  $('#brand-version').textContent=revision?'Commande locale · révision '+revision.slice(0,8):'Commande locale · révision inconnue';
  $('#footer-version').textContent=revision?'Hue Lab · révision '+revision.slice(0,8):'Hue Lab · révision inconnue';
  label.textContent=status.message||(status.configured?'Prêt pour la vérification GitHub.':'Migration initiale requise via Termux.');
  renderUpdateChanges(status);
  $('#update-version').textContent=revision?revision.slice(0,8):'Version inconnue';
  const badge=$('#update-badge');
  badge.hidden=!status.available&&!status.busy;
  badge.textContent=status.busy?'En cours…':'Disponible';
  $('.update-shortcut').setAttribute('aria-label',status.available?'Mises à jour disponibles':'Mises à jour');
  $('#settings-update-dot').hidden=!status.available&&!status.busy;
  const blocked=!status.configured||!!status.busy;
  $('#update-check').disabled=blocked;
  $('#update-apply').disabled=blocked||!status.available;
  if(updaterWasBusy&&!status.busy&&status.phase==='success'){
    window.location.reload();return;
  }
  updaterWasBusy=!!status.busy;
}
async function runUpdater(action){
  if(action==='apply'&&!window.confirm('Installer la mise à jour GitHub et redémarrer Hue Lab ? Les commandes seront indisponibles quelques instants.'))return;
  $('#update-check').disabled=true;$('#update-apply').disabled=true;
  try{
    await api('/api/update/'+action,'POST',{}, {'X-Hue-Update-Request':'1'});
    $('#update-status').textContent=action==='apply'?'Mise à jour demandée. Le serveur va redémarrer…':'Vérification GitHub demandée…';
    updaterWasBusy=action==='apply';
    window.setTimeout(()=>safe(refreshUpdater),1200);
  }catch(e){showToast(e.message,true);await safe(refreshUpdater);}
}

function bindEvents(){
  $('#update-check').onclick=()=>safe(()=>runUpdater('check'));
  $('#update-apply').onclick=()=>safe(()=>runUpdater('apply'));
  $('#setup-discover').onclick=()=>safe(discoverHue);
  $('#setup-ip').addEventListener('input',()=>{setupIpEdited=true;});
  $('#setup-use-detected').onclick=()=>{
    $('#setup-ip').value=$('#setup-use-detected').dataset.ip;
    setupIpEdited=true;$('#setup-use-detected').hidden=true;
  };
  $('#setup-bridges').onchange=e=>{if(e.target.value){$('#setup-ip').value=e.target.value;setupIpEdited=true;}};
  $('#setup-pair').onclick=()=>safe(pairHue);
  $('#setup-cancel').onclick=()=>{setupCancelled=true;setSetupStatus('Annulation demandée…');};
  $$('[data-tab]').forEach(btn=>btn.onclick=()=>setTab(btn.dataset.tab));
  $('#clock-source').onchange=e=>safe(async()=>{await api('/api/clock-mode','POST',{mode:e.target.value});showToast('Horloge '+(e.target.value==='reel'?'réelle':'accélérée')+' sélectionnée pour les lampes Auto.');await refresh();});
  $('#sim-play').onclick=()=>safe(()=>updateSimulation({running:!state.simulation.running}));
  $('#sim-speed').onchange=e=>safe(()=>updateSimulation({seconds_per_day:Number(e.target.value)}));
  $('#time-slider').addEventListener('input',()=>{seekDragging=true;tickClock();});
  $('#time-slider').addEventListener('change',e=>safe(()=>updateSimulation({minute:Number(e.target.value),running:false})));
  $('#seek-time').addEventListener('change',e=>{
    if(!e.target.value)return;
    const [hours,minutes]=e.target.value.split(':').map(Number);
    safe(()=>updateSimulation({minute:hours*60+minutes,running:false}));
  });
  $('#profile-light').onchange=e=>{selectedId=e.target.value;loadProfile();};
  $('#add-point').onclick=()=>{if(editingPoints.length>=24){showToast('Maximum 24 points',true);return;}editingPoints=readPoints();let next=720;while(editingPoints.some(p=>p.minute===next))next=(next+30)%1440;editingPoints.push({minute:next,brightness:50});editingPoints.sort((a,b)=>a.minute-b.minute);profileDirty=true;renderPointRows();renderChart();};
  $('#save-profile').onclick=()=>safe(async()=>{const points=readPoints();if(points.some(p=>!Number.isFinite(p.minute)||!Number.isFinite(p.brightness)))throw Error('Vérifie les heures et les valeurs.');await api(`/api/profile/${encodeURIComponent(selectedId)}`,'PUT',{points});showToast('Courbe enregistrée');await loadProfile();await refresh();});
  $('#refresh-diagnostics').onclick=()=>safe(refreshDiagnostics);
  $('#refresh-logs').onclick=()=>safe(refreshLogs);
  $('#export-diag').onclick=()=>safe(async()=>downloadJSON(await api('/api/diagnostics'),`hue-diagnostics-${new Date().toISOString().slice(0,10)}.json`));
  $('#powerup-preset').onchange=updatePowerupVisibility;
  $('#cancel-powerup').onclick=()=>$('#powerup-dialog').close();
  $('#save-powerup').onclick=()=>safe(async()=>{const preset=$('#powerup-preset').value;const brightness=Number($('#powerup-brightness').value);const result=await api(`/api/light/${encodeURIComponent(powerupId)}/powerup`,'POST',{preset,brightness});$('#powerup-dialog').close();showToast(result.verified_readback?'Réglage confirmé par lecture du pont. Teste le retour secteur.':'Écriture envoyée mais valeur non confirmée. Consulte Diagnostics.',!result.verified_readback);await refresh();await refreshDiagnostics();});
}
initClockFace();
bindEvents();
// The deferred profile editors must register their loaders before the first state is read.
document.addEventListener('DOMContentLoaded', () => {
  tickClock();
  refresh();
  safe(refreshUpdater);
  setInterval(tickClock, 250);
  setInterval(() => {
    refresh();
    if (activeTab === 'profiles' && !profileDirty) renderChart();
    if (activeTab === 'updates') refreshUpdater().catch(() => {
      $('#update-status').textContent = 'Connexion interrompue : redémarrage ou serveur indisponible…';
    });
  }, 2000);
  // The local status read does not trigger a GitHub check.
  setInterval(() => { if (activeTab !== 'updates') refreshUpdater().catch(() => {}); }, 60000);
}, {once: true});
