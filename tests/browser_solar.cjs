const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({locale:'fr-CH'}),errors=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.method()!=='GET')writes.push({url:new URL(r.url()).pathname,data:r.postDataJSON()});});
 await page.goto('http://127.0.0.1:8765');
 await page.locator('.light-card').first().waitFor({state:'attached'});
 await page.locator('.nav [data-tab="profiles"]').click();
 await page.waitForFunction(()=>selectedId==='light-0'&&!document.querySelector('#v052-wake').disabled);
 await page.locator('.v052-mode[data-type="solar"]').click();
 await page.locator('#solar-graph').waitFor({state:'visible'});
 assert.equal(await page.locator('#solar-advanced').getAttribute('open'),null);
 assert.equal(await page.locator('#solar-wake').isVisible(),true);
 assert.equal(await page.locator('#solar-bed').isVisible(),true);
 assert.equal(await page.locator('#solar-day_kelvin').isVisible(),true);
 assert.equal(await page.locator('#solar-comfort').isVisible(),false);
 assert.equal(await page.locator('#solar-day_kelvin').inputValue(),'2700');
 await page.locator('#solar-preview > summary').click();
 await page.locator('#solar-results').waitFor({state:'visible'});
 await page.locator('#solar-wake').fill('05:15');
 await page.locator('#solar-bed').fill('22:30');
 await page.locator('#solar-date').fill('2026-11-06');
 await page.waitForFunction(()=>document.querySelector('#solar-draft-hours').textContent.includes('04:45–05:15'));
 assert.ok((await page.locator('#solar-draft-hours').textContent()).includes('teinte du soir à 17:13 · baisse 21:30–22:30'));
 assert.deepEqual(await page.locator('#solar-landmarks li').allTextContents(),
   ['Réveil · 05:15','Lever du soleil · 07:23','Coucher du soleil · 17:13','Mon coucher · 22:30']);
 assert.equal(await page.locator('#solar-graph-lines line').count(),4);
 assert.ok(await page.locator('#solar-color-gradient stop').count()>100);
 assert.equal(writes.length,0,'previews must not change settings or lamps');
 await page.locator('#solar-save').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('Soleil actif'));
 await page.waitForFunction(()=>!window.HueSolar.isBusy());
 const saved=await page.evaluate(()=>api('/api/profile/solar/light-0'));
 assert.equal(saved.config.wake,315);assert.equal(saved.type,'solar');assert.equal('day' in saved.config,false);
 assert.equal(saved.config.transition,30);assert.equal(saved.config.comfort,55);assert.equal(saved.config.saturation,45);assert.equal(saved.config.day_kelvin,2700);
 assert.equal(await page.locator('#solar-save').isDisabled(),true,'no false dirty state after save');
 assert.ok((await page.locator('#solar-saturation-line').getAttribute('points')).length>100);
 await page.locator('#solar-sample').fill('1320');await page.locator('#solar-sample').dispatchEvent('input');
 assert.ok((await page.locator('#solar-sample-label').textContent()).includes('luminosité 55 % · saturation 45 %'));
 await page.locator('#solar-sample').fill('1350');await page.locator('#solar-sample').dispatchEvent('input');
 assert.ok((await page.locator('#solar-sample-label').textContent()).includes('luminosité 10 % · saturation 100 %'));
 const count=writes.length;
 await page.locator('#solar-date').fill('2027-06-21');
 await page.waitForFunction(()=>document.querySelector('#solar-status').textContent.includes('21.06.2027'));
 const summer=await page.locator('#solar-draft-hours').textContent();
 await page.locator('#solar-date').fill('2027-12-21');
 await page.waitForFunction(()=>document.querySelector('#solar-status').textContent.includes('21.12.2027'));
 assert.notEqual(await page.locator('#solar-draft-hours').textContent(),summer);
 assert.equal(writes.length,count,'changing preview date is read only');
 assert.deepEqual(await page.evaluate(()=>api('/api/profile/solar/light-0')),saved);
 // Dirty solar fields protect lamp selection and navigation; cancelling restores them.
 await page.locator('#solar-wake').fill('06:00');
 page.once('dialog',d=>d.dismiss());await page.locator('#profile-light').selectOption('light-1');
 assert.equal(await page.locator('#profile-light').inputValue(),'light-0');
 page.once('dialog',d=>d.dismiss());await page.locator('.nav [data-tab="dashboard"]').click();
 assert.equal(await page.evaluate(()=>activeTab),'profiles');
 await page.locator('#solar-cancel').click();assert.equal(await page.locator('#solar-wake').inputValue(),'05:15');
 await page.locator('#profile-light').selectOption('light-1');
 await page.waitForFunction(()=>selectedId==='light-1'&&!document.querySelector('#solar-wake').disabled);
 await page.locator('.v052-mode[data-type="solar"]').click();
 await page.locator('#solar-wake').fill('07:10');await page.locator('#solar-save').click();
 await page.waitForFunction(()=>!window.HueSolar.isBusy()&&document.querySelector('#v052-type-status').textContent.includes('Soleil actif'));
 await page.locator('#profile-light').selectOption('light-0');
 await page.waitForFunction(()=>selectedId==='light-0'&&document.querySelector('#solar-wake').value==='05:15');
 // Profile selection persists after reload. No activation based on the preview date.
 await page.reload();await page.locator('.light-card').first().waitFor({state:'attached'});await page.locator('.nav [data-tab="profiles"]').click();
 await page.waitForFunction(()=>document.querySelector('.profile-card').dataset.v052View==='solar'&&!document.querySelector('#solar-wake').disabled&&document.querySelector('#solar-wake').value==='05:15');
 assert.equal(await page.locator('#solar-preview').getAttribute('open'),null);
 await page.locator('#solar-advanced > summary').click();
 for(const width of [320,390,1320]){
  await page.setViewportSize({width,height:1000});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  assert.equal(await page.locator('.v052-mode').evaluateAll(buttons=>buttons.some(b=>b.scrollWidth>b.clientWidth)),false,'profile labels fit at '+width);
  await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(80);
  await page.screenshot({path:`/tmp/hue-solar-${width}.png`,fullPage:true});
 }
 for (const [left,right] of [['wake','bed'],['comfort','saturation'],['transition','low']]) {
   const a=await page.locator('#solar-'+left).boundingBox();
   const b=await page.locator('#solar-'+right).boundingBox();
   assert.ok(a&&b&&Math.abs(a.y-b.y)<1,'paired solar fields align: '+left);
 }
 // Existing color editor keeps the daily source and hides duplicate schedule controls.
 await page.locator('#profile-colors > summary').click();
 await page.waitForFunction(()=>window.HueRGB.currentId()==='light-0');
 await page.locator('#rgb-auto').click();
 assert.equal(await page.locator('#rgb-schedule-toggle').isVisible(),false);
 assert.equal(await page.locator('#rgb-wheel').isVisible(),false,'Soleil colours have a single editor');
 await page.locator('#rgb-save').click();
 await page.waitForFunction(()=>!window.HueRGB.hasChanges());
 await page.waitForFunction(()=>document.querySelector('#solar-save-status').textContent.includes('Suivi automatique actif'));
 assert.equal((await page.evaluate(()=>api('/api/profile/solar/light-0'))).type,'solar');
 // New values and colours persist after save/reload; cancel restores all fields.
 await page.locator('#solar-comfort').fill('62');await page.locator('#solar-saturation').fill('58');await page.locator('#solar-transition').fill('45');
 await page.locator('#solar-day_kelvin').selectOption('3000');await page.locator('#solar-night_hue').fill('0');
 await page.locator('#solar-save').click();await page.waitForFunction(()=>!window.HueSolar.isBusy()&&document.querySelector('#solar-save').disabled);
 const changed=await page.evaluate(()=>api('/api/profile/solar/light-0'));
 assert.equal(changed.config.comfort,62);assert.equal(changed.config.saturation,58);assert.equal(changed.config.transition,45);assert.equal(changed.config.day_kelvin,3000);assert.equal(changed.config.night_hue,0);
 await page.route('**/static/solar_daily.js?*',async route=>{
  await new Promise(resolve=>setTimeout(resolve,350));
  await route.continue();
 },{times:1});
 await page.reload();await page.locator('.light-card').first().waitFor({state:'attached'});await page.locator('.nav [data-tab="profiles"]').click();
 try{await page.waitForFunction(()=>!document.querySelector('#solar-wake').disabled&&document.querySelector('#solar-comfort').value==='62');}catch(e){console.error('Reload state',await page.evaluate(()=>({selectedId,activeTab,status:document.querySelector('#solar-save-status').textContent,value:document.querySelector('#solar-comfort').value,disabled:document.querySelector('#solar-wake').disabled})),errors,await page.evaluate(()=>api('/api/profile/solar/light-0')));throw e;}
 await page.locator('#solar-advanced > summary').click();
 await page.locator('#solar-preview > summary').click();
 assert.equal(await page.locator('#solar-transition').inputValue(),'45');assert.equal(await page.locator('#solar-day_kelvin').inputValue(),'3000');
 await page.locator('#solar-wake').fill('02:00');await page.locator('#solar-transition').fill('180');assert.equal(await page.locator('#solar-save').isDisabled(),true,'overlapping night ramps rejected');
 await page.locator('#solar-cancel').click();assert.equal(await page.locator('#solar-transition').inputValue(),'45');
 // Validation, polar fallback and recovery; invalid inputs never activate.
 await page.locator('#solar-wake').fill('23:30');
 assert.equal(await page.locator('#solar-save').isDisabled(),true);
 await page.waitForFunction(()=>document.querySelector('#solar-status').textContent.includes('Vérifie'));
 assert.equal(await page.locator('#solar-results').isVisible(),false);
 await page.locator('#solar-cancel').click();
 // Settings validate the shared city before replacing the per-lamp location.
 await page.locator('.nav [data-tab="settings"]').click();
 await page.locator('.settings-nav [data-tab="location"]').click();
 await page.locator('#solar-place').selectOption('custom');
 await page.locator('#solar-zone').fill('No/SuchZone');
 await page.locator('#solar-location-save').click();
 await page.getByText('Fuseau horaire inconnu.',{exact:true}).waitFor();
 assert.equal((await page.evaluate(()=>api('/api/solar/location'))).location,null);
 await page.locator('#solar-zone').fill('Europe/Zurich');
 await page.locator('#solar-lat').fill('78.22');
 await page.locator('#solar-lon').fill('15.65');
 await page.locator('#solar-location-save').click();
 await page.getByText('Ville enregistrée.',{exact:true}).waitFor();
 await page.locator('.nav [data-tab="profiles"]').click();
 await page.locator('#solar-date').fill('2027-06-21');
 await page.waitForFunction(()=>document.querySelector('#solar-draft-hours').textContent.includes('Soleil absent'));
 assert.equal(await page.locator('#solar-graph-lines line').count(),2);
 assert.equal(await page.locator('#solar-landmarks li.sunset').textContent(),'Coucher du soleil · —');
 for (const id of ['light-0','light-1']) {
   assert.equal((await page.evaluate(uid=>api('/api/profile/solar/'+uid),id)).config.latitude,78.22);
 }
 // Save a Simple profile while keeping Soleil's settings for a later return.
 await page.locator('.v052-mode[data-type="simple"]').click();
 await page.locator('#v052-save').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('Profil simple actif'));
 assert.equal((await page.evaluate(()=>api('/api/profile/solar/light-0'))).config.wake,315);
 assert.equal(errors.length,0,errors.join('\n'));
 console.log('PASS: shared city, daily solar settings, seasonal dates, drafts, reload and responsive layouts.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
