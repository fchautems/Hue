// Real browser, actual API and simulated bridge. Never contacts the user's lamps.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({locale:'fr-CH',hasTouch:true});
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
 const plan=page.getByRole('region',{name:'Plan de l’appartement'});
 const lamp=plan.locator('[data-plan-lamp="light-0"]');
 const corridor=plan.getByRole('button',{name:'Allumer ou éteindre la pièce · Couloir'});
 const surface=plan.locator('.apartment-plan-surface');
 assert.equal(await plan.getByText('Parties communes',{exact:true}).count(),0);
 const listToggle=page.locator('.plan-cards-toggle');
 await lamp.waitFor();
 assert.equal(await plan.locator('.plan-room-action').count(),6);
 assert.equal(await plan.locator('.plan-lamp').count(),3);
 assert.equal(await listToggle.getAttribute('aria-expanded'),'false');
 for(const width of [320,393]){
  await page.setViewportSize({width,height:680});
  await page.screenshot({path:`/tmp/hue-ergonomics-rooms-${width}.png`});
  const pageHeight=await page.evaluate(()=>document.documentElement.scrollHeight);
  assert.ok(pageHeight<=680,`room home fits the phone at ${width}px (page height ${pageHeight}px)`);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),width);
  assert.ok(await plan.locator('.plan-lamp').evaluateAll(markers=>markers.every(marker=>{
   const {left,top,right,bottom,width,height}=marker.getBoundingClientRect();
   const room=marker.closest('.plan-room').getBoundingClientRect();
   return width>=32&&height>=32&&left>=room.left&&right<=room.right&&top>=room.top&&bottom<=room.bottom
    &&document.elementFromPoint(left+width/2,top+height/2)===marker;
  })),'markers are touchable and stay within their rooms');
 }
 const compactHeight=(await surface.boundingBox()).height;
 await page.setViewportSize({width:393,height:830});
 assert.ok((await surface.boundingBox()).height>compactHeight+50,'a tall phone preserves the plan proportions');
 assert.ok(await page.evaluate(()=>document.documentElement.scrollHeight<=innerHeight),'the plan still fits without scrolling');
 await page.screenshot({path:'/tmp/hue-ergonomics-plan-pixel.png'});
 await page.setViewportSize({width:393,height:680});
 const planBox=await surface.boundingBox();
 await page.touchscreen.tap(planBox.x+planBox.width*0.55,planBox.y+planBox.height*0.62);
 assert.equal(writes.length,0,'the common area sends no Hue command');
 await lamp.tap();
 await page.waitForFunction(()=>!state.lights[0].on);
 assert.deepEqual(writes.splice(0).map(r=>r.url),['/api/light/light-0/switch']);
 const roomBox=await corridor.boundingBox();
 const tapRoom=()=>page.touchscreen.tap(roomBox.x+roomBox.width*0.87,roomBox.y+roomBox.height-5);
 await tapRoom();
 await page.waitForFunction(()=>state.lights.slice(0,2).every(l=>!l.on));
 assert.deepEqual(writes.splice(0).map(r=>r.url).sort(),['/api/light/light-0/switch','/api/light/light-1/switch']);
 await tapRoom();
 await page.waitForFunction(()=>state.lights.slice(0,2).every(l=>l.on));
 assert.deepEqual(writes.splice(0).map(r=>r.url).sort(),['/api/light/light-0/switch','/api/light/light-1/switch']);

 const edit=plan.locator('.plan-edit-toggle');
 const assignment=plan.getByRole('combobox',{name:'Pièce de Entrée'});
 await edit.tap();
 assert.ok(await corridor.isDisabled());
 assert.equal(await assignment.inputValue(),'couloir');
 await lamp.tap();
 assert.equal(writes.length,0,'editing a marker never sends a Hue command');
 const other=plan.locator('[data-plan-lamp="light-1"]');
 const touchPoint=box=>({x:box.x+box.width/2,y:box.y+box.height/2});
 const touch=await page.context().newCDPSession(page);
 const drag=async(start,end)=>{
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[start]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[end]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 };
 const start=touchPoint(await lamp.boundingBox());
 const neighbour=touchPoint(await other.boundingBox());
 await drag(start,neighbour);
 assert.deepEqual(touchPoint(await lamp.boundingBox()),start,'overlapping drops keep both markers reachable');
 assert.deepEqual(touchPoint(await other.boundingBox()),neighbour,'moving one marker never moves the other');
 const desired={x:start.x+11,y:start.y+15};
 await drag(start,desired);
 const moved=touchPoint(await lamp.boundingBox());
 assert.ok(Math.hypot(moved.x-desired.x,moved.y-desired.y)<1,'the marker stays where the finger released it');
 assert.deepEqual(touchPoint(await other.boundingBox()),neighbour);
 const savedPosition=await lamp.getAttribute('style');
 await page.reload();
 await lamp.waitFor();
 await page.locator('#room-notice').waitFor({state:'hidden'});
 assert.equal(await lamp.getAttribute('style'),savedPosition,'free position survives reloading');
 await edit.tap();
 await assignment.selectOption('');
 assert.equal(await lamp.count(),0);
 assert.match(await listToggle.textContent(),/1 hors plan/);
 await page.reload();
 await other.waitFor();
 await page.locator('#room-notice').waitFor({state:'hidden'});
 assert.equal(await lamp.count(),0,'Hors plan survives reloading');
 await edit.tap();
 await assignment.selectOption('couloir');
 await lamp.waitFor();
 assert.equal(await assignment.inputValue(),'couloir');
 await edit.tap();
 assert.equal(writes.length,0,'assignment, drag and reload do not command lamps');

 const dense=await browser.newPage({locale:'fr-CH',hasTouch:true,viewport:{width:320,height:680}});
 dense.on('pageerror',e=>errors.push(e.message));
 const salonIds=['light-0', ...Array.from({length:4},(_,index)=>`salon-${index+2}`)];
 await dense.route('**/api/state',async route=>{
  const response=await route.fetch();
  const snapshot=await response.json();
  snapshot.lights=salonIds.map((id,index)=>({...snapshot.lights[0],id,name:`Salon ${index+1}`,on:index<2}));
  await route.fulfill({response,json:snapshot});
 });
 await dense.route('**/api/lighting-groups',route=>route.fulfill({json:{ok:true,data:[{
  id:'room-salon',kind:'room',name:'Salon',light_ids:salonIds,
 }]}}));
 await dense.goto('http://127.0.0.1:8766');
 const salonMarkers=dense.locator('[data-plan-room="salon"] .plan-lamp');
 await salonMarkers.last().waitFor();
 assert.equal(await salonMarkers.count(),5,'all five lamps fit in the salon');
 assert.ok(await salonMarkers.evaluateAll(markers=>markers.every(marker=>{
  const {left,top,width,height}=marker.getBoundingClientRect();
  return document.elementFromPoint(left+width/2,top+height/2)===marker;
 })),'each of the five lamps has its own touch target');
 await dense.screenshot({path:'/tmp/hue-ergonomics-salon-five-lamps.png'});
 await dense.close();

 await listToggle.click();
 const room=page.locator('.room-card').filter({has:page.getByRole('heading',{name:'Couloir',exact:true})});
 await room.waitFor();
 assert.equal(await room.locator('.room-lamp').count(),2);
 const zone=page.locator('.room-card').filter({has:page.getByRole('heading',{name:'Étage',exact:true})});
 assert.equal(await zone.locator('.room-lamp').count(),3);
 assert.ok(await page.evaluate(()=>[...document.querySelectorAll('.room-card button')].every(
  button=>button.getBoundingClientRect().height>=48)),'list touch targets at least 48 px high');
 const roomSwitch=room.getByRole('button',{name:'Commande de groupe · Couloir'});
 assert.equal(await roomSwitch.locator('.switch > span').count(),1,'the room uses the shared switch design');
 await roomSwitch.click();
 await page.waitForFunction(()=>state.lights.slice(0,2).every(l=>!l.on));
 assert.deepEqual(writes.splice(0).map(r=>r.url).sort(),['/api/light/light-0/switch','/api/light/light-1/switch']);
 const salon=room.getByRole('button',{name:'Salon',exact:true});
 const salonInZone=zone.getByRole('button',{name:'Salon',exact:true});
 let stale=true;
 const holdObservedState=async route=>{
  const response=await route.fetch();
  const snapshot=await response.json();
  if(stale)snapshot.lights[1].on=false;
  await route.fulfill({response,json:snapshot});
 };
 await page.route('**/api/state',holdObservedState);
 const acknowledged=page.waitForResponse(response=>response.url().endsWith('/api/light/light-1/switch'));
 await salon.click();
 assert.equal(await salon.getAttribute('aria-busy'),'true');
 assert.equal(await salonInZone.getAttribute('aria-busy'),'true');
 assert.equal(await salon.getAttribute('aria-pressed'),'false','waiting preserves the observed off state');
 assert.equal(await salon.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(68, 55, 34)');
 assert.ok((await acknowledged).ok());
 assert.equal(await salon.getAttribute('aria-busy'),'true','HTTP acceptance is not lamp confirmation');
 await nav('dashboard').click();
 const dashboardSwitch=page.locator('.light-card[data-id="light-1"] .switch');
 assert.equal(await dashboardSwitch.getAttribute('aria-busy'),'true','the other view shows the same pending command');
 assert.equal(await dashboardSwitch.locator('input').isChecked(),false);
 await nav('rooms').click();
 stale=false;
 await salon.and(page.locator('[aria-pressed="true"][aria-busy="false"]')).waitFor();
 await page.unroute('**/api/state',holdObservedState);
 assert.equal(await salon.evaluate(el=>getComputedStyle(el).backgroundColor),'rgb(40, 72, 63)');
 assert.deepEqual(writes.splice(0).map(r=>r.url),['/api/light/light-1/switch']);
 await page.route('**/api/light/light-1/switch',route=>route.fulfill({
  status:502,json:{ok:false,error:'Commande refusée pour le test'},
 }),{times:1});
 await salon.click();
 await page.getByText('Commande refusée pour le test',{exact:true}).waitFor();
 assert.equal(await salon.getAttribute('aria-busy'),'false');
 assert.equal(await salon.getAttribute('aria-pressed'),'true','a refused command leaves the observed state intact');
 writes.splice(0);
 await room.getByRole('button',{name:'Entrée',exact:true}).click();
 await page.waitForFunction(()=>state.lights[0].on);
 writes.splice(0);

 // Layout and reachable daily activities at phone/tablet/desktop widths.
 for(const width of [320,390,1320]){
  await page.setViewportSize({width,height:1000});
  for(const tab of ['rooms','dashboard','profiles','presence','settings','updates']){
   await nav(tab).click();
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
   assert.equal(overflow,false,`${tab} overflow at ${width}`);
   if(width<=700){
    const layout=await page.locator('.sidebar').evaluate(sidebar=>{
     const nav=sidebar.querySelector('.nav');
     const buttons=[...nav.querySelectorAll('.nav-item')];
     const rect=nav.getBoundingClientRect();
     return {
      rows:new Set(buttons.map(button=>button.offsetTop)).size,
      buttons:buttons.length,
      allVisible:buttons.every(button=>{
       const box=button.getBoundingClientRect();
       return box.width>0&&box.height>=48&&box.left>=rect.left&&box.right<=rect.right+1;
      }),
      title:sidebar.querySelector('.brand').getBoundingClientRect().height>0,
      noHorizontalScroll:nav.scrollWidth===nav.clientWidth,
     };
    });
    assert.deepEqual(layout,{rows:2,buttons:6,allVisible:true,title:true,noHorizontalScroll:true},
      `${tab}: two rows with all tabs and Hue Lab visible at ${width}px`);
   }
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
 await page.waitForFunction(()=>activeTab==='rooms');
 assert.equal(writes.find(r=>r.url==='/api/setup/pair').data.ip,'10.0.0.12');
 await nav('dashboard').click();
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
