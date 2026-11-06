const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const src = fs.readFileSync(require('node:path').join(__dirname,'..','static','v062.js'),'utf8');
async function runCase(type, {unsaved=false, confirmed=true, changeTarget=false, changeSource=false}={}) {
  const calls = [];
  const status = [];
  const handlers={};
  const button={disabled:false,addEventListener:(key,fn)=>{handlers[key]=fn}};
  const source={value:'',options:[],replaceChildren(...opts){this.options=opts;this.value=opts[0]?.value||'';}};
  const row={className:'',set innerHTML(_) {},querySelector:s=>s==='#v062-copy-source'?source:button};
  const lamp={value:'hall',options:[{value:'hall',textContent:'Hall'},{value:'couloir',textContent:'Couloir'}],addEventListener() {}};
  const details={children:[],append(...nodes){this.children.push(...nodes)}};
  const bar={appendChild(x){assert.equal(x,details);assert.equal(x.children[1],row)}};
  const win={confirm(){return confirmed},HueProfiles:{hasUnsaved:()=>unsaved,reload:async()=>{calls.push(['reload'])}},HueRGB:{hasChanges:()=>false,reloadIfClean:()=>{calls.push(['rgbReload'])}}};
  const ctx={
    window:win,selectedId:'hall',document:{querySelector:s=>s==='#profile-light'?lamp:s==='#tab-profiles .v061-lamp-bar'?bar:null,createElement:tag=>tag==='div'?row:tag==='details'?details:{value:'',textContent:''}},
    MutationObserver:class{observe(){}},
    api:async(url,method='GET',data)=>{calls.push([method,url,data]);if(changeTarget)ctx.selectedId='autre';if(changeSource)source.value='autre';if(url==='/api/profile/simple/couloir'&&method==='GET')return {type,params:{wake:350}};if(url==='/api/profile/couloir'&&method==='GET')return [{minute:0,brightness:10},{minute:720,brightness:80}];return {};},
    safe:async fn=>{try{await fn()}catch(e){status.push(e.message)}},
    refresh:async()=>{calls.push(['refresh'])},showToast:msg=>status.push(msg),
    encodeURIComponent,
  };
  vm.runInNewContext(src,ctx);
  await handlers.click();
  return {calls,status,button};
}
(async()=>{
 const simple=await runCase('simple');
 assert.deepEqual(simple.calls.filter(a=>a[0]==='PUT').map(a=>a[1]),['/api/profile/simple/hall']);
 assert.ok(simple.calls.some(a=>a[0]==='reload'));
 const custom=await runCase('custom');
 assert.deepEqual(custom.calls.filter(a=>a[0]==='PUT').map(a=>a[1]),['/api/profile/hall']);
 const dirty=await runCase('simple',{unsaved:true});
 assert.ok(!dirty.calls.some(a=>a[0]==='PUT'));
 const cancel=await runCase('simple',{confirmed:false});
 assert.ok(!cancel.calls.some(a=>a[0]==='PUT'));
 const changed=await runCase('simple',{changeTarget:true});
 assert.ok(!changed.calls.some(a=>a[0]==='PUT'));
 const sourceChanged=await runCase('simple',{changeSource:true});
 assert.ok(!sourceChanged.calls.some(a=>a[0]==='PUT'));
 console.log('6 scénarios OK : Simple, Personnalisée, brouillon, annulation, changement de lampe et de source.');
})().catch(e=>{console.error(e);process.exit(1)});
