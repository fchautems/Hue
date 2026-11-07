/* Persistent per-lamp solar settings. Preview dates never enter saved settings. */
'use strict';
(() => {
  const $=id=>document.getElementById('solar-'+id);
  if(!$('save'))return;
  const places={muids:[46.46,6.22],nyon:[46.3833,6.2333],lausanne:[46.5197,6.6323]};
  const defaults={latitude:46.46,longitude:6.22,tz:'Europe/Zurich',wake:420,bed:1350,low:10,high:85,transition:30,comfort:55,saturation:45,morning_hue:34,evening_hue:28,night_hue:16,day_kelvin:5000};
  const rhythmIds=['transition','comfort','saturation','morning_hue','evening_hue','night_hue','day_kelvin'];
  const fieldIds=['wake','bed','low','high','place','lat','lon','zone',...rhythmIds];
  let uid=null,saved=null,loading=false,saving=false,view='custom',active='custom',legacy=false;
  let loadToken=0,previewToken=0,preview=null,timer=null,followToday=true;
  const fmt=raw=>{const m=((raw%1440)+1440)%1440;return `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;};
  const minutes=v=>/^\d{2}:\d{2}$/.test(v)?Number(v.slice(0,2))*60+Number(v.slice(3)):NaN;
  const today=zone=>new Intl.DateTimeFormat('sv-SE',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  function config(){
    const coords=places[$('place').value];
    return {...Object.fromEntries(rhythmIds.map(k=>[k,Number($(k).value)])),latitude:coords?coords[0]:Number($('lat').value),longitude:coords?coords[1]:Number($('lon').value),
      tz:coords?'Europe/Zurich':$('zone').value.trim(),wake:minutes($('wake').value),bed:minutes($('bed').value),low:Number($('low').value),high:Number($('high').value)};
  }
  function valid(c){
    return Number.isInteger(c.wake)&&Number.isInteger(c.bed)&&c.wake>=0&&c.bed<1440&&c.bed-c.wake>=180&&
      Number.isInteger(c.low)&&Number.isInteger(c.high)&&c.low>=1&&c.low<c.high&&c.high<=100&&
      rhythmIds.every(k=>Number.isInteger(c[k])&&$(k).value!=='')&&c.transition>=1&&c.transition<=180&&2*c.transition<=1440-(c.bed-c.wake)&&
      c.comfort>=c.low&&c.comfort<=c.high&&c.saturation>=0&&c.saturation<=100&&
      ['morning_hue','evening_hue','night_hue'].every(k=>c[k]>=0&&c[k]<=359)&&c.day_kelvin>=4000&&c.day_kelvin<=6500&&
      Number.isFinite(c.latitude)&&Math.abs(c.latitude)<=90&&Number.isFinite(c.longitude)&&Math.abs(c.longitude)<=180&&!!c.tz&&
      ($('place').value!=='custom'||($('lat').value!==''&&$('lon').value!==''));
  }
  const dirty=()=>!!saved&&Object.keys(defaults).some(k=>config()[k]!==saved[k]);
  function fill(c){
    c={...defaults,...c};
    c.comfort=Math.max(c.low,Math.min(c.high,c.comfort));
    rhythmIds.forEach(k=>$(k).value=c[k]);
    if($('day_kelvin').value===''){const o=new Option(`${c.day_kelvin} K`,c.day_kelvin);$('day_kelvin').add(o);$('day_kelvin').value=c.day_kelvin;}
    $('wake').value=fmt(c.wake);$('bed').value=fmt(c.bed);$('low').value=c.low;$('high').value=c.high;
    $('lat').value=c.latitude;$('lon').value=c.longitude;$('zone').value=c.tz;
    $('place').value=Object.keys(places).find(k=>places[k][0]===c.latitude&&places[k][1]===c.longitude&&c.tz==='Europe/Zurich')||'custom';
    $('coordinates').hidden=$('place').value!=='custom';
  }
  function lightColorNote(){const light=state?.lights.find(l=>l.id===uid);return light&&!light.capabilities?.color?'Cette lampe ne gère pas les couleurs : seule la luminosité sera appliquée.':'Choisis des couleurs pleines ; le profil règle leur saturation. Le blanc de journée est indépendant. Rendu écran indicatif.';}
  function status(){
    const changed=dirty(),c=config();
    for(const phase of ['morning','evening','night']){const h=c[phase+'_hue'];$(phase+'-swatch').style.background=`hsl(${h} 100% 50%)`;}
    $('rhythm-summary').textContent=valid(c)?`Réveil de ${fmt(c.wake-c.transition)} à ${fmt(c.wake)}. Passage à la nuit de ${fmt(c.bed)} à ${fmt(c.bed+c.transition)} (luminosité ${c.low} %, saturation 100 %).`:'Vérifie les niveaux et la durée : les transitions doivent tenir dans la nuit.';
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
  function invalidate(){previewToken++;preview=null;$('results').hidden=true;clearTimeout(timer);}
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
      const time=iso=>iso?new Intl.DateTimeFormat('fr-CH',{timeZone:d.timezone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(iso)):'—';
      $('rise').textContent=time(d.sunrise);$('set').textContent=time(d.sunset);
      $('curve-line').setAttribute('points',d.samples.map(s=>`${s.minute/2},${120-s.brightness}`).join(' '));
      $('saturation-line').setAttribute('points',d.samples.map(s=>`${s.minute/2},${120-s.color.s}`).join(' '));
      const p=d.params;
      $('draft-hours').textContent=`Réveil ${fmt(c.wake-c.transition)}–${fmt(c.wake)} · journée dès ${fmt(p.morning_end)} · soirée dès ${fmt(p.evening_start)} · nuit ${fmt(c.bed)}–${fmt(c.bed+c.transition)}. ${d.polar_fallback?'Soleil absent : rythme personnel utilisé.':d.timing_note||''}`;
      $('results').hidden=false;sample();
      $('status').textContent=`Aperçu du ${d.day.split('-').reverse().join('.')} · ${d.timezone}. La date ne modifie pas le suivi quotidien.`;
    }catch(e){if(token===previewToken)$('status').textContent='Aperçu indisponible. '+e.message;}
  }
  function schedule(){invalidate();status();if(view==='solar')timer=setTimeout(renderPreview,250);}
  for(const id of fieldIds){
    $(id).addEventListener('input',schedule);
    $(id).addEventListener('change',()=>{$('coordinates').hidden=$('place').value!=='custom';schedule();});
  }
  $('date').addEventListener('input',()=>{followToday=false;schedule();});
  $('today').onclick=()=>{try{$('date').value=today(config().tz);followToday=true;renderPreview();}catch(e){$('status').textContent='Fuseau horaire inconnu.';}};
  $('sample').addEventListener('input',sample);
  function discard(){if(saved)fill(saved);invalidate();status();}
  $('cancel').onclick=()=>{discard();renderPreview();};
  async function reload(id){
    const token=++loadToken;uid=id;loading=true;saved=null;invalidate();status();
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
  window.HueSolar={hasChanges:dirty,isBusy:()=>saving,discard,refreshStatus:status,
    setView(next,kind){const changed=view!==next;view=next;active=kind;status();if(changed&&view==='solar'&&saved)renderPreview();}};
  fill(defaults);status();
  setInterval(()=>{
    if(view!=='solar'||!saved||loading)return;
    status();
    if(followToday){try{const day=today(config().tz);if($('date').value!==day){$('date').value=day;renderPreview();}}catch(_){}}
  },60000);
})();
