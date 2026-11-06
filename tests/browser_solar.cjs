const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({locale:'fr-CH'}),errors=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.method()!=='GET')writes.push({url:new URL(r.url()).pathname,data:r.postDataJSON()});});
 await page.goto('http://127.0.0.1:8765');
 await page.locator('.light-card').first().waitFor();
 await page.locator('.nav [data-tab="profiles"]').click();
 await page.waitForFunction(()=>selectedId==='light-0'&&!document.querySelector('#v052-wake').disabled);
 await page.locator('.v052-mode[data-type="solar"]').click();
 await page.locator('#solar-results').waitFor({state:'visible'});
 await page.locator('#solar-wake').fill('05:15');
 await page.locator('#solar-bed').fill('22:30');
 await page.locator('#solar-date').fill('2026-11-06');
 await page.waitForFunction(()=>document.querySelector('#solar-draft-hours').textContent.includes('05:15–07:23'));
 assert.ok((await page.locator('#solar-draft-hours').textContent()).includes('17:13–22:30'));
 assert.equal(writes.length,0,'previews must not change settings or lamps');
 await page.locator('#solar-save').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('Soleil actif'));
 await page.waitForFunction(()=>!window.HueSolar.isBusy());
 const saved=await page.evaluate(()=>api('/api/profile/solar/light-0'));
 assert.equal(saved.config.wake,315);assert.equal(saved.type,'solar');assert.equal('day' in saved.config,false);
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
 await page.reload();await page.locator('.nav [data-tab="profiles"]').click();
 await page.waitForFunction(()=>document.querySelector('.profile-card').dataset.v052View==='solar'&&!document.querySelector('#solar-wake').disabled);
 assert.equal(await page.locator('#solar-wake').inputValue(),'05:15');
 for(const width of [320,390,1320]){
  await page.setViewportSize({width,height:1000});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  await page.evaluate(()=>window.scrollTo(0,0));await page.waitForTimeout(80);
  await page.screenshot({path:`/tmp/hue-solar-${width}.png`,fullPage:true});
 }
 // Existing color editor keeps the daily source and hides duplicate schedule controls.
 await page.locator('#profile-colors > summary').click();
 await page.waitForFunction(()=>window.HueRGB.currentId()==='light-0');
 await page.locator('#rgb-auto').click();
 assert.equal(await page.locator('#rgb-schedule-toggle').isVisible(),false);
 await page.locator('#rgb-presets button[data-h="32"]').click();await page.locator('#rgb-save').click();
 await page.waitForFunction(()=>!window.HueRGB.hasChanges());
 await page.waitForFunction(()=>document.querySelector('#solar-save-status').textContent.includes('Suivi automatique actif'));
 assert.equal((await page.evaluate(()=>api('/api/profile/solar/light-0'))).type,'solar');
 // Validation, polar fallback and recovery; invalid inputs never activate.
 await page.locator('#solar-wake').fill('23:30');
 assert.equal(await page.locator('#solar-save').isDisabled(),true);
 await page.waitForFunction(()=>document.querySelector('#solar-status').textContent.includes('Vérifie'));
 assert.equal(await page.locator('#solar-results').isVisible(),false);
 await page.locator('#solar-cancel').click();
 await page.locator('#solar-place').selectOption('custom');await page.locator('#solar-zone').fill('No/SuchZone');
 await page.waitForFunction(()=>document.querySelector('#solar-status').textContent.includes('indisponible'));
 await page.locator('#solar-zone').fill('Europe/Zurich');await page.locator('#solar-lat').fill('78.22');await page.locator('#solar-lon').fill('15.65');
 await page.locator('#solar-date').fill('2027-06-21');
 await page.waitForFunction(()=>document.querySelector('#solar-draft-hours').textContent.includes('Soleil absent'));
 await page.locator('#solar-cancel').click();
 // Switching away from Soleil keeps its options for a later return.
 await page.locator('.v052-mode[data-type="custom"]').click();
 await page.locator('#v052-activate-custom').click();
 await page.waitForFunction(()=>document.querySelector('#v052-type-status').textContent.includes('personnalisé actif'));
 assert.equal((await page.evaluate(()=>api('/api/profile/solar/light-0'))).config.wake,315);
 assert.equal(errors.length,0,errors.join('\n'));
 console.log('PASS: persistent daily solar per lamp, read-only seasonal dates, reload, drafts/guards, RGB source preservation, polar/validation, 320/390/1320 px.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
