/* Hue Lab v0.5.1 — ergonomie du profil, aucune modification du moteur Hue. */
"use strict";
(() => {
  const chart = document.querySelector('#profile-chart');
  const holder = document.querySelector('#point-rows');
  const lampSelector = document.querySelector('#profile-light');
  if (!chart || !holder || !lampSelector) return;

  let selectedMinute = null;
  let savedPoints = [];
  let dragging = null;
  let saving = false;
  const originalChart = renderChart;
  const originalLoad = loadProfile;
  const MIN_POINTS = 2;
  const MAX_POINTS = 24;
  const clone = arr => arr.map(p => ({minute:Number(p.minute), brightness:Number(p.brightness)}));
  const sorted = () => [...editingPoints].sort((a,b) => a.minute - b.minute);
  const validTime = m => Number.isInteger(m) && m >= 0 && m < 1440;
  const validLevel = v => Number.isInteger(v) && v >= 1 && v <= 100;
  const format = m => mm(m);

  function selected() {
    return editingPoints.find(p => p.minute === selectedMinute) ?? sorted()[0];
  }
  function setDirty() {
    profileDirty = true;
    updateIndicators();
  }
  function updateIndicators() {
    const dirty = !!profileDirty;
    const status = document.querySelector('#profile-edit-status');
    const save = document.querySelector('#save-profile');
    const undo = document.querySelector('#cancel-profile');
    const add = document.querySelector('#add-point');
    if (status) {
      status.textContent = dirty ? '● Modifications non enregistrées' : '✓ Courbe enregistrée';
      status.classList.toggle('unsaved', dirty);
      status.setAttribute('role', 'status');
    }
    if (save) save.disabled = saving || !dirty || !selectedId;
    if (undo) undo.disabled = saving || !dirty;
    if (add) add.disabled = saving || editingPoints.length >= MAX_POINTS;
  }
  function warn(message) { showToast(message, true); }
  function validate(points) {
    if (!Array.isArray(points) || points.length < MIN_POINTS || points.length > MAX_POINTS) throw Error('La courbe doit contenir entre 2 et 24 points.');
    const minutes = new Set();
    for (const p of points) {
      if (!validTime(p.minute) || !validLevel(p.brightness)) throw Error('Heure ou luminosité invalide.');
      if (minutes.has(p.minute)) throw Error('Deux points ne peuvent pas avoir la même heure.');
      minutes.add(p.minute);
    }
    return points.sort((a,b)=>a.minute-b.minute);
  }
  function changePoint(patch, redraw=true) {
    const point = selected();
    if (!point) return false;
    const minute = patch.minute ?? point.minute;
    const level = patch.brightness ?? point.brightness;
    if (!validTime(minute) || !validLevel(level)) { warn('Valeur hors limites.'); return false; }
    if (minute !== point.minute && editingPoints.some(p=>p!==point && p.minute===minute)) { warn('Un point existe déjà à cette heure.'); return false; }
    if (minute===point.minute && level===point.brightness) return true;
    point.minute = minute;
    point.brightness = level;
    selectedMinute = minute;
    setDirty();
    if (redraw) { renderPointRows(); renderChart(); }
    return true;
  }
  function changeTime(delta) {
    const p = selected();
    if (!p) return;
    const next = Math.min(1439, Math.max(0, p.minute + delta));
    changePoint({minute:next});
  }
  function changeLevel(delta) {
    const p = selected();
    if (!p) return;
    changePoint({brightness:Math.min(100,Math.max(1,p.brightness+delta))});
  }
  function updateLiveLevel(v) {
    const n = Number(v);
    if (!Number.isInteger(n) || n < 1 || n > 100) return;
    if (changePoint({brightness:n},false)) {
      const number = holder.querySelector('#v051-level-number');
      const value = holder.querySelector('#v051-level-value');
      const chip = holder.querySelector(`.v051-point[data-minute="${selectedMinute}"] .v051-chip-value`);
      if (number) number.value = String(n);
      if (value) value.textContent = `${n} %`;
      if (chip) chip.textContent = `${n} %`;
      renderChart();
    }
  }

  // Le moteur existant lit encore les points depuis l'ancien tableau ; la v0.5.1
  // conserve le même contrat JSON et utilise la liste en mémoire comme source unique.
  readPoints = () => clone(sorted());
  renderPointRows = function () {
    const points = sorted();
    if (!points.length) { holder.innerHTML = '<p class="v051-empty">Aucun point horaire.</p>'; updateIndicators(); return; }
    if (!points.some(p=>p.minute===selectedMinute)) selectedMinute = points[0].minute;
    const p = selected();
    holder.innerHTML = `
      <div class="v051-list-head"><strong>Points horaires <span>(${points.length}/${MAX_POINTS})</span></strong><span>Sélectionne un point</span></div>
      <div class="v051-point-list" role="group" aria-label="Points de la courbe">
        ${points.map(pt=>`<button class="v051-point ${pt.minute===p.minute?'is-selected':''}" type="button" data-minute="${pt.minute}" aria-pressed="${pt.minute===p.minute}"><span class="v051-chip-time">${format(pt.minute)}</span><span class="v051-chip-value">${pt.brightness} %</span></button>`).join('')}
      </div>
      <section class="v051-editor" aria-label="Édition du point ${format(p.minute)}">
        <div class="v051-editor-top"><div><small>POINT SÉLECTIONNÉ</small><h3>${format(p.minute)}</h3></div><button id="v051-remove" type="button" class="v051-remove" ${points.length<=MIN_POINTS?'disabled':''} aria-label="Supprimer le point de ${format(p.minute)}">Supprimer</button></div>
        <div class="v051-field"><label for="v051-point-time">Heure exacte</label>
          <div class="v051-time-control"><button type="button" id="v051-time-minus" aria-label="Reculer de 5 minutes">− 5 min</button><input id="v051-point-time" type="text" value="${format(p.minute)}" maxlength="5" inputmode="numeric" placeholder="HH:MM" autocomplete="off" spellcheck="false" aria-label="Heure du point"><button type="button" id="v051-time-plus" aria-label="Avancer de 5 minutes">+ 5 min</button></div>
        </div>
        <div class="v051-field"><div class="v051-level-head"><label for="v051-level-range">Luminosité</label><strong id="v051-level-value">${p.brightness} %</strong></div>
          <input id="v051-level-range" type="range" min="1" max="100" step="1" value="${p.brightness}" aria-label="Luminosité du point">
          <div class="v051-level-control"><button id="v051-level-minus" type="button" aria-label="Diminuer de 5 pour cent">− 5 %</button><label for="v051-level-number">Valeur exacte</label><input id="v051-level-number" type="number" min="1" max="100" step="1" inputmode="numeric" value="${p.brightness}" aria-label="Luminosité exacte en pour cent"><button id="v051-level-plus" type="button" aria-label="Augmenter de 5 pour cent">+ 5 %</button></div>
        </div>
      </section>`;
    // Garde le point sélectionné visible dans le ruban horizontal sans
    // faire défiler toute la page lors des modifications.
    const strip = holder.querySelector('.v051-point-list');
    const chip = strip.querySelector('.v051-point.is-selected');
    if (chip && strip.scrollWidth > strip.clientWidth) {
      strip.scrollLeft = chip.offsetLeft - strip.offsetLeft - (strip.clientWidth - chip.offsetWidth) / 2;
    }
    holder.querySelectorAll('.v051-point').forEach(btn=>btn.addEventListener('click',()=>{
      selectedMinute = Number(btn.dataset.minute); renderPointRows(); renderChart();
    }));
    holder.querySelector('#v051-remove').onclick=()=>{
      if (editingPoints.length<=MIN_POINTS) return;
      const ix=points.findIndex(x=>x.minute===selectedMinute);
      editingPoints=editingPoints.filter(x=>x.minute!==selectedMinute);
      selectedMinute=sorted()[Math.min(ix,editingPoints.length-1)].minute;
      setDirty(); renderPointRows(); renderChart();
    };
    holder.querySelector('#v051-time-minus').onclick=()=>changeTime(-5);
    holder.querySelector('#v051-time-plus').onclick=()=>changeTime(5);
    holder.querySelector('#v051-point-time').onchange=e=>{
      const match=/^(\d{1,2}):(\d{2})$/.exec(e.target.value.trim());
      const m=match?Number(match[1])*60+Number(match[2]):NaN;
      if(!changePoint({minute:m})) e.target.value=format(selected().minute);
    };
    holder.querySelector('#v051-level-range').addEventListener('input',e=>updateLiveLevel(e.target.value));
    holder.querySelector('#v051-level-range').addEventListener('change',()=>renderPointRows());
    holder.querySelector('#v051-level-minus').onclick=()=>changeLevel(-5);
    holder.querySelector('#v051-level-plus').onclick=()=>changeLevel(5);
    holder.querySelector('#v051-level-number').onchange=e=>{
      if(!changePoint({brightness:Number(e.target.value)})) e.target.value=String(selected().brightness);
    };
    updateIndicators();
  };

  renderChart = function () {
    originalChart();
    const points = sorted();
    if (!points.length) return;
    const x = m => 30 + m / 1440 * (826 - 30);
    const y = level => 220 - level / 100 * (220 - 14);
    chart.insertAdjacentHTML('beforeend', points.map(p=>{
      const active = p.minute===selectedMinute;
      return `<circle class="v051-point-ring ${active?'is-selected':''}" cx="${x(p.minute)}" cy="${y(p.brightness)}" r="${active?10:7}" fill="none" stroke="${active?'#fff':'#efbf6d'}" stroke-width="2" vector-effect="non-scaling-stroke" pointer-events="none"/><circle class="v051-point-hit" cx="${x(p.minute)}" cy="${y(p.brightness)}" r="24" fill="transparent" data-minute="${p.minute}" role="button" aria-label="Point ${format(p.minute)} à ${p.brightness} pour cent" tabindex="0"/>`;
    }).join(''));
    if (profileDirty) {
      document.querySelector('#profile-target').textContent=`Cible ${Math.round(interpolation(points,currentMinute()))} %`;
    }
  };
  loadProfile = async function () {
    await originalLoad();
    if (!profileDirty) {
      savedPoints = clone(editingPoints);
      if (!editingPoints.some(p=>p.minute===selectedMinute)) selectedMinute=sorted()[0]?.minute ?? null;
      renderPointRows();renderChart();
    }
  };

  // Le graphique peut être manipulé au doigt. Les champs précis restent la
  // solution de secours pour les points rapprochés et les lecteurs d'écran.
  function dragCoordinates(e) {
    const rect=chart.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const vx=(e.clientX-rect.left)/rect.width*840;
    const vy=(e.clientY-rect.top)/rect.height*260;
    return {
      minute:Math.min(1439, Math.max(0, Math.round(((vx-30)/(826-30)*1440)/5)*5)),
      brightness:Math.min(100,Math.max(1,Math.round((220-vy)/(220-14)*100)))
    };
  }
  chart.addEventListener('pointerdown', e=>{
    const hit=e.target.closest?.('.v051-point-hit');
    if (!hit) return;
    selectedMinute=Number(hit.dataset.minute);
    dragging={id:e.pointerId,minute:selectedMinute,originX:e.clientX,originY:e.clientY,moved:false};
    if (chart.setPointerCapture) chart.setPointerCapture(e.pointerId);
    renderPointRows();renderChart();
  });
  chart.addEventListener('pointermove', e=>{
    if (!dragging || e.pointerId!==dragging.id) return;
    if (Math.hypot(e.clientX-dragging.originX,e.clientY-dragging.originY)>7) dragging.moved=true;
    if (!dragging.moved) return;
    const pos=dragCoordinates(e);
    if (!pos) return;
    // Ne pas écraser un autre point lors d'un glissé.
    if (editingPoints.some(p=>p.minute!==selectedMinute && p.minute===pos.minute)) pos.minute=selectedMinute;
    changePoint(pos,false);
    renderPointRows();renderChart();
    e.preventDefault();
  });
  const stopDrag=e=>{
    if (!dragging || e.pointerId!==dragging.id) return;
    dragging=null;
    renderPointRows();renderChart();
  };
  chart.addEventListener('pointerup',stopDrag);
  chart.addEventListener('pointercancel',stopDrag);
  chart.addEventListener('keydown', e=>{
    if (e.key!=='Enter' && e.key!==' ') return;
    const hit=e.target.closest?.('.v051-point-hit');
    if (!hit) return;
    e.preventDefault();selectedMinute=Number(hit.dataset.minute);renderPointRows();renderChart();
  });

  document.querySelector('#add-point').onclick=()=>{
    if (editingPoints.length>=MAX_POINTS){warn('Maximum 24 points');return;}
    const base=selected()?.minute ?? 720;
    let minute=-1;
    for (let i=1;i<=288;i++) {
      const candidate=(Math.floor(base/5)*5+i*5)%1440;
      if (!editingPoints.some(p=>p.minute===candidate)) {minute=candidate;break;}
    }
    if (minute<0){warn('Aucune heure disponible');return;}
    const brightness=Math.round(interpolation(editingPoints,minute));
    editingPoints.push({minute,brightness:Math.min(100,Math.max(1,brightness))});
    selectedMinute=minute;
    setDirty();renderPointRows();renderChart();
  };
  const cancelButton=document.querySelector('#cancel-profile');
  if (cancelButton) cancelButton.onclick=()=>{
    editingPoints=clone(savedPoints);
    profileDirty=false;
    selectedMinute=editingPoints[0]?.minute ?? null;
    renderPointRows();renderChart();
    showToast('Modifications annulées');
  };
  document.querySelector('#save-profile').onclick=()=>safe(async()=>{
    if (!profileDirty || saving || !selectedId) return;
    const points=validate(readPoints());
    saving=true;updateIndicators();
    try {
      await api(`/api/profile/${encodeURIComponent(selectedId)}`,'PUT',{points});
      savedPoints=clone(points);
      profileDirty=false;
      showToast('Courbe enregistrée');
      await loadProfile();
      await refresh();
    } finally {saving=false;updateIndicators();}
  });

  // Éviter de perdre la courbe lors d'un changement de lampe ou d'onglet.
  const mayLeave=()=>!profileDirty || window.confirm('Cette courbe contient des modifications non enregistrées. Les abandonner ?');
  const discard=()=>{if(profileDirty){editingPoints=clone(savedPoints);profileDirty=false;selectedMinute=editingPoints[0]?.minute??null;renderPointRows();renderChart();}};
  lampSelector.onchange=e=>{
    if(!mayLeave()){e.target.value=selectedId;return;}
    discard();selectedId=e.target.value;loadProfile();
  };
  document.querySelector('.nav')?.addEventListener('click',e=>{
    const btn=e.target.closest?.('.nav-item');
    if(!btn || btn.dataset.tab==='profiles' || activeTab!=='profiles')return;
    if(!mayLeave()){e.stopImmediatePropagation();e.preventDefault();return;}
    discard();
  },true);
  window.addEventListener('beforeunload',e=>{if(profileDirty){e.preventDefault();e.returnValue='';}});

  const simToggle=document.querySelector('#v051-simulation-toggle');
  if (simToggle) simToggle.onclick=()=>{
    const open=document.body.classList.toggle('v051-show-simulator');
    simToggle.setAttribute('aria-expanded',String(open));
    simToggle.textContent=open?'Masquer la simulation':'Afficher la simulation et l’horloge';
  };
  // Le rendu initial sera aussi déclenché par la requête /api/profile.
  updateIndicators();
})();
