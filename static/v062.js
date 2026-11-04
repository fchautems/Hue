/* Hue Lab v0.6.2 — copier une courbe enregistrée entre deux lampes. */
"use strict";
(() => {
  const lamp = document.querySelector('#profile-light');
  const bar = document.querySelector('#tab-profiles .v061-lamp-bar');
  if (!lamp || !bar) return;

  const row = document.createElement('div');
  row.className = 'v062-copy-row';
  row.innerHTML = `<label for="v062-copy-source">Reprendre la courbe de</label>
    <select id="v062-copy-source" class="field" aria-label="Lampe source"></select>
    <button id="v062-copy" type="button" class="btn muted">Copier vers cette lampe</button>
    <small>Copie la courbe de luminosité active. Les couleurs, le mode Manuel/Auto et Vacances ne changent pas.</small>`;
  bar.appendChild(row);
  const source = row.querySelector('#v062-copy-source');
  const button = row.querySelector('#v062-copy');
  let busy = false;

  function syncSources() {
    const previous = source.value;
    const others = [...lamp.options].filter(option => option.value && option.value !== lamp.value);
    source.replaceChildren(...others.map(option => {
      const copy = document.createElement('option');
      copy.value = option.value;
      copy.textContent = option.textContent;
      return copy;
    }));
    source.value = others.some(option => option.value === previous) ? previous : (others[0]?.value || '');
    button.disabled = busy || !source.value || !lamp.value;
  }

  new MutationObserver(syncSources).observe(lamp, {childList: true});
  lamp.addEventListener('change', syncSources);
  syncSources();

  button.addEventListener('click', () => safe(async () => {
    if (busy || !source.value || !selectedId) return;
    if (window.HueProfiles?.hasUnsaved() || window.HueRGB?.hasChanges()) {
      throw Error('Enregistre ou annule les modifications en cours avant de copier une courbe.');
    }
    const fromId = source.value;
    const toId = selectedId;
    if (fromId === toId) return;
    const fromName = [...lamp.options].find(o => o.value === fromId)?.textContent || 'la source';
    const toName = [...lamp.options].find(o => o.value === toId)?.textContent || 'la destination';
    if (!window.confirm(`Copier la courbe de « ${fromName} » vers « ${toName} » ? La courbe active de destination sera remplacée.`)) return;
    busy = true;
    button.disabled = true;
    try {
      const data = await api(`/api/profile/simple/${encodeURIComponent(fromId)}`);
      if (selectedId !== toId || source.value !== fromId) throw Error('La sélection a changé. Copie annulée.');
      if (data.type === 'simple') {
        await api(`/api/profile/simple/${encodeURIComponent(toId)}`, 'PUT', {params: data.params});
      } else if (data.type === 'custom') {
        const points = await api(`/api/profile/${encodeURIComponent(fromId)}`);
        if (selectedId !== toId) throw Error('La lampe sélectionnée a changé. Copie annulée.');
        await api(`/api/profile/${encodeURIComponent(toId)}`, 'PUT', {points});
      } else {
        throw Error('Type de courbe source inconnu.');
      }
      if (selectedId === toId) {
        await window.HueProfiles?.reload();
        window.HueRGB?.reloadIfClean(toId);
        await refresh();
      }
      showToast('Courbe copiée. Tu peux la tester avec l’horloge accélérée.');
    } finally {
      busy = false;
      syncSources();
    }
  }));
})();
