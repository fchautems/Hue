/* Solar preview only. No access to Hue commands, modes or saved lamp profiles. */
'use strict';
(() => {
  const $ = id => document.getElementById('solar-' + id);
  if (!$('form')) return;
  const places = {muids: [46.46, 6.22], nyon: [46.3833, 6.2333], lausanne: [46.5197, 6.6323]};
  let result = null;
  let generation = 0;
  const minute = value => {
    if (!/^\d{2}:\d{2}$/.test(value)) return null;
    const [h, m] = value.split(':').map(Number);
    return h < 24 && m < 60 ? h * 60 + m : null;
  };
  const duration = minutes => `${Math.floor(minutes / 60)} h ${String(Math.round(minutes % 60)).padStart(2, '0')}`;
  const localDay = zone => new Intl.DateTimeFormat('sv-SE', {timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
  function save() {
    try {
      localStorage.setItem('hue-solar-preview-v1', JSON.stringify(Object.fromEntries(
        ['place', 'lat', 'lon', 'zone', 'wake', 'bed'].map(id => [id, $(id).value]))));
    } catch (_) { /* Preview remains usable if browser storage is disabled. */ }
  }
  function location() {
    const coordinates = places[$('place').value];
    return coordinates ? {latitude: coordinates[0], longitude: coordinates[1], tz: 'Europe/Zurich'}
      : {latitude: $('lat').value, longitude: $('lon').value, tz: $('zone').value.trim()};
  }
  function invalidate() {
    generation++;
    result = null;
    $('results').hidden = true;
    $('status').textContent = 'Choisis « Voir cette journée » pour actualiser l’aperçu.';
  }
  function routine() {
    if (!result) return;
    const wake = minute($('wake').value), bed = minute($('bed').value);
    for (const [id, value] of [['wake', wake], ['bed', bed]]) {
      const marker = $(id + '-marker');
      marker.hidden = value === null;
      if (value !== null) marker.style.left = `${value / 1440 * 100}%`;
    }
    const rise = result.sunrise_minute, set = result.sunset_minute;
    if (rise === null || set === null || wake === null || bed === null) {
      $('comparison').textContent = 'Les repères de ton rythme restent indépendants des heures solaires.';
    } else {
      const gap = Math.round(Math.abs(wake - rise));
      const bedGap = Math.round(Math.abs(bed - set));
      $('comparison').textContent = `Ton réveil est ${duration(gap)} ${wake < rise ? 'avant' : 'après'} le lever du soleil. Ton coucher est ${duration(bedGap)} ${bed < set ? 'avant' : 'après'} le coucher du soleil.`;
    }
    save();
  }
  async function load() {
    const token = ++generation;
    result = null;
    $('results').hidden = true;
    $('status').textContent = 'Calcul de la journée…';
    try {
      const params = new URLSearchParams({...location(), day: $('date').value});
      const response = await fetch('/api/solar/preview?' + params);
      const payload = await response.json();
      if (token !== generation) return;
      if (!response.ok || !payload.ok) throw Error(payload.error || 'Vérifie la date, le lieu et le fuseau horaire.');
      result = payload.data;
      const format = iso => iso ? new Intl.DateTimeFormat('fr-CH', {timeZone: result.timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).format(new Date(iso)) : '—';
      $('rise').textContent = format(result.sunrise);
      $('set').textContent = format(result.sunset);
      $('duration').textContent = result.daylight_minutes === null ? '—' : duration(result.daylight_minutes);
      const rise = result.sunrise_minute, set = result.sunset_minute;
      const band = $('daylight');
      band.hidden = rise === null || set === null || set <= rise;
      $('timeline').hidden = band.hidden;
      $('scale').hidden = band.hidden;
      if (!band.hidden) {
        band.style.left = `${rise / 1440 * 100}%`;
        band.style.width = `${(set - rise) / 1440 * 100}%`;
      }
      $('timeline').setAttribute('aria-label', `Lever ${format(result.sunrise)}, coucher ${format(result.sunset)}. Plage claire : jour naturel, fond sombre : nuit.`);
      $('results').hidden = false;
      $('status').textContent = (rise === null || set === null)
        ? `Lever ou coucher absent à cette date et à ce lieu (région polaire). ${result.timezone}.`
        : `Heures locales · ${result.timezone} · aperçu sans commande de lampe.`;
      routine();
    } catch (error) {
      if (token !== generation) return;
      result = null;
      $('results').hidden = true;
      $('status').textContent = 'Aperçu indisponible. ' + error.message;
    }
  }
  try {
    const saved = JSON.parse(localStorage.getItem('hue-solar-preview-v1') || 'null');
    if (saved && typeof saved === 'object') {
      for (const id of ['place', 'lat', 'lon', 'zone', 'wake', 'bed']) {
        if (typeof saved[id] === 'string') $(id).value = saved[id];
      }
    }
  } catch (_) { /* Ignore stale or unavailable browser storage. */ }
  if (!places[$('place').value] && $('place').value !== 'custom') $('place').value = 'muids';
  function toggleCoordinates() {
    const custom = $('place').value === 'custom';
    $('coordinates').classList.toggle('hidden', !custom);
    for (const id of ['lat', 'lon', 'zone']) $(id).disabled = !custom;
  }
  toggleCoordinates();
  $('place').addEventListener('change', () => { toggleCoordinates(); invalidate(); save(); });
  for (const id of ['date', 'lat', 'lon', 'zone']) $(id).addEventListener('input', invalidate);
  for (const id of ['wake', 'bed']) $(id).addEventListener('input', routine);
  $('form').addEventListener('submit', event => { event.preventDefault(); load(); });
  $('today').addEventListener('click', () => {
    try { $('date').value = localDay(location().tz); load(); }
    catch (_) { invalidate(); $('status').textContent = 'Fuseau horaire inconnu.'; }
  });
  try { $('date').value = localDay(location().tz); }
  catch (_) { $('date').value = localDay('Europe/Zurich'); }
  globalThis.HueSolarPreview = {context: () => result ? {...location(), day: result.day} : null};
  load();
})();
