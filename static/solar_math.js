/* Mirrors hue_solar_rhythm.py for fixed copies and browser charts. */
'use strict';
window.HueRhythm={brightness(p,minute){
  const r=p.solar_rhythm,start=r.wake-r.transition;
  const m=(((minute-start)%1440)+1440)%1440+start;
  const times=[start,r.wake,p.morning_end,p.evening_start,r.bed,r.bed+r.transition];
  const levels=[p.min_brightness,r.comfort,p.max_brightness,p.max_brightness,r.comfort,p.min_brightness];
  for(let i=0;i<5;i++){
    if(m<times[i]||m>=times[i+1])continue;
    let t=(m-times[i])/(times[i+1]-times[i]);
    t=i>=3?t*t:1-(1-t)**2;
    const k=t*t*t*(t*(6*t-15)+10);
    return Math.round((levels[i]+(levels[i+1]-levels[i])*k)*100)/100;
  }
  return p.min_brightness;
}};
