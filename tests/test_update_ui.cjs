"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");

const text = fs.readFileSync("static/app.js", "utf8");
const start = text.indexOf("function renderUpdateChanges(status){");
const end = text.indexOf("\nasync function refreshUpdater", start);
assert.ok(start >= 0 && end > start, "release notes renderer must be present");

const nodes = {
  "#update-changes-title": {textContent: ""},
  "#update-changes-type": {textContent: ""},
  "#update-changes-list": {
    children: [],
    replaceChildren(){this.children=[]},
    appendChild(item){this.children.push(item)}
  }
};
const renderer = new Function("$", "document",
  text.slice(start, end) + "\nreturn renderUpdateChanges;")(
  name => nodes[name], {createElement: tag => ({tag, textContent:""})});

renderer({available:true, change_kind:"internal", changes:["Tests solaires", "Documentation"]});
assert.match(nodes["#update-changes-type"].textContent,/aucune différence visuelle/);
assert.equal(nodes["#update-changes-list"].children.length,2);
assert.equal(nodes["#update-changes-list"].children[0].textContent,"Tests solaires");

renderer({available:false, last_change_kind:"interface",last_changes:["Nouveau sélecteur"]});
assert.match(nodes["#update-changes-type"].textContent,/interface/);
assert.equal(nodes["#update-changes-list"].children[0].textContent,"Nouveau sélecteur");

renderer({available:false,latest_note:"**Interface** plus claire",last_changes:[]});
assert.match(nodes["#update-changes-list"].children[0].textContent,/Interface plus claire/);
assert.equal(nodes["#update-changes-list"].children.length,1);

const html=fs.readFileSync("templates/index.html","utf8");
assert.ok(html.includes("id=\"update-changes-list\""));
assert.ok(html.includes("id=\"brand-version\""));
console.log("update UI and release notes regression OK");
