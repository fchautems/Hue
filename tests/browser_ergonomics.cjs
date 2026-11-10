// Real browser, actual API and simulated bridge. Never contacts the user's lamps.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({locale:'fr-CH'});
 const errors=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(!['GET','HEAD'].includes(r.method()))writes.push({url:new URL(r.url()).pathname,data:r.postDataJSON()});});
 await page.route('**/api/update/status',r=>r.fulfill({json:{ok:true,data:{configured:true,installed:'old123456',remote:'new123456',available:true,changes:['Navigation revue'],change_kind:'interface'}}}));
 await page.goto('http://127.0.0.1:8766');
 await page.locator('.light-card').first().waitFor({state:'attached'});
 const nav=tab=>page.locator('.nav [data-tab="'+tab+'"]');
 const check=async(condition,msg)=>assert.ok(await condition,msg);
 await check(page.locator('#update-badge').isVisible(),'permanent update badge');
 assert.equal(writes.length,0,'opening the app must not command lamps');
 const room=page.locator('.room-card').filter({has:page.getByRole('heading',{name:'Couloir',exact:true})});
 await room.waitFor();
 assert.equal(await room.locator('.room-lamp').count(),2);
 const zone=page.locator('.room-card').filter({has:page.getByRole('heading',{name:'Étage',exact:true})});
 assert.equal(await zone.locator('.room-lamp').count(),3);
 for(const width of [320,393]){
  await page.setViewportSize({width,height:680});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollHeight>innerHeight),false,'room home fits the phone');
  assert.ok(await page.evaluate(()=>[...document.querySelectorAll('.room-card button')].every(
    button=>button.getBoundingClientRect().height>=48)),'touch targets at least 48 px high');
 }
 await page.screenshot({path:'/tmp/hue-ergonomics-rooms.png'});
 await room.getByRole('button',{name:'Commande de groupe · Couloir'}).click();
 await page.waitForFunction(()=>state.lights.slice(0,2).every(l=>!l.on));
 assert.deepEqual(writes.splice(0).map(r=>r.url).sort(),['/api/light/light-0/switch','/api/light/light-1/switch']);
 await room.getByRole('button',{name:'Salon',exact:true}).click();
 await page.waitForFunction(()=>state.lights[1].on);
 assert.deepEqual(writes.splice(0).map(r=>r.url),['/api/light/light-1/switch']);
 await room.getByRole('button',{name:'Entrée',exact:true}).click();
 await page.waitForFunction(()=>state.lights[0].on);
 writes.splice(0);

 // Layout and reachable daily activities at phone/tablet/desktop widths.
 for(const width of [320,390,1320]){
  await page.setViewportSize({width,height:1000});
  for(const tab of ['dashboard','profiles','presence','settings','updates']){
   await nav(tab).click();
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(overflow,false,`${tab} overflow at ${width}`);
   if(tab==='profiles'){
    await check(page.locator('#clock-svg').isVisible(),'clock visible');
    await check(page.locator('#profile-chart').isVisible(),'curve visible');
   }
  }
  await nav('profiles').click();
  await page.screenshot({path:`/tmp/hue-ergonomics-${width}.png`,fullPage:true});
 }
 // Clock source has one location and is absent from technical panels.
 assert.equal(await page.locator('#clock-source').count(),1);
 await page.locator('#clock-source').selectOption('accelere');
 await page.waitForFunction(()=>state.clock_mode==='accelere');
 await check(page.locator('#sim-play').isVisible(),'pause is visible next to the seek slider');
 await page.waitForFunction(()=>state.simulation.running);
 await page.locator('#sim-play').click();
 await page.waitForFunction(()=>!state.simulation.running);
 await page.locator('#seek-time').fill('14:37');
 await page.waitForFunction(()=>state.simulation.minute===877&&!state.simulation.running&&!document.querySelector('#time-slider').disabled);
 assert.equal(await page.locator('#time-slider').inputValue(),'877');
 await page.locator('#sim-play').click();
 await page.waitForFunction(()=>state.simulation.running);
 await page.locator('#time-slider').fill('510');
 await page.waitForFunction(()=>state.simulation.minute===510&&!state.simulation.running&&!document.querySelector('#seek-time').disabled);
 assert.equal(await page.locator('#seek-time').inputValue(),'08:30');
 await page.locator('#v051-simulation-toggle').click();
 await check(page.locator('#sim-play').isEnabled(),'simulation can run');
 await page.locator('#sim-play').click();
 await page.waitForFunction(()=>state.simulation.running);
 await page.locator('#sim-play').click();
 await page.waitForFunction(()=>!state.simulation.running);
 await page.locator('#sim-speed').selectOption('60');
 await page.waitForFunction(()=>state.simulation.seconds_per_day===60);
 await page.locator('#clock-source').selectOption('reel');
 await page.waitForFunction(()=>state.clock_mode==='reel');
 // Custom curve: cancellation, navigation protection and explicit save.
 await page.locator('#v051-level-number').fill('27');
 await page.locator('#v051-level-number').press('Tab');
 await page.waitForFunction(()=>profileDirty);
 page.once('dialog',d=>d.dismiss());
 await nav('updates').click();
 assert.equal(await page.evaluate(()=>activeTab),'profiles','update shortcut respects dirty curve');
 await page.locator('#cancel-profile').click();
 await page.locator('#v051-level-number').fill('28');
 await page.locator('#v051-level-number').press('Tab');
 await page.locator('#save-profile').click();
 await page.waitForFunction(()=>!profileDirty);
 assert.ok(writes.some(r=>r.url==='/api/profile/light-0'&&r.data.points));
 // Simple profile and shared lamp selection; edits remain guarded.
 await page.locator('.v052-mode[data-type="simple"]').click();
 await page.locator('#v052-save').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('actif'));
 await page.locator('#v052-wake').fill('06:30');
 page.once('dialog',d=>d.dismiss());
 await nav('settings').click();
 assert.equal(await page.evaluate(()=>activeTab),'profiles');
 await page.locator('#v052-cancel').click();
 // Saved server target must stay authoritative across both periodic callbacks,
 // simple/custom editor switches and unsaved drafts (old UI alternated values).
 await page.locator('#clock-source').selectOption('accelere');
 await page.waitForFunction(()=>state.clock_mode==='accelere');
 await page.evaluate(async()=>{
   await api('/api/clock-mode','POST',{mode:'accelere'});
   await api('/api/simulation','POST',{minute:720,running:false});
 });
 // refresh() may already be awaiting a response sampled before the pause.
 await page.waitForFunction(()=>!state.simulation.running&&Math.abs(state.minute-720)<.01);
 const activeTarget=await page.evaluate(()=>Math.round(state.lights.find(l=>l.id===selectedId).target));
 const expectTarget=`Cible active ${activeTarget} %`;
 await page.evaluate(()=>{
   window.targetValues=[];
   window.targetObserver=new MutationObserver(()=>window.targetValues.push(document.querySelector('#profile-target').textContent));
   window.targetObserver.observe(document.querySelector('#profile-target'),{childList:true,subtree:true,characterData:true});
 });
 await page.locator('#v052-max_brightness').fill('92');
 await page.waitForTimeout(2300);
 await page.locator('.v052-mode[data-type="custom"]').click();
 assert.equal(await page.locator('.profile-card').getAttribute('data-v052-view'),'simple','field edits remain guarded');
 await page.locator('#v052-cancel').click();
 await page.locator('.v052-mode[data-type="custom"]').click();
 await page.waitForTimeout(1100);
 const values=await page.evaluate(()=>{window.targetObserver.disconnect();return window.targetValues;});
 assert.ok(values.length>5,'sample several timer updates');
 assert.ok(values.every(v=>v===expectTarget),`conflicting target writers: ${values.join(', ')}`);
 // Return to the saved simple profile; its cancel button is hidden in custom view.
 await page.locator('.v052-mode[data-type="simple"]').click();
 await page.waitForFunction(()=>!window.HueProfiles.hasUnsaved());
 await page.locator('#clock-source').selectOption('reel');
 await page.waitForFunction(()=>state.clock_mode==='reel');
 // Colors remain editable; cancelling a navigation retains the draft.
 await page.locator('#profile-colors > summary').click();
 await page.waitForFunction(()=>document.querySelector('#rgb-status').textContent.includes('RGB')||document.querySelector('#rgb-status').textContent.includes('Configuration'));
 await page.locator('#rgb-manual').click();
 await page.locator('#rgb-presets button[data-h="0"]').click();
 page.once('dialog',d=>d.dismiss());
 await nav('presence').click();
 assert.equal(await page.evaluate(()=>activeTab),'profiles');
 await page.locator('#rgb-save').click();
 await page.waitForFunction(()=>!window.HueRGB.hasChanges());
 assert.ok(writes.some(r=>r.url==='/api/rgb/light-0'&&r.data.manual));
 await page.locator('#profile-light').selectOption('light-1');
 await page.waitForFunction(()=>selectedId==='light-1'&&window.HueRGB.currentId()==='light-1');
 // Daily solar settings: date is preview-only; activation persists the rhythm.
 await page.locator('.v052-mode[data-type="solar"]').click();
 await page.locator('#solar-wake').fill('05:15');
 await page.locator('#solar-bed').fill('22:30');
 await page.locator('#solar-date').fill('2026-11-06');
 await page.waitForFunction(()=>document.querySelector('#solar-draft-hours').textContent.includes('04:45–05:15'));
 await page.locator('#solar-save').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('Soleil actif'));
 const solarSaved=await page.evaluate(()=>api('/api/profile/solar/light-1'));
 assert.equal(solarSaved.type,'solar');
 assert.equal(solarSaved.config.wake,315);
 assert.equal(solarSaved.config.bed,1350);
 assert.equal('day' in solarSaved.config,false);
 for(const width of [320,390,1320]){
   await page.setViewportSize({width,height:1000});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(80);
   await page.screenshot({path:`/tmp/hue-ergonomics-solar-${width}.png`,fullPage:true});
 }
 // Both copy operations retain their distinct behavior and confirmation.
 await page.locator('.profile-copy > summary').click();
 await page.locator('#v062-copy-source').selectOption('light-0');
 page.once('dialog',d=>d.accept());
 await page.locator('#v063-copy-full').click();
 await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('Profil complet copié'));
 page.once('dialog',d=>d.accept());
 await page.locator('#v062-copy').click();
 await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('Courbe copiée'));
 // Settings and updates are separate destinations, even when returning from History.
 await nav('presence').click();
 await nav('updates').click();
 assert.equal(await page.locator('#tab-updates').isVisible(),true);
 assert.equal(await page.locator('.settings-nav').isVisible(),false);
 assert.deepEqual(await page.locator('.nav [aria-current="page"]').evaluateAll(nodes=>nodes.map(node=>node.dataset.tab)),['updates']);
 // Technical functions live under Settings, without the clock source.
 await nav('settings').click();
 assert.equal(await page.locator('#tab-updates').isVisible(),false);
 assert.deepEqual(await page.locator('.nav [aria-current="page"]').evaluateAll(nodes=>nodes.map(node=>node.dataset.tab)),['settings']);
 await check(page.locator('#clock-source').isHidden(),'no clock source in settings');
 await page.locator('.settings-nav [data-tab="setup"]').click();
 assert.equal(await page.locator('#setup-ip').inputValue(),'10.0.0.12');
 await page.locator('#setup-discover').click();
 await page.waitForFunction(()=>!document.querySelector('#setup-discover').disabled);
 assert.equal(await page.locator('#setup-bridges').isVisible(),false,'one result requires no dropdown');
 await page.locator('#setup-ip').fill('10.0.0.2');
 await page.locator('#setup-discover').click();
 await page.locator('#setup-use-detected').waitFor({state:'visible'});
 assert.equal(await page.locator('#setup-ip').inputValue(),'10.0.0.2','saved IP not overwritten');
 await page.locator('#setup-use-detected').click();
 assert.equal(await page.locator('#setup-ip').inputValue(),'10.0.0.12','explicit one-click use');
 // Typing while fetching survives the delayed discovery response.
 let releaseDiscovery;
 await page.route('**/api/setup/discover',async r=>{await new Promise(resolve=>releaseDiscovery=resolve);await r.fulfill({json:{ok:true,data:{bridges:['10.0.0.2','10.0.0.13']}}});});
 await page.locator('#setup-discover').click();
 await page.waitForFunction(()=>document.querySelector('#setup-discover').disabled);
 await page.locator('#setup-ip').fill('10.0.0.12');
 while(!releaseDiscovery)await new Promise(r=>setTimeout(r,10));
 releaseDiscovery();
 await page.waitForFunction(()=>!document.querySelector('#setup-discover').disabled);
 assert.equal(await page.locator('#setup-ip').inputValue(),'10.0.0.12');
 await check(page.locator('#setup-bridges').isVisible(),'multiple discovered choices');
 await page.locator('#setup-bridges').selectOption('10.0.0.13');
 assert.equal(await page.locator('#setup-ip').inputValue(),'10.0.0.13');
 await page.locator('#setup-ip').fill('10.0.0.12');
 // Association still uses the explicit manual address and preserves button instructions.
 await page.route('**/api/setup/pair',r=>r.fulfill({json:{ok:true,data:{paired:true,ip:'10.0.0.12',lights:3}}}));
 await page.locator('#setup-pair').click();
 await page.waitForFunction(()=>activeTab==='dashboard');
 assert.equal(writes.find(r=>r.url==='/api/setup/pair').data.ip,'10.0.0.12');
 // Dawn settings are saved once, and show the alarm confirmed by the Raspberry.
 await page.setViewportSize({width:320,height:1000});
 await page.locator('#dawn-save').waitFor();
 await page.locator('#dawn-enabled').check();
 await page.locator('#dawn-light').selectOption('light-0');
 await page.locator('#dawn-color').fill('#ff7700');
 await page.locator('#dawn-minutes').fill('25');
 await page.locator('#dawn-brightness').fill('65');
 await page.locator('#dawn-save').click();
 await page.waitForFunction(()=>document.querySelector('#dawn-status').textContent.includes('première synchronisation'));
 assert.deepEqual(writes.find(r=>r.url==='/api/dawn').data,
   {enabled:true, light_id:'light-0', color:'#ff7700', minutes:25, brightness:65});
 await page.evaluate(()=>api('/api/dawn/alarm','PUT',{observed_at:Date.now(),alarm_at:Date.now()+36e5}));
 await page.waitForFunction(()=>document.querySelector('#dawn-status').textContent.includes('Réveil reçu'));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.locator('#dawn-enabled').uncheck();
 await page.locator('#dawn-save').click();
 await page.waitForFunction(()=>document.querySelector('#dawn-status').textContent==='Désactivé.');
 await page.setViewportSize({width:1320,height:1000});
 // Vacations, manual commands, history and advanced diagnostics remain reachable.
 await page.locator('.light-card').first().locator('.switch').click();
 await page.waitForFunction(()=>!state.lights[0].on);
 await page.locator('.light-card').first().locator('.switch').click();
 await page.locator('.light-card').first().locator('[data-control="auto"]').click();
 await page.locator('.light-card').first().locator('.light-rgb').click();
 await check(page.locator('#rgb-wheel').isVisible(),'color shortcut opens disclosure');
 await nav('dashboard').click();
 await page.locator('#vacation-lights input').first().check();
 await page.locator('#vacation-toggle').click();
 await page.waitForFunction(()=>document.querySelector('#vacation-status').textContent==='ACTIF');
 await page.locator('#vacation-test-toggle').click();
 await page.waitForFunction(()=>document.querySelector('#vacation-test-toggle').dataset.running==='true');
 await page.locator('#vacation-test-toggle').click();
 await page.waitForFunction(()=>document.querySelector('#vacation-test-toggle').dataset.running==='false');
 await page.locator('#vacation-toggle').click();
 await page.waitForFunction(()=>document.querySelector('#vacation-status').textContent!=='ACTIF');
 await nav('presence').click();
 await check(page.locator('#presence-rows').isVisible(),'history preserved');
 await nav('settings').click();
 await page.locator('.settings-nav [data-tab="diagnostics"]').click();
 await page.locator('#diag-lights .diag-item').first().waitFor();
 await page.locator('.powerup-btn').first().click();
 await check(page.locator('#powerup-dialog').isVisible(),'powerup dialog');
 await page.locator('#cancel-powerup').click();
 const download=page.waitForEvent('download');
 await page.locator('#export-diag').click();
 assert.ok((await download).suggestedFilename().endsWith('.json'));
 await page.locator('#refresh-logs').click();
 await check(page.locator('#log-display').isVisible(),'logs preserved');
 await nav('updates').click();
 await check(page.locator('#update-apply').isEnabled(),'installation remains accessible');
 // First installation: no made-up IP and association opens inside Settings.
 const first=await browser.newPage();
 first.on('pageerror',e=>errors.push(e.message));
 await first.route('**/api/state',async route=>{
   const response=await route.fetch();const json=await response.json();
   json.needs_setup=true;json.connected=false;json.lights=[];
   await route.fulfill({json});
 });
 await first.route('**/api/setup/status',r=>r.fulfill({json:{ok:true,data:{ip:'',paired:false}}}));
 await first.route('**/api/setup/discover',r=>r.fulfill({json:{ok:true,data:{bridges:['10.0.0.12']}}}));
 await first.goto('http://127.0.0.1:8766');
 await first.waitForFunction(()=>document.querySelector('#setup-ip').value==='10.0.0.12');
 assert.equal(await first.evaluate(()=>activeTab),'setup');
 assert.equal(await first.locator('#setup-bridges').isVisible(),false);
 await first.route('**/api/setup/discover',r=>r.fulfill({status:502,json:{ok:false,error:'Découverte indisponible'}}));
 await first.locator('#setup-ip').fill('10.0.0.99');
 await first.locator('#setup-discover').click();
 await first.waitForFunction(()=>document.querySelector('#setup-status').textContent.includes('indisponible'));
 assert.equal(await first.locator('#setup-ip').inputValue(),'10.0.0.99');
 await first.close();
 assert.equal(errors.length,0,errors.join('\n'));
 console.log('PASS: responsive navigation, clock, curve/simple/RGB saves and guards, both copies, async discovery, pairing, manual/Auto, vacation test, history, powerup, export, logs, update badge.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
