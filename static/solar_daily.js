/* Persistent per-lamp solar settings. Preview dates never enter saved settings. */
'use strict';
(() => {
  const $=id=>document.getElementById('solar-'+id);
  if(!$('save'))return;
  const places={muids:[46.46,6.22],nyon:[46.3833,6.2333],lausanne:[46.5197,6.6323]};
  const defaults={latitude:46.46,longitude:6.22,tz:'Europe/Zurich',wake:420,bed:1350,low:10,high:85,transition:30,comfort:55,saturation:45,morning_hue:34,evening_hue:28,night_hue:30,day_kelvin:2700};
  const rhythmIds=['transition','comfort','saturation','morning_hue','evening_hue','night_hue','day_kelvin'];
  const fieldIds=['wake','bed','low','high',...rhythmIds];
  let uid=null,saved=null,loading=false,saving=false,view='custom',active='custom',legacy=false;
  let location={latitude:defaults.latitude,longitude:defaults.longitude,tz:defaults.tz};
  let locationSaving=false;
  let loadToken=0,previewToken=0,preview=null,timer=null,followToday=true;
  const fmt=raw=>{const m=((raw%1440)+1440)%1440;return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;};
  const minutes=v=>/^\d{2}:\d{2}$/.test(v)?Number(v.slice(0,2))*60+Number(v.slice(3)):NaN;
  const today=zone=>new Intl.DateTimeFormat('sv-SE',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function config(){
    return {...location,...Object.fromEntries(rhythmIds.map(k=>[k,Number($(k).value)])),
      wake:minutes($('wake').value),bed:minutes($('bed').value),low:Number($('low').value),high:Number($('high').value)};
  }
  function valid(c){
    return Number.isInteger(c.wake)&&Number.isInteger(c.bed)&&c.wake>=0&&c.bed<1440&&c.bed-c.wake>=180&&
      Number.isInteger(c.low)&&Number.isInteger(c.high)&&c.low>=1&&c.low<c.high&&c.high<=100&&
      rhythmIds.every(k=>Number.isInteger(c[k])&&$(k).value!=='')&&c.transition>=1&&c.transition<=180&&2*c.transition<=1440-(c.bed-c.wake)&&
      c.comfort>=c.low&&c.comfort<=c.high&&c.saturation>=0&&c.saturation<=100&&
      ['morning_hue','evening_hue','night_hue'].every(k=>c[k]>=0&&c[k]<=359)&&c.day_kelvin>=2700&&c.day_kelvin<=6500&&
      Number.isFinite(c.latitude)&&Math.abs(c.latitude)<=90&&Number.isFinite(c.longitude)&&Math.abs(c.longitude)<=180&&!!c.tz;
  }
  const dirty=()=>!!saved&&Object.keys(defaults).some(k=>config()[k]!==saved[k]);
  function fill(c){
    c={...defaults,...c};
    c.comfort=Math.max(c.low,Math.min(c.high,c.comfort));
    rhythmIds.forEach(k=>$(k).value=c[k]);
    if($('day_kelvin').value===''){const o=new Option(`${c.day_kelvin} K`,c.day_kelvin);$('day_kelvin').add(o);$('day_kelvin').value=c.day_kelvin;}
    $('wake').value=fmt(c.wake);$('bed').value=fmt(c.bed);$('low').value=c.low;$('high').value=c.high;
    location={latitude:c.latitude,longitude:c.longitude,tz:c.tz};
  }
  function lightColorNote(){const light=state?.lights.find(l=>l.id===uid);return light&&!light.capabilities?.color?'Cette lampe ne gère pas les couleurs : seule la luminosité sera appliquée.':'Choisis des couleurs pleines ; le profil règle leur saturation. Le blanc de journée est indépendant. Rendu écran indicatif.';}
  function status(){
    const changed=dirty(),c=config();
    for(const phase of ['morning','evening','night']){const h=c[phase+'_hue'];$(phase+'-swatch').style.background=`hsl(${h} 100% 50%)`;}
    $('rhythm-summary').textContent=valid(c)?'La montée se termine à ton réveil. La baisse atteint la luminosité de nuit à ton coucher.':'Vérifie les niveaux et la durée des transitions.';
    $('color-note').textContent=lightColorNote();
    $('save').disabled=loading||saving||!uid||!valid(c)||(!changed&&active==='solar'&&!legacy);
    $('cancel').disabled=loading||saving||!changed;
    $('save').textContent=saving?'Enregistrement…':legacy?'Adopter ce rythme Soleil':active==='solar'?'Enregistrer les réglages':'Enregistrer et activer Soleil';
    const light=state?.lights.find(l=>l.id===uid);
    const reason=light?.vacation_active?'Vacances est prioritaire.':light?.control_mode!=='auto'?'Passe en Auto pour suivre ce profil.':!light?.on?'Le suivi reprendra après allumage.':'Suivi automatique actif.';
    $('save-status').textContent=loading?'Chargement des réglages…':changed?'● Modifications non enregistrées · aperçu uniquement':legacy?'Ancien profil conservé. Cet aperçu propose le nouveau rythme ; enregistre pour l’adopter.':active==='solar'?`✓ Soleil enregistré · recalcul quotidien. ${reason}`:'Choisis ton rythme, puis enregistre pour activer Soleil.';
    $('save-status').classList.toggle('unsaved',changed);
    fieldIds.forEach(id=>$(id).disabled=loading||saving);
  }
  function invalidate(hideGraph=false){
    previewToken++;preview=null;$('results').hidden=true;clearTimeout(timer);
    $('graph').setAttribute('aria-busy','true');
    if(hideGraph)$('graph').hidden=true;
  }
  function sample(){
    if(!preview)return;
    const minute=Number($('sample').value);
    const s=preview.samples.reduce((best,item)=>Math.abs(item.minute-minute)<Math.abs(best.minute-minute)?item:best);
    $('sample-label').textContent=`${fmt(s.minute)} · luminosité ${Math.round(s.brightness)} % · saturation ${Math.round(s.color.s)} % · aperçu uniquement`;
    const saturation=s.color.s/100,l=1-saturation/2;
    const sat=l===1?0:(1-l)/Math.min(l,1-l);
    $('swatch').style.background=s.color.display_rgb?`rgb(${s.color.display_rgb.join(' ')})`:`hsl(${s.color.h} ${sat*100}% ${l*100}%)`;
    $('swatch').style.opacity=String(Math.max(.1,s.brightness/100));
  }
  const svgElement=tag=>document.createElementNS('http://www.w3.org/2000/svg',tag);
  function renderLandmarks(d,c){
    const clock=new Intl.DateTimeFormat('fr-CH',{timeZone:d.timezone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
    const eventMinute=iso=>iso?minutes(clock.format(new Date(iso))):null;
    const landmarks=[
      ['wake','Réveil',c.wake],
      ['sunrise','Lever du soleil',eventMinute(d.sunrise)],
      ['sunset','Coucher du soleil',eventMinute(d.sunset)],
      ['bed','Mon coucher',c.bed],
    ];
    const lines=[],labels=[];
    for(const [key,label,minute] of landmarks){
      const row=document.createElement('li');
      row.className='solar-landmark '+key;
      row.textContent=`${label} · ${minute===null?'—':fmt(minute)}`;
      labels.push(row);
      if(minute===null)continue;
      const line=svgElement('line'),title=svgElement('title');
      title.textContent=row.textContent;
      line.classList.add('solar-landmark',key);
      for(const [name,value] of Object.entries({x1:minute/2,x2:minute/2,y1:10,y2:121}))line.setAttribute(name,value);
      line.append(title);
      lines.push(line);
    }
    $('graph-lines').replaceChildren(...lines);
    $('landmarks').replaceChildren(...labels);
  }
  function renderColorBand(d){
    const stops=d.samples.filter(s=>s.color.display_rgb).map(s=>{
      const stop=svgElement('stop');
      stop.setAttribute('offset',s.minute/1440);
      stop.setAttribute('stop-color',`rgb(${s.color.display_rgb.join(' ')})`);
      return stop;
    });
    $('color-gradient').replaceChildren(...stops);
    const show=stops.length>0&&state?.lights.find(l=>l.id===uid)?.capabilities?.color!==false;
    for(const id of ['color-band','saturation-line'])$(id).toggleAttribute('hidden',!show);
    for(const id of ['color-key','saturation-key'])$(id).hidden=!show;
  }
  async function renderPreview(){
    invalidate();const token=previewToken,id=uid,c=config();
    if(view!=='solar'||!id||loading)return;
    if(!valid(c)){$('status').textContent='Vérifie les horaires (réveil avant coucher) et les niveaux lumineux.';return;}
    if(!/^\d{4}-\d{2}-\d{2}$/.test($('date').value)){$('status').textContent='Choisis une date pour l’aperçu.';return;}
    $('status').textContent='Calcul de l’aperçu…';
    try{
      const d=await api('/api/solar/draft?'+new URLSearchParams({...c,day:$('date').value,uid:id}));
      if(token!==previewToken||uid!==id)return;
      preview=d;
      renderLandmarks(d,c);
      renderColorBand(d);
      $('curve-line').setAttribute('points',d.samples.map(s=>`${s.minute/2},${120-s.brightness}`).join(' '));
      $('saturation-line').setAttribute('points',d.samples.map(s=>`${s.minute/2},${120-s.color.s}`).join(' '));
      const t=d.timing;
      $('draft-hours').textContent=`Réveil ${fmt(t.wake_start)}–${fmt(c.wake)} · teinte du soir à ${fmt(t.warm_at)} · baisse ${fmt(t.dim_start)}–${fmt(c.bed)}. ${d.polar_fallback?'Soleil absent : rythme personnel utilisé.':d.timing_note||''}`;
      $('results').hidden=false;$('graph').hidden=false;$('graph').removeAttribute('aria-busy');sample();
      $('status').textContent=`Aperçu du ${d.day.split('-').reverse().join('.')} · ${d.timezone}. La date ne modifie pas le suivi quotidien.`;
    }catch(e){if(token===previewToken)$('status').textContent='Aperçu indisponible. '+e.message;}
  }
  function schedule(){invalidate();status();if(view==='solar')timer=setTimeout(renderPreview,250);}
  for(const id of fieldIds){
    $(id).addEventListener('input',schedule);
    $(id).addEventListener('change',schedule);
  }
  function locationFields() {
    const custom=$('place').value==='custom';
    $('coordinates').hidden=!custom;
    for(const id of ['lat','lon','zone']) $(id).required=custom;
    $('location-save').disabled=locationSaving||!$('place').value;
  }
  $('place').addEventListener('change',locationFields);
  function locationStatus(shared) {
    $('location-status').textContent=shared?'Cette ville sert au calcul du lever et du coucher du soleil pour toutes les lampes.':
      'Choisis une ville commune. Chaque profil Soleil utilise actuellement son lieu enregistré.';
  }
  async function openLocation() {
    if(locationSaving)return;
    $('place').disabled=true;
    $('location-save').disabled=true;
    try{
      const {location:shared}=await api('/api/solar/location');
      const place=shared||location;
      $('lat').value=place.latitude;$('lon').value=place.longitude;$('zone').value=place.tz;
      $('place').value=shared?(Object.keys(places).find(key=>places[key][0]===place.latitude&&
        places[key][1]===place.longitude&&place.tz==='Europe/Zurich')||'custom'):'';
      locationStatus(shared);
      $('place').disabled=false;
      locationFields();
    }catch(error){$('location-status').textContent=error.message;}
  }
  $('location-form').onsubmit=event=>{
    event.preventDefault();
    if(locationSaving||$('place').disabled||!$('place').value)return;
    safe(async()=>{
      const coords=places[$('place').value];
      const data=coords?{latitude:coords[0],longitude:coords[1],tz:'Europe/Zurich'}:
        {latitude:Number($('lat').value),longitude:Number($('lon').value),tz:$('zone').value.trim()};
      locationSaving=true;
      $('place').disabled=true;
      locationFields();
      try{
        const {location:shared}=await api('/api/solar/location','PUT',data);
        locationStatus(shared);
        await window.HueProfiles?.reload();
        await refresh();
        showToast('Ville enregistrée.');
      }catch(error){$('location-status').textContent=error.message;}
      finally{locationSaving=false;$('place').disabled=false;locationFields();}
    });
  };
  $('date').addEventListener('input',()=>{followToday=false;schedule();});
  $('today').onclick=()=>{try{$('date').value=today(config().tz);followToday=true;renderPreview();}catch(e){$('status').textContent='Fuseau horaire inconnu.';}};
  $('sample').addEventListener('input',sample);
  function discard(){if(saved)fill(saved);invalidate(true);status();}
  $('cancel').onclick=()=>{discard();renderPreview();};
  async function reload(id){
    const token=++loadToken;uid=id;loading=true;saved=null;invalidate(true);status();
    if(!id){loading=false;status();return;}
    try{
      const data=await api('/api/profile/solar/'+encodeURIComponent(id));
      if(token!==loadToken||selectedId!==id)return;
      legacy=!('transition' in data.config);saved={...defaults,...data.config};active=data.type;fill(saved);saved=config();followToday=true;$('date').value=today(saved.tz);
    }catch(e){if(token===loadToken)$('save-status').textContent='Chargement impossible. '+e.message;}
    finally{if(token===loadToken){loading=false;if(saved){status();if(view==='solar')renderPreview();}}}
  }
  $('save').onclick=()=>safe(async()=>{
    if(saving||loading||!uid||!valid(config()))return;
    if(window.HueProfiles?.hasFieldEdits()||window.HueRGB?.hasChanges())throw Error('Enregistre ou annule les autres modifications avant d’activer Soleil.');
    const id=uid,c=config();saving=true;status();
    try{
      await api('/api/profile/solar/'+encodeURIComponent(id),'PUT',{config:c});
      saved=c;active='solar';legacy=false;
      await window.HueProfiles.reload();window.HueRGB?.reloadIfClean(id);await refresh();
      showToast('Soleil enregistré : les horaires se recalculeront chaque jour.');
    }finally{saving=false;status();}
  });
  const originalLoad=loadProfile;
  loadProfile=async function(){const id=selectedId;await originalLoad();if(id===selectedId)await reload(id);};
  window.HueSolar={hasChanges:dirty,isBusy:()=>saving||locationSaving,discard,openLocation,refreshStatus:status,
    setView(next,kind){const changed=view!==next;view=next;active=kind;status();if(changed&&view==='solar'&&saved)renderPreview();}};
  fill(defaults);status();
  setInterval(()=>{
    if(view!=='solar'||!saved||loading)return;
    status();
    if(followToday){try{const day=today(config().tz);if($('date').value!==day){$('date').value=day;renderPreview();}}catch(_){}}
  },60000);
})();
