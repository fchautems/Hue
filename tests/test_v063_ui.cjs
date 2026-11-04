const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'v063.js'), 'utf8');

async function scenario({dirty = false, rgbDirty = false, confirm = true, switchTarget = false,
                         sourceId = 'couloir', requestError = false} = {}) {
  const calls = [], events = [], handlers = {};
  const curveButton = {disabled: false};
  const source = {value: sourceId, addEventListener() {}};
  const lamp = {
    value: 'hall',
    options: [{value:'hall', textContent:'Hall'}, {value:'couloir', textContent:'Couloir'}],
    addEventListener() {}
  };
  const help = {textContent: ''};
  let button = null;
  const row = {
    querySelector(sel) {
      if (sel === '#v062-copy-source') return source;
      if (sel === '#v062-copy') return curveButton;
      if (sel === 'small') return help;
      return null;
    },
    insertBefore(node, anchor) { assert.equal(anchor, help); button = node; }
  };
  const win = {
    confirm(message) { events.push('confirm'); assert.match(message, /couleurs automatiques/);
      if (switchTarget) ctx.selectedId = 'autre';
      return confirm;
    },
    HueProfiles: {hasUnsaved: () => dirty, reload: async () => {events.push('profiles-reload');}},
    HueRGB: {hasChanges: () => rgbDirty, reloadIfClean: () => {events.push('rgb-reload');}}
  };
  const ctx = {
    window: win, selectedId: 'hall',
    document: {
      querySelector: selector => selector === '#profile-light' ? lamp
        : selector === '#tab-profiles .v062-copy-row' ? row : null,
      createElement: () => ({addEventListener(type, fn) {handlers[type] = fn;}})
    },
    MutationObserver: class {observe() {}},
    safe: async fn => {try {await fn();} catch (e) {events.push('error:' + e.message);}},
    api: async (url, method, data) => {calls.push({url, method, data});
      if (requestError) throw Error('Erreur simulée'); return {};
    },
    refresh: async () => {events.push('refresh');},
    showToast: s => {events.push(s);},
    encodeURIComponent
  };
  vm.runInNewContext(src, ctx);
  assert.ok(button, 'bouton inséré');
  assert.equal(help.textContent.includes('luminosité seule'), true);
  await handlers.click();
  return {calls, events, button, curveButton};
}
(async () => {
  const ok = await scenario();
  assert.equal(ok.calls.length, 1);
  assert.equal(ok.calls[0].url, '/api/profile/copy/hall');
  assert.equal(ok.calls[0].method, 'POST');
  assert.equal(ok.calls[0].data.source_uid, 'couloir');
  assert.ok(ok.events.includes('profiles-reload'));
  assert.ok(ok.events.includes('rgb-reload'));
  assert.equal(ok.curveButton.disabled, false);
  for (const opts of [
    {dirty: true}, {rgbDirty: true}, {confirm: false}, {switchTarget: true},
    {sourceId: 'hall'}
  ]) {
    const result = await scenario(opts);
    assert.equal(result.calls.length, 0, JSON.stringify(opts));
  }
  const fail = await scenario({requestError:true});
  assert.equal(fail.button.disabled, false, 'bouton libéré même en erreur');
  assert.ok(fail.events.some(e=>e.includes('Erreur simulée')));
  console.log('7 scénarios OK : profil complet, brouillons, annulation, sélection et erreur.');
})().catch(error => {console.error(error);process.exit(1);});
