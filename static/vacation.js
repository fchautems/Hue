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

  function renderTest(test = {}, lights = []) {
    const running = test.running === true;
    const button = $("#vacation-test-toggle");
    button.dataset.running = String(running);
    button.textContent = running ? "■ Arrêter le test" : "▶ Tester 60 s";
    button.disabled = !running && $("#vacation-status").textContent !== "ACTIF";
    const panel = $("#vacation-test-progress");
    panel.classList.toggle("hidden", test.status === "inactif" || !test.status);
    const elapsed = Math.min(60, Math.max(0, Number(test.elapsed_seconds) || 0));
    $("#vacation-test-fill").style.width = (elapsed / 60 * 100).toFixed(1) + "%";
    $("#vacation-test-meter").setAttribute("aria-valuenow", String(Math.round(elapsed)));
    let label;
    if (running) {
      const clock = test.simulated_time
        ? new Intl.DateTimeFormat("fr-CH", {timeZone:"Europe/Zurich",
            hour:"2-digit", minute:"2-digit",hour12:false}).format(new Date(test.simulated_time))
        : "—";
      const names = Object.fromEntries(lights.map(l => [l.id,l.name]));
      const event = test.last_event
        ? (" · Dernier : " + (names[test.last_event.light_id] || "Lampe")
          + " " + (test.last_event.on ? "allumée" : "éteinte")) : "";
      label = Math.ceil(60-elapsed) + " s restantes · Heure simulée " + clock +
        " · " + (test.processed || 0) + "/" + (test.total || 0) + " événements" + event;
    } else {
      label = test.status === "terminé"
        ? "Test terminé — le programme Vacances réel a repris."
        : "Test interrompu — retour au programme normal.";
    }
    $("#vacation-test-label").textContent = label;
    return running;
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
      const testing = renderTest(vacation.test, known);
      $("#vacation-toggle").disabled = testing || (!active && (!selected.length || !data.connected));
      $("#vacation-test-toggle").disabled = !testing && !active;
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

  $("#vacation-test-toggle").addEventListener("click", async () => {
    const button = $("#vacation-test-toggle");
    const action = button.dataset.running === "true" ? "stop" : "start";
    button.disabled = true;
    $("#vacation-test-label").textContent = action === "start" ? "Démarrage du test…" : "Arrêt en cours…";
    try {
      const response = await fetch("/api/vacation/test", {method:"POST", cache:"no-store",
        headers:{"Content-Type":"application/json"}, body:JSON.stringify({action})});
      const result = await response.json();
      if(!response.ok || result.ok===false)
        throw new Error(result.error || "Erreur HTTP " + response.status);
      await refresh();
    } catch(e) {
      $("#vacation-feedback").textContent = "Test rapide : " + e.message;
      await refresh();
    }
  });

  refresh();
  let lastIdleRefresh = Date.now();
  setInterval(() => {
    if ($("#tab-dashboard").classList.contains("hidden")) return;
    const running = $("#vacation-test-toggle").dataset.running === "true";
    if (running || Date.now() - lastIdleRefresh >= 20000) {
      refresh();
      if (!running) lastIdleRefresh = Date.now();
    }
  }, 1000);
})();
