"use strict";
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let state = null;
let selectedId = null;
let editingPoints = [];
let cardIds = "";
let lastStateAt = performance.now();
let activeTab = "dashboard";
let powerupId = null;
let toastTimeout;
let seekDragging = false;
let refreshBusy = false;
let profileDirty = false;
let setupInProgress = false;
let setupFirstShown = false;
let setupCancelled = false;
let setupInitDone = false;
let updaterWasBusy = false;

function escapeHtml(text) { return String(text ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function mm(minute) { const m = ((Math.floor(minute) % 1440) + 1440) % 1440; return `${String(Math.floor(m/60)).padStart(2,"0")}:${String(m%60).padStart(2,"0")}`; }
function showToast(message, error=false) { const t = $("#toast"); t.textContent=message; t.className=`toast visible${error?' error':''}`; clearTimeout(toastTimeout); toastTimeout=setTimeout(()=>t.classList.remove("visible"),4000); }
async function api(url, method="GET", data=undefined) {
  const r = await fetch(url, {method, headers:data===undefined?{}:{"Content-Type":"application/json"}, body:data===undefined?undefined:JSON.stringify(data), cache:"no-store"});
  const result=await r.json().catch(()=>({error:`Réponse HTTP ${r.status} non JSON`}));
  if (!r.ok || result.ok===false) throw new Error(result.error || `HTTP ${r.status}`);
  return result.data ?? result;
}
async function safe(fn) { try {await fn();} catch(e) {showToast(e.message,true);} }
function currentMinute() {
  if (!state) return 480;
  if (!state.simulation.enabled) {
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
  if(!seekDragging){$("#time-slider").value=Math.floor(minute);$("#seek-label").textContent=mm(minute);}
  const d=new Date(); $("#real-clock").textContent=d.toLocaleTimeString("fr-CH",{hour12:false});
  if (state && selectedId && editingPoints.length && !profileDirty) $("#profile-target").textContent=`Cible ${Math.round(interpolation(editingPoints,minute))} %`;
}
function addLightCards(lights) {
  const ids=lights.map(l=>l.id).join("|");
  if (ids===cardIds) return;
  cardIds=ids;
  $("#light-grid").innerHTML=lights.length?lights.map(l=>`<article class="card light-card" data-id="${escapeHtml(l.id)}"><div class="light-top"><div class="light-icon">☀</div><label class="switch"><input class="light-switch" type="checkbox" aria-label="Allumer ou éteindre ${escapeHtml(l.name)}"><span></span></label></div><h3>${escapeHtml(l.name)}</h3><div class="subline">${escapeHtml(l.model)}</div><div class="light-bottom"><div class="light-level"><span>Luminosité</span><strong class="light-value">— %</strong></div><input class="range light-brightness" type="range" min="1" max="100" step="1"><div class="light-foot"><span class="pill light-status">…</span><button class="tiny light-details" type="button">Voir capacités →</button></div></div></article>`).join(''):'<div class="empty">Aucune ampoule trouvée.</div>';
  $$(".light-card").forEach(card=>{
    const id=card.dataset.id;
    card.querySelector(".light-switch").addEventListener("change",e=>safe(async()=>{await api(`/api/light/${encodeURIComponent(id)}/switch`,"POST",{on:e.target.checked});showToast('Commande envoyée');await refresh();}));
    const slider=card.querySelector(".light-brightness");
    slider.addEventListener("input",e=>{card.querySelector(".light-value").textContent=`${e.target.value} %`;});
    slider.addEventListener("change",e=>safe(async()=>{await api(`/api/light/${encodeURIComponent(id)}/brightness`,"POST",{brightness:Number(e.target.value)});showToast('Luminosité demandée');await refresh();}));
    card.querySelector(".light-details").addEventListener("click",()=>{setTab("diagnostics");});
  });
  const select=$("#profile-light"); const was=selectedId;
  select.innerHTML=lights.map(l=>`<option value="${escapeHtml(l.id)}">${escapeHtml(l.name)}</option>`).join('');
  selectedId=lights.some(l=>l.id===was)?was:(lights[0]?.id||null);
  if(selectedId){select.value=selectedId;loadProfile();}
}
function updateLights(lights) {
  for(const light of lights){
    const card=$$(".light-card").find(c=>c.dataset.id===light.id); if(!card)continue;
    const cb=card.querySelector('.light-switch'); const slider=card.querySelector('.light-brightness');
    if(document.activeElement!==cb)cb.checked=!!light.on;
    if(document.activeElement!==slider){slider.value=Math.max(1,Math.round(light.brightness??1));card.querySelector('.light-value').textContent=light.brightness==null?'Non disponible':`${Math.round(light.brightness)} %`;}
    slider.disabled=!light.capabilities.dimming||!light.on||light.status==='disconnected';
    cb.disabled=light.status==='disconnected'||!light.capabilities.on;
    const status=card.querySelector('.light-status');
    status.className='pill light-status'+(light.status==='connected'?' ok':light.status==='disconnected'?' bad':'');
    status.textContent=light.status==='connected'?'● En ligne':light.status==='disconnected'?'● Hors ligne':`● ${light.status}`;
  }
}
function setTab(tab) {
  activeTab=tab;
  $$('.tab').forEach(x=>x.classList.toggle('hidden', x.id!==`tab-${tab}`));
  $$('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));
  const titles={dashboard:['Tableau de bord','Éclairage, simulation et suivi en temps réel.'],profiles:['Courbes & simulation','Un cycle jour-nuit fluide et accéléré pour les essais.'],diagnostics:['Diagnostics','Ce que chaque ampoule déclare réellement au pont Hue.'],setup:['Connexion au pont','Découverte et association Philips Hue sans configuration manuelle.'],updates:['Mises à jour','Télécharger les nouvelles versions depuis GitHub, sans PC.']};
  $('#page-title').textContent=titles[tab][0]; $('#page-subtitle').textContent=titles[tab][1];
  if(tab==='diagnostics')safe(refreshDiagnostics);
  if(tab==='updates')safe(refreshUpdater);
}
async function refresh() {
  if(refreshBusy)return; refreshBusy=true;
  try{
    const s=await api('/api/state');state=s;lastStateAt=performance.now();
    $('#bridge-dot').classList.toggle('online',s.connected);
    $('#bridge-label').textContent=s.connected?'Pont connecté':'Pont non connecté';
    $('#bridge-ip').textContent=s.bridge_ip??'Association requise';
    if(s.needs_setup && !setupFirstShown) {setupFirstShown=true;setTab('setup');initializeSetup();}
    $('#error-banner').classList.toggle('hidden', !s.error || s.needs_setup);
    $('#error-banner').textContent=s.error||'';
    $('#stat-count').textContent=s.lights.length;
    $('#stat-online').textContent=s.lights.filter(l=>l.status==='connected').length;
    const names={manuel:'Manuel',reel:'Temps réel',accelere:'Temps accéléré'};
    $('#stat-mode').textContent=names[s.mode]??s.mode;
    $('#light-updated').textContent=s.last_poll?`Pont actualisé : ${s.last_poll.replace('T',' ').slice(11,19)}`:'En attente du pont';
    if(document.activeElement!==$('#hue-mode'))$('#hue-mode').value=s.mode;
    $('#sim-play').textContent=s.simulation.running?'Ⅱ Pause':'▶ Démarrer';
    $('#sim-play').disabled=!s.simulation.enabled;
    $('#sim-speed').value=s.simulation.seconds_per_day;
    $('#time-slider').disabled=s.mode!=='accelere';
    $('#sim-speed').disabled=s.mode!=='accelere';
    $('#clock-mode').textContent=s.mode==='accelere'?'TEMPS ACCÉLÉRÉ':'HEURE RÉELLE';
    $('#sim-notice').textContent=s.mode==='accelere'?'Le mode accéléré commande les ampoules réelles.':'Choisir le mode « Accéléré » ci-dessus pour piloter les lampes avec cette horloge.';
    addLightCards(s.lights);
    updateLights(s.lights);
    tickClock();
  } catch(e){$('#bridge-label').textContent='Serveur indisponible';$('#error-banner').classList.remove('hidden');$('#error-banner').textContent=e.message;}
  finally{refreshBusy=false;}
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
  setSetupStatus('Recherche du pont sur le réseau…');
  const button=$('#setup-discover');button.disabled=true;
  try {
    const info=await api('/api/setup/discover');
    const ips=info.bridges||[];
    const select=$('#setup-bridges');
    select.innerHTML=ips.length?ips.map(ip=>`<option value="${escapeHtml(ip)}">${escapeHtml(ip)}</option>`).join(''):'<option value="">Aucun pont détecté</option>';
    if(ips.length){$('#setup-ip').value=ips[0];setSetupStatus(`${ips.length} pont(s) trouvé(s). Démarre l'association.`);}
    else setSetupStatus('Aucun pont trouvé. Tu peux saisir directement son adresse IP.',true);
  } catch(e) {setSetupStatus(e.message,true);}
  finally {button.disabled=false;}
}
async function initializeSetup() {
  if(setupInitDone)return;
  setupInitDone=true;
  try {
    const cfg=await api('/api/setup/status');
    if(cfg.ip)$('#setup-ip').value=cfg.ip;
    if(cfg.paired){setSetupStatus('Une configuration existe. Si elle ne fonctionne plus, tu peux refaire l’association.');}
  } catch(e){setSetupStatus(e.message,true);}
  await discoverHue();
}
async function pairHue() {
  if(setupInProgress)return;
  const ip=setupSelection();
  if(!ip){setSetupStatus('Sélectionne un pont ou saisis son adresse IP.',true);return;}
  setupInProgress=true;setupCancelled=false;
  $('#setup-pair').disabled=true;$('#setup-cancel').classList.remove('hidden');
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
          setTab('dashboard');
          showToast('Pont connecté. Configuration enregistrée automatiquement.');
          return;
        }
      }catch(e){setSetupStatus(e.message,true);return;}
      if(!setupCancelled) await new Promise(resolve=>setTimeout(resolve,1500));
    }
    setSetupStatus(setupCancelled?'Association annulée.':'Délai écoulé. Relance l’association et appuie sur le bouton du pont.',!setupCancelled);
  }finally{setupInProgress=false;$('#setup-pair').disabled=false;$('#setup-cancel').classList.add('hidden');}
}

