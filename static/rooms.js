"use strict";
(() => {
  const grid = $("#room-grid");
  const notice = $("#room-notice");
  let groups = [];
  let bridge = null;
  let retryAt = 0;
  let pendingRead = false;
  let failed = false;
  let loaded = false;
  let layout = "";
  let sending = false;
  let controls = [];

  function render(snapshot) {
    const lights = new Map(snapshot.lights.map(light => [light.id, light]));
    const assigned = new Set(groups.flatMap(group => group.light_ids));
    const others = (loaded || failed ? snapshot.lights : []).filter(light => !assigned.has(light.id)).map(light => light.id);
    const cards = others.length
      ? [...groups, {name: failed ? "Toutes les lampes" : "Lampes hors groupe", light_ids: others}]
      : groups;
    const visibleCards = cards.map(group => ({
      ...group, light_ids: group.light_ids.filter(id => lights.has(id)),
    }));
    const key = JSON.stringify(visibleCards.map(group => [
      group.kind, group.name, group.light_ids.map(id => [id, lights.get(id).name]),
    ]));
    if (layout !== key) {
      layout = key;
      controls = [];
      grid.replaceChildren(...visibleCards.map(group => {
        const card = document.createElement("article");
        card.className = "room-card";
        const heading = document.createElement("h2");
        heading.textContent = group.name;
        heading.title = group.name;
        const header = document.createElement("div");
        header.className = "room-card-header";
        header.append(heading, button(group.name, group.light_ids, true));
        const list = document.createElement("div");
        list.className = "room-lamps";
        list.append(...group.light_ids.map(id => button(lights.get(id).name, [id])));
        if (!group.light_ids.length) list.textContent = "Aucune lampe";
        card.append(header, list);
        return card;
      }));
    }
    for (const control of controls) {
      const available = control.ids.map(id => lights.get(id)).filter(light =>
        light?.capabilities.on && light.status !== "disconnected");
      control.targets = available.map(light => light.id);
      const on = available.filter(light => light.on).length;
      const mixed = on > 0 && on < available.length;
      control.on = on > 0;
      control.element.disabled = sending || !snapshot.connected || !available.length;
      control.element.setAttribute("aria-pressed", mixed ? "mixed" : String(control.on));
      control.element.title = control.group
        ? `${control.on ? "Éteindre" : "Allumer"} ${control.name}`
        : control.name;
    }
    notice.textContent = failed ? "Pièces indisponibles sur le pont."
      : !snapshot.connected ? "En attente du pont Hue…"
      : !loaded ? "Recherche des pièces du pont…"
      : !visibleCards.length ? "Aucune pièce ou lampe sur ce pont."
      : "";
  }

  function button(name, ids, group = false) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = group ? "room-power" : "room-lamp";
    element.setAttribute("aria-label", group ? `Commande de groupe · ${name}` : name);
    if (group) {
      element.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 3v8M7.2 5.6a8 8 0 1 0 9.6 0"/></svg>';
    } else {
      const icon = document.createElement("span");
      icon.className = "room-lamp-dot";
      icon.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "room-lamp-label";
      label.textContent = name;
      element.append(icon, label);
    }
    const control = {element, name, ids, group, targets: [], on: false};
    controls.push(control);
    element.addEventListener("click", async () => {
      if (sending || !control.targets.length) return;
      const {targets, on} = control;
      sending = true;
      render(state);
      try {
        const results = await Promise.allSettled(targets.map(id =>
          api(`/api/light/${encodeURIComponent(id)}/switch`, "POST", {on: !on})));
        const rejected = results.filter(result => result.status === "rejected");
        if (rejected.length) {
          showToast(rejected.length === 1 && targets.length === 1 ? rejected[0].reason.message
            : `${targets.length - rejected.length}/${targets.length} commandes envoyées.`, true);
        }
        await refresh();
      } finally {
        sending = false;
        render(state);
      }
    });
    return element;
  }

  async function update(snapshot) {
    if (bridge !== snapshot.bridge_ip) {
      bridge = snapshot.bridge_ip;
      groups = [];
      loaded = false;
      failed = false;
      retryAt = 0;
    }
    render(snapshot);
    if (!snapshot.connected || pendingRead || Date.now() < retryAt) return;
    pendingRead = true;
    const requestedBridge = bridge;
    try {
      const result = await api("/api/lighting-groups");
      if (bridge !== requestedBridge || state.bridge_ip !== requestedBridge) return;
      groups = result;
      loaded = true;
      failed = false;
      retryAt = Date.now() + 30_000;
    } catch {
      if (bridge !== requestedBridge || state.bridge_ip !== requestedBridge) return;
      failed = true;
      retryAt = Date.now() + 5_000;
    } finally {
      pendingRead = false;
      if (activeTab === "rooms") render(state);
    }
  }

  window.HueRooms = {update};
})();
