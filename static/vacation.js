"use strict";
(() => {
  const $ = q => document.querySelector(q);
  const prettyDate = new Intl.DateTimeFormat("fr-CH", {timeZone:"Europe/Zurich",
    weekday:"short", day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit", hour12:false});
  let busy = false, selectionInitialized = false, known = [], selected = [];

  function renderSelection(lights, current) {
    const options = $("#vacation-lights");
    options.replaceChildren();
    for(const light of lights) {
      const label = document.createElement("label");
      label.className = "vacation-choice";
      const input = document.createElement("input");
      input.type = "checkbox"; input.value = light.id;
      input.checked = current.includes(light.id);
      input.addEventListener("change", () => {
        selected = [...options.querySelectorAll("input:checked")].map(x => x.value);
        $("#vacation-toggle").disabled = !selected.length;
      });
      label.append(input, document.createTextNode(" " + light.name));
      options.appendChild(label);
    }
  }

  function renderPreview(events, lights) {
    const where = $("#vacation-preview");
    where.replaceChildren();
    if(!events.length) {
      where.textContent = "Aucun événement à venir.";
      return;
    }
    const lookup = Object.fromEntries(lights.map(x => [x.id, x.name]));
    const ul = document.createElement("ul");
    ul.className = "vacation-plan";
    for(const event of events.slice(0, 8)) {
      const li = document.createElement("li");
      const date = document.createElement("time");
      date.textContent = prettyDate.format(new Date(event.at));
      li.append(date, document.createTextNode(" · " +
        (lookup[event.light_id] || "Lampe") + " · " +
        (event.on ? "Allumage" : "Extinction")));
      ul.appendChild(li);
    }
    where.appendChild(ul);
  }

  async function refresh() {
    if(busy) return;
    busy = true;
    try {
      const [vResp, lResp] = await Promise.all([
        fetch("/api/vacation", {cache:"no-store"}),
        fetch("/api/state", {cache:"no-store"})
      ]);
      if(!vResp.ok || !lResp.ok) throw new Error("Communication indisponible");
      const vacation = (await vResp.json()).data;
      const data = await lResp.json();
      known = data.lights || [];
      const ids = known.map(x => x.id).join("|");
      const prior = $("#vacation-lights").dataset.ids;
      if(!selectionInitialized || prior !== ids || vacation.enabled) {
        selected = vacation.enabled ? vacation.light_ids : (selectionInitialized ? selected : known.map(x=>x.id));
        selected = selected.filter(id => known.some(l=>l.id===id));
        renderSelection(known, selected);
        $("#vacation-lights").dataset.ids = ids;
        selectionInitialized = true;
      }
      const active = vacation.enabled;
      $("#vacation-status").textContent = active ? "ACTIF" : "DÉSACTIVÉ";
      $("#vacation-status").classList.toggle("vacation-active", active);
      $("#vacation-toggle").textContent = active ? "Arrêter Vacances" : "Activer Vacances";
      $("#vacation-toggle").disabled = !active && (!selected.length || !data.connected);
      $("#vacation-lights").querySelectorAll("input").forEach(input => input.disabled = active);
      const overrides = Object.keys(vacation.overrides || {}).length;
      $("#vacation-feedback").textContent = active
        ? (overrides ? overrides+" priorité(s) manuelle(s) de 10 min en cours." : "Simulation active sur le Raspberry.")
        : "Laisse les interrupteurs muraux sous tension.";
      renderPreview(vacation.next_actions || [], known);
    } catch(e) {
      $("#vacation-feedback").textContent = "Impossible de lire Vacances : " + e.message;
    } finally {busy=false;}
  }

  $("#vacation-toggle").addEventListener("click", async () => {
    const active = $("#vacation-status").textContent === "ACTIF";
    const button = $("#vacation-toggle");
    button.disabled = true;
    try {
      const response = await fetch("/api/vacation", {method:"POST",cache:"no-store",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({enabled:!active,light_ids:!active?selected:undefined})});
      const result = await response.json();
      if(!response.ok || result.ok===false)
        throw new Error(result.error || "Erreur HTTP " + response.status);
      await refresh();
    } catch(e) {
      $("#vacation-feedback").textContent = "Erreur : " + e.message;
      button.disabled = false;
    }
  });

  refresh();
  setInterval(() => {
    if (!$("#tab-dashboard").classList.contains("hidden")) refresh();
  }, 20000);
})();