async function refreshUpdater(){
  const status=await api('/api/update/status');
  const installed=$('#update-installed'),remote=$('#update-remote'),label=$('#update-status');
  installed.textContent=status.installed||'Archive / inconnue';
  remote.textContent=status.remote||'Pas encore vérifiée';
  label.textContent=status.message||(status.configured?'Prêt pour la vérification GitHub.':'Migration initiale requise via Termux.');
  const blocked=!status.configured||!!status.busy;
  $('#update-check').disabled=blocked;
  $('#update-apply').disabled=blocked||!status.available;
  if(updaterWasBusy&&!status.busy&&status.phase==='success'){
    window.location.reload();return;
  }
  updaterWasBusy=!!status.busy;
}
async function runUpdater(action){
  const pin=$('#update-pin').value;
  if(!pin){showToast('Saisis ton code privé de mise à jour.',true);$('#update-pin').focus();return;}
  if(action==='apply'&&!window.confirm('Installer la mise à jour GitHub et redémarrer Hue Lab ? Les commandes seront indisponibles quelques instants.'))return;
  $('#update-check').disabled=true;$('#update-apply').disabled=true;
  try{
    await api('/api/update/'+action,'POST',{pin});
    $('#update-status').textContent=action==='apply'?'Mise à jour demandée. Le serveur va redémarrer…':'Vérification GitHub demandée…';
    updaterWasBusy=action==='apply';
    window.setTimeout(()=>safe(refreshUpdater),1200);
  }catch(e){showToast(e.message,true);await safe(refreshUpdater);}
}

