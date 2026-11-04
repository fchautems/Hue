const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const code = fs.readFileSync(path.join(__dirname, "..", "static", "presence.js"), "utf8");

const all = Array.from({length: 95}, (_, i) => ({
  detected_at: "2026-11-04T10:15:00+01:00",
  light_name: i === 0 ? "<script>injection</script>" : "Lampe " + i,
  event: i % 2 ? "light_off" : "light_on"
}));
const buttons = {};
let onTimer = null;
const fetches = [];
const body = {
  rows: [],
  replaceChildren() {this.rows = [];},
  appendChild(row) {this.rows.push(row);}
};
const elements = {
  "#presence-rows": body,
  "#presence-status": {textContent:""},
  "#presence-page-status": {textContent:""},
  "#tab-presence": {classList:{contains: () => false}}
};
for (const id of ["#presence-refresh", "#presence-older", "#presence-newer"]) {
  buttons[id] = {disabled:false, addEventListener(type, callback) {assert.equal(type, "click");this.click=callback;}};
  elements[id] = buttons[id];
}
const ctx = {
  window: {},
  document: {
    querySelector: sel => elements[sel],
    createElement: tag => tag === "tr"
      ? {cells:[], appendChild(td) {this.cells.push(td);}}
      : {textContent:"", colSpan:1}
  },
  setInterval: (callback, ms) => {assert.equal(ms,15000);onTimer=callback;},
  fetch: async (url, opts) => {
    assert.equal(opts.cache, "no-store");
    fetches.push(url);
    const offset = Number(/offset=(\d+)/.exec(url)[1]);
    const limit = Number(/limit=(\d+)/.exec(url)[1]);
    const records = [...all].reverse().slice(offset, offset + limit);
    return {ok:true, json:async()=>({ok:true, data:records})};
  }
};
vm.runInNewContext(code,ctx);
(async () => {
  await ctx.window.HuePresence.refresh();
  assert.match(fetches.at(-1), /limit=41&offset=0/);
  assert.equal(body.rows.length, 40);
  assert.equal(body.rows[0].cells[1].textContent, "Lampe 94");
  assert.equal(buttons["#presence-newer"].disabled, true);
  assert.equal(buttons["#presence-older"].disabled, false);
  await buttons["#presence-older"].click();
  assert.match(fetches.at(-1), /offset=40/);
  assert.equal(elements["#presence-page-status"].textContent, "Page 2");
  assert.equal(body.rows[0].cells[1].textContent,"Lampe 54");
  await buttons["#presence-older"].click();
  assert.match(fetches.at(-1), /offset=80/);
  assert.equal(body.rows.length, 15);
  assert.equal(body.rows.at(-1).cells[1].textContent, "<script>injection</script>");
  assert.equal(buttons["#presence-older"].disabled, true);
  const count = fetches.length;
  onTimer();
  await Promise.resolve();
  assert.equal(fetches.length,count, "pas de refresh automatique dans les archives");
  await buttons["#presence-newer"].click();
  assert.match(fetches.at(-1), /offset=40/);
  await buttons["#presence-refresh"].click();
  assert.match(fetches.at(-1), /offset=0/);
  onTimer();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(fetches.at(-1), /offset=0/);
  console.log("Historique v0.6.4 : 8 contrôles fonctionnels réussis.");
})().catch(e=>{console.error(e);process.exit(1);});
