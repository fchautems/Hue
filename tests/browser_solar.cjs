const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({locale:'fr-CH'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765');
 await page.waitForTimeout(700);
 await page.locator('[data-tab="profiles"]').click();
 await page.locator('#solar-results').waitFor({state:'visible'});
 for(const width of [320,390,1320]){
  await page.setViewportSize({width,height:950});
  await page.locator('#solar-title').scrollIntoViewIfNeeded();
  const overflow=await page.locator('.solar-card').evaluate(el=>el.scrollWidth>el.clientWidth);
  if(overflow)throw Error('solar overflow '+width);
  await page.locator('.solar-card').screenshot({path:'/tmp/hue-solar-'+width+'.png'});
 }
 await page.locator('#solar-date').fill('2026-06-21');
 if(await page.locator('#solar-results').isVisible())throw Error('stale results visible');
 await page.getByRole('button',{name:'Voir cette journée'}).click();
 await page.locator('#solar-results').waitFor({state:'visible'});
 const summer=await page.locator('#solar-duration').textContent();
 await page.locator('#solar-wake').fill('05:00');
 if(!(await page.locator('#solar-comparison').textContent()).includes('avant'))throw Error('routine comparison');
 await page.locator('#solar-place').selectOption('custom');
 await page.locator('#solar-zone').fill('No/SuchZone');
 await page.getByRole('button',{name:'Voir cette journée'}).click();
 await page.waitForFunction(()=>document.getElementById('solar-status').textContent.includes('indisponible'));
 if(await page.locator('#solar-results').isVisible())throw Error('error retains stale result');
 await page.locator('#solar-zone').fill('Europe/Zurich');
 await page.locator('#solar-lat').fill('78.22');
 await page.locator('#solar-lon').fill('15.65');
 await page.getByRole('button',{name:'Voir cette journée'}).click();
 await page.waitForFunction(()=>document.getElementById('solar-status').textContent.includes('polaire'));
 if(await page.locator('#solar-daylight').isVisible())throw Error('polar day band');
 if(await page.locator('#solar-scale').isVisible())throw Error('polar scale');
 if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: 320/390/1320 px; seasonal preview '+summer+'; routine; invalid zone; polar fallback; no JS errors');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