function bindEvents(){
  $('#update-check').onclick=()=>safe(()=>runUpdater('check'));
  $('#update-apply').onclick=()=>safe(()=>runUpdater('apply'));
  $('#setup-discover').onclick=()=>safe(discoverHue);
  $('#setup-bridges').onchange=e=>{if(e.target.value)$('#setup-ip').value=e.target.value;};
  $('#setup-pair').onclick=()=>safe(pairHue);
  $('#setup-cancel').onclick=()=>{setupCancelled=true;setSetupStatus('Annulation demandée…');};
  $$('.nav-item').forEach(btn=>btn.onclick=()=>{setTab(btn.dataset.tab);if(btn.dataset.tab==='setup')safe(initializeSetup);});
  $('#hue-mode').onchange=e=>safe(async()=>{await api('/api/mode','POST',{mode:e.target.value});showToast('Mode '+e.target.options[e.target.selectedIndex].text+' activé');await refresh();});
  $('#go-diagnostics').onclick=()=>setTab('diagnostics');
  $('#sim-play').onclick=()=>safe(async()=>{await api('/api/simulation','POST',{running:!state.simulation.running});await refresh();});
  $('#sim-speed').onchange=e=>safe(async()=>{await api('/api/simulation','POST',{seconds_per_day:Number(e.target.value)});await refresh();});
  $('#time-slider').addEventListener('input',e=>{seekDragging=true;$('#seek-label').textContent=mm(Number(e.target.value));$('#hour-hand').setAttribute('transform',`rotate(${Number(e.target.value)/1440*360} 160 160)`);});
  $('#time-slider').addEventListener('change',e=>safe(async()=>{seekDragging=false;await api('/api/simulation','POST',{minute:Number(e.target.value)});await refresh();renderChart();}));
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
initClockFace();bindEvents();tickClock();setInterval(tickClock,250);refresh();setInterval(()=>{refresh();if(activeTab==='profiles'&&!profileDirty)renderChart();if(activeTab==='updates')refreshUpdater().catch(()=>{$('#update-status').textContent='Connexion interrompue : redémarrage ou serveur indisponible…';});},2000);
