const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const css = fs.readFileSync(path.join(__dirname, '..', 'static', 'v062.css'), 'utf8');
const rule = selector => {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = css.match(new RegExp(escaped + '\\s*\\{([^}]*)\\}'));
  assert.ok(match, 'Missing CSS rule: ' + selector);
  return match[1];
};
for (const selector of ['#tab-profiles .v062-copy-row select', '#tab-profiles .v062-copy-row button']) {
  const value = rule(selector).match(/min-height:\\s*(\\d+)px/);
  assert.ok(value && Number(value[1]) >= 44, selector + ' must be >=44px tall');
}
assert.match(css, /\.v062-copy-row select:focus-visible/);
assert.match(css, /\.v062-copy-row button:focus-visible/);
assert.match(css, /outline:3px solid/);
console.log('Profile copy touch targets and keyboard focus OK.');
