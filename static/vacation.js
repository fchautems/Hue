"use strict";
(() => {
  const $ = q => document.querySelector(q);
  const prettyDate = new Intl.DateTimeFormat("fr-CH", {timeZone:"Europe/Zurich",
    weekday:"short", day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit", hour12:false});
  let busy = false, selectionInitialized = false, known = [], selected = [];
  let scheduleCache = null, scheduleKey = "", dayIndex = 0;
  const dateText = new Intl.DateTimeFormat("fr-CH", {
    timeZone: "UTC", weekday: "short", day: "2-digit", month: "short"
  });

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

  // L'API transmet le vrai programme stocké sur le Raspberry, sans approximation.
  // Une seule requête par génération de programme (pas à chaque actualisation).
  function renderTimeline() {
    const where = $("#vacation-timeline-body");
    const prev = $("#vacation-day-prev");
    const next = $("#vacation-day-next");
    where.replaceChildren();
    const valid = scheduleCache && scheduleCache.plan_date;
    prev.disabled = !valid || dayIndex === 0;
    next.disabled = !valid || dayIndex === 6;
    if (!valid) {
      $("#vacation-day-label").textContent = "—";
      where.textContent = "Active Vacances pour voir les horaires.";
      return;
    }
    const day = new Date(scheduleCache.plan_date + "T12:00:00Z");
    day.setUTCDate(day.getUTCDate() + dayIndex);
    const dateKey = day.toISOString().slice(0, 10);
    $("#vacation-day-label").textContent = dateText.format(day);
    const dayEvents = (scheduleCache.events || [])
      .filter(event => event.at?.slice(0, 10) === dateKey);
    const selectedLights = (scheduleCache.light_ids || []).map(id => ({
      id, name: known.find(light => light.id === id)?.name || "Lampe"
    }));
    for (const light of selectedLights) {
      const changes = dayEvents.filter(e => e.light_id === light.id)
        .map(e => ({on: e.on === true,
                    minute: Number(e.at.slice(11, 13)) * 60 + Number(e.at.slice(14, 16))}))
        .filter(e => Number.isFinite(e.minute) && e.minute >= 0 && e.minute <= 1440)
        .sort((x, y) => x.minute - y.minute);
      const periods = [];
      let start = null;
      for (const item of changes) {
        if (item.on && start === null) start = item.minute;
        else if (!item.on && start !== null) {
          if (item.minute > start) periods.push([start, item.minute]);
          start = null;
        }
      }
      if (start !== null) periods.push([start, 1440]);

      const row = document.createElement("div");
      row.className = "vacation-lamp-timeline";
      const caption = document.createElement("div");
      caption.className = "vacation-lamp-caption";
      const name = document.createElement("strong");
      name.textContent = light.name;
      const times = document.createElement("span");
      const hhmm = minute => String(Math.floor(minute / 60)).padStart(2,"0")
        + ":" + String(minute % 60).padStart(2,"0");
      times.textContent = periods.length
        ? periods.map(([from, to]) => hhmm(from) + "–" + hhmm(to)).join(" · ")
        : "Aucun allumage prévu";
      caption.append(name, times);
      const track = document.createElement("div");
      track.className = "vacation-lamp-track";
      track.setAttribute("role", "img");
      track.setAttribute("aria-label", light.name + " : " + times.textContent);
      for (const [from, to] of periods) {
        const segment = document.createElement("span");
        segment.className = "vacation-lamp-on";
        segment.style.left = (from / 1440 * 100) + "%";
        segment.style.width = ((to - from) / 1440 * 100) + "%";
        track.appendChild(segment);
      }
      row.append(caption, track);
      where.appendChild(row);
    }
    if (!selectedLights.length) where.textContent = "Aucune lampe sélectionnée.";
  }

  async function syncTimeline(vacation) {
    if (!vacation.enabled) {
      scheduleCache = null;
      scheduleKey = "";
      dayIndex = 0;
      renderTimeline();
      return;
    }
    const key = vacation.plan_date + ":" + vacation.light_ids.join(",");
    if (key !== scheduleKey) {
      try {
        const response = await fetch("/api/vacation/schedule", {cache: "no-store"});
        if (!response.ok) throw new Error("HTTP " + response.status);
        const result = await response.json();
        if (!result.data || !Array.isArray(result.data.events) ||
            result.data.plan_date !== vacation.plan_date) {
          throw new Error("Programme indisponible");
        }
        scheduleCache = result.data;
        scheduleKey = key;
        dayIndex = 0;
      } catch (_error) {
        $("#vacation-timeline-body").textContent = "Planning indisponible. Réessaie dans un instant.";
        return;
      }
    }
    renderTimeline();
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
      await syncTimeline(vacation);
    } catch(e) {
      $("#vacation-feedback").textContent = "Impossible de lire Vacances : " + e.message;
    } finally {busy=false;}
  }

  $("#vacation-day-prev").addEventListener("click", () => {
    if (dayIndex > 0) { dayIndex -= 1; renderTimeline(); }
  });
  $("#vacation-day-next").addEventListener("click", () => {
    if (dayIndex < 6) { dayIndex += 1; renderTimeline(); }
  });

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
