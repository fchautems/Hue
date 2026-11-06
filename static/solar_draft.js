'use strict';
(() => {
  const $ = id => document.getElementById('solar-' + id);
  let draft = null, generation = 0, applying = false;
  const time = value => {const [h,m] = value.split(':').map(Number);return h*60+m;};
  const label = m => `${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
  function invalidate() { generation++; draft=null; $('draft').hidden=true; }
  for (const id of ['date','place','lat','lon','zone','wake','bed','low','high']) {
    $(id).addEventListener('input', invalidate);
    $(id).addEventListener('change', invalidate);
  }
  $('today').addEventListener('click',invalidate);
  $('form').addEventListener('submit',invalidate);
  function sample() {
    if (!draft) return;
    const s=draft.samples[Number($('sample').value)];
    $('sample-label').textContent=`${label(s.minute)} · ${s.brightness} % · teinte ${Math.round(s.color.h)}°, saturation ${Math.round(s.color.s)} %`;
    // HSV to HSL, matching the profile's hue/saturation at full value.
    const saturation=s.color.s/100, lightness=1-saturation/2;
    const hslS=lightness===1?0:(1-lightness)/Math.min(lightness,1-lightness);
    $('swatch').style.background=`hsl(${s.color.h} ${hslS*100}% ${lightness*100}%)`;
    $('swatch').style.opacity=String(Math.max(.1,s.brightness/100));
  }
  $('sample').addEventListener('input',sample);
  $('generate').addEventListener('click',async()=>{
    invalidate();const token=generation;
    try {
      const context=globalThis.HueSolarPreview.context();
      if (!context) throw Error('Actualise d’abord la journée solaire.');
      const query=new URLSearchParams({...context,wake:time($('wake').value),bed:time($('bed').value),low:$('low').value,high:$('high').value});
      const data=await api('/api/solar/draft?'+query);
      if(token!==generation)return;
      draft=data;
      $('draft-date').textContent=data.day;
      $('curve-line').setAttribute('points',data.samples.map(s=>`${s.minute/2},${120-s.brightness}`).join(' '));
      const p=data.params;
      $('draft-hours').textContent=`Montée ${label(p.wake)}–${label(p.morning_end)} · descente ${label(p.evening_start)}–${label(p.bed)}.${data.polar_fallback?' Soleil absent : horaires personnels utilisés.':''}`;
      $('draft').hidden=false;sample();
    } catch(error){if(token===generation)$('status').textContent=error.message;}
  });
  $('apply').addEventListener('click',()=>safe(async()=>{
    if(!draft||applying)return;
    const lamp=document.getElementById('profile-light'),uid=lamp.value;
    if(!uid)throw Error('Sélectionne une lampe dans Horloge & lumières.');
    if(window.HueProfiles?.hasUnsaved()||window.HueRGB?.hasChanges())throw Error('Enregistre ou annule les modifications de la lampe avant d’appliquer ce profil.');
    const name=lamp.options[lamp.selectedIndex]?.textContent||uid;
    if(!window.confirm(`Remplacer le profil de « ${name} » par celui du ${draft.day} ? Luminosité et couleurs compatibles seront remplacées. Le mode reste inchangé ; si la lampe est en Auto, le profil peut s’appliquer immédiatement.`))return;
    const payload={params:draft.params,colors:draft.colors};
    applying=true;$('apply').disabled=true;
    try{
      const result=await api('/api/profile/solar/'+encodeURIComponent(uid),'POST',payload);
      if(lamp.value===uid){await window.HueProfiles?.reload();window.HueRGB?.reloadIfClean(uid);}
      showToast(result.rgb_auto?'Profil luminosité et couleurs enregistré.':'Profil de luminosité enregistré (lampe sans RGB).');
    }finally{applying=false;$('apply').disabled=false;}
  }));
})();
