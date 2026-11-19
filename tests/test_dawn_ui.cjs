const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/dawn.js'), 'utf8');

(async () => {
  const elements = new Map();
  const select = id => {
    if (!elements.has(id)) elements.set(id, {
      events: {}, options: [], value: '', textContent: '',
      addEventListener(type, listener) { this.events[type] = listener; },
      replaceChildren(...options) { this.options = options; },
    });
    return elements.get(id);
  };
  const form = select('#dawn-form');
  form.elements = ['#dawn-enabled', '#dawn-light', '#dawn-time', '#dawn-color',
    '#dawn-minutes', '#dawn-brightness', '#dawn-save', '#dawn-sync'].map(select);
  const calls = [];
  const window = {location: {href: 'http://raspberry.local/'}};
  const config = {enabled: true, light_id: 'light-0', wake_time: '', color: '#ff7700',
    minutes: 25, brightness: 65, next_alarm_at: null, time_zone: 'Europe/Zurich'};
  vm.runInNewContext(source, {
    window, $: select, navigator: {userAgent: 'HueLabAndroid/0.2'}, activeTab: 'dashboard',
    Option: class { constructor(text, value) { Object.assign(this, {text, value}); } },
    api: async (url, method, data) => {
      calls.push({url, method});
      if (method === 'PUT') Object.assign(config, data, {
        next_alarm_at: data.wake_time ? Date.parse('2026-11-20T05:20:00Z') : null
      });
      return {...config};
    },
    showToast() {},
  });

  window.HueDawn.refresh([{id: 'light-0', name: 'Chambre', capabilities: {color: true, dimming: true}}]);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(select('#dawn-sync').hidden, false);
  for (const time of ['', '06:20']) {
    select('#dawn-time').value = time;
    form.events.input();
    await form.events.submit({preventDefault() {}});
    assert.equal(window.location.href, 'http://raspberry.local/', 'save must never invoke Android');
    assert.equal(select('#dawn-sync').hidden, Boolean(time));
  }
  assert.deepEqual(calls, [
    {url: '/api/dawn', method: undefined},
    {url: '/api/dawn', method: 'PUT'},
    {url: '/api/dawn', method: 'PUT'},
  ]);
  assert.match(select('#dawn-status').textContent, /06:20.*05:55/);
  select('#dawn-time').value = '';
  form.events.input();
  select('#dawn-sync').events.click();
  assert.equal(window.location.href, 'huelab://sync-alarm', 'only the explicit button invokes Android');
  console.log('Réveil Web et WebView Android simulée : Enregistrer reste local au Raspberry.');
})().catch(error => {console.error(error);process.exit(1);});
