const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const src = fs.readFileSync(path.join(__dirname, '..', 'static', 'v063.js'), 'utf8');

class Option {
  constructor(textContent, value) { Object.assign(this, {textContent, value}); }
}

async function scenario({dirty = false, rgbDirty = false, confirm = true,
                         destination = 'couloir', requestError = false} = {}) {
  const calls = [], events = [];
  const details = {open: true};
  const button = {closest: () => details, addEventListener(type, handler) {this[type] = handler;}};
  const select = (value, options) => ({
    value, options,
    get selectedOptions() {return this.options.filter(option => option.value === this.value);},
    addEventListener(type, handler) {this[type] = handler;},
    replaceChildren(...options) {this.options = options;}
  });
  const lamp = select('hall', [new Option('Hall','hall'), new Option('Couloir','couloir')]);
  const target = select('', []);
  const ctx = {
    Option, selectedId: 'hall',
    window: {
      confirm(message) {events.push('confirm'); assert.match(message, /« Hall » vers « Couloir »/); return confirm;},
      HueProfiles: {hasUnsaved: () => dirty},
      HueRGB: {hasChanges: () => rgbDirty}
    },
    document: {querySelector: id => ({
      '#profile-light': lamp, '#profile-copy-target': target, '#v063-copy-full': button
    })[id]},
    MutationObserver: class {observe() {}},
    safe: async fn => {try {await fn();} catch (e) {events.push('error:' + e.message);}},
    api: async (url, method, data) => {
      calls.push({url, method, source: data.source_uid});
      assert.equal(button.disabled,true,'one copy at a time');
      if (requestError) throw Error('Erreur simulée');
    },
    refresh: async () => {events.push('refresh');},
    showToast: message => {events.push(message);},
    encodeURIComponent
  };
  vm.runInNewContext(src, ctx);
  assert.deepEqual(Array.from(target.options, option => option.value), ['', 'couloir']);
  assert.equal(button.disabled,true);
  target.value = destination;
  target.change();
  await button.click();
  return {calls, events, button, details};
}

(async () => {
  const ok = await scenario();
  assert.deepEqual(ok.calls, [{url:'/api/profile/copy/couloir',method:'POST',source:'hall'}]);
  assert.ok(ok.events.includes('refresh'));
  assert.equal(ok.details.open,false);
  for (const opts of [{dirty:true}, {rgbDirty:true}, {confirm:false}, {destination:'hall'}, {destination:''}]) {
    const result = await scenario(opts);
    assert.equal(result.calls.length,0,JSON.stringify(opts));
  }
  const fail = await scenario({requestError:true});
  assert.equal(fail.button.disabled,false,'retry after error');
  assert.ok(fail.events.some(event => event.includes('Erreur simulée')));
  console.log('Copie complète : source affichée, confirmation, brouillons et reprise après erreur.');
})().catch(error => {console.error(error);process.exit(1);});
