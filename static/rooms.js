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
  let controls = [];
  const planRooms = [
    {key: "salon", label: "Salon", x: 2, y: 2, w: 58, h: 30, columns: 4},
    {key: "cuisine", label: "Cuisine", x: 61, y: 2, w: 37, h: 30, columns: 3},
    {key: "chambre", label: "Chambre", x: 2, y: 34, w: 40, h: 30, columns: 3},
    {key: "bureau", label: "Bureau", x: 2, y: 66, w: 40, h: 32, columns: 3},
    {key: "couloir", label: "Couloir", x: 72, y: 34, w: 26, h: 30, columns: 2},
    {key: "bain", label: "Salle de bain", x: 55, y: 66, w: 43, h: 32, columns: 3},
  ];
  let editMode = false;
  let showCards = false;
  let planConfig = {};
  let storageFailed = false;
  const storageKey = ip => "hue-apartment-plan-v1:" + (ip || "offline");

  function loadConfig(ip) {
    storageFailed = false;
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey(ip)) || "{}");
      planConfig = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch { planConfig = {}; }
  }

  function redraw(focusSelector) {
    layout = "";
    render(state);
    if (focusSelector) grid.querySelector(focusSelector)?.focus({preventScroll: true});
  }

  function saveConfig(focusSelector) {
    try {
      localStorage.setItem(storageKey(bridge), JSON.stringify(planConfig));
      storageFailed = false;
    } catch { storageFailed = true; }
    redraw(focusSelector);
  }

  function roomForLight(id, cards) {
    if (Object.prototype.hasOwnProperty.call(planConfig, id)) {
      const saved = planConfig[id]?.room;
      return planRooms.some(room => room.key === saved) ? saved : "";
    }
    const group = cards.find(card => card.kind === "room" && card.light_ids.includes(id));
    if (!group) return "";
    const words = group.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().split(/[^a-z]+/);
    return planRooms.find(room => room.key === "bain"
      ? words.some(word => ["bain", "bains", "douche", "wc"].includes(word))
      : words.includes(room.key))?.key || "";
  }

  function closestSlot(slots, x, y) {
    return slots.reduce((best, slot) => {
      const distance = (slot.x - x) ** 2 + (slot.y - y) ** 2;
      return !best || distance < best.distance ? {slot, distance} : best;
    }, null)?.slot;
  }

  function placeLamps(room, lamps) {
    const slots = Array.from({length: room.columns * 2}, (_, index) => {
      const column = index % room.columns;
      const row = Math.floor(index / room.columns);
      return {column, row, x: (column + 0.5) * 100 / room.columns, y: (row + 0.5) * 50};
    });
    const hasPosition = light => Number.isFinite(planConfig[light.id]?.x) && Number.isFinite(planConfig[light.id]?.y);
    for (const light of [...lamps.filter(hasPosition), ...lamps.filter(light => !hasPosition(light))]) {
      const free = slots.filter(slot => !slot.light);
      if (!free.length) break;
      const point = planConfig[light.id];
      const slot = hasPosition(light) ? closestSlot(free, point.x, point.y) : free[0];
      slot.light = light;
    }
    return slots;
  }

  function enableLampMove(lamp, room, layer, slots, current) {
    const id = current.light.id;
    const savePosition = next => {
      if (!next || next === current) return;
      // Swapping keeps both lamps reachable, even when every slot is occupied.
      if (next.light) planConfig[next.light.id] = {room: room.key, x: current.x, y: current.y};
      planConfig[id] = {room: room.key, x: next.x, y: next.y};
      saveConfig(`[data-plan-lamp="${CSS.escape(id)}"]`);
    };
    lamp.addEventListener("keydown", event => {
      const step = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
      if (!step) return;
      event.preventDefault();
      savePosition(slots.find(slot => slot.column === current.column + step[0] && slot.row === current.row + step[1]));
    });
    lamp.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      lamp.setPointerCapture(event.pointerId);
      const move = next => {
        lamp.style.translate = `${next.clientX - event.clientX}px ${next.clientY - event.clientY}px`;
      };
      const cancel = () => {
        lamp.style.translate = "";
        lamp.removeEventListener("pointermove", move);
        lamp.removeEventListener("pointerup", stop);
        lamp.removeEventListener("lostpointercapture", cancel);
      };
      const stop = next => {
        cancel();
        if (Math.hypot(next.clientX - event.clientX, next.clientY - event.clientY) < 5) return;
        const rect = layer.getBoundingClientRect();
        const x = (next.clientX - rect.left) / rect.width * 100;
        const y = (next.clientY - rect.top) / rect.height * 100;
        savePosition(closestSlot(slots, x, y));
      };
      lamp.addEventListener("pointermove", move);
      lamp.addEventListener("pointerup", stop);
      lamp.addEventListener("lostpointercapture", cancel);
    });
  }

  function makePlan(cards, lights) {
    const plan = document.createElement("section");
    plan.className = "apartment-plan";
    plan.setAttribute("aria-labelledby", "apartment-plan-title");
    const title = document.createElement("h2");
    title.id = "apartment-plan-title";
    title.textContent = "Plan de l’appartement";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "plan-edit-toggle";
    edit.textContent = editMode ? "Terminer" : "Modifier le plan";
    edit.setAttribute("aria-pressed", String(editMode));
    edit.addEventListener("click", () => { editMode = !editMode; redraw(".plan-edit-toggle"); });
    const header = document.createElement("div");
    header.className = "plan-header";
    header.append(title, edit);
    const surface = document.createElement("div");
    surface.className = "apartment-plan-surface";
    const outside = document.createElement("div");
    outside.className = "plan-outside";
    outside.textContent = "Parties communes";
    surface.append(outside);

    const entries = [...lights.values()];
    const assignments = new Map(entries.map(light => [light.id, roomForLight(light.id, cards)]));
    let visibleLamps = 0;
    for (const room of planRooms) {
      const roomLamps = entries.filter(light => assignments.get(light.id) === room.key);
      const area = document.createElement("div");
      area.className = "plan-room";
      area.dataset.planRoom = room.key;
      Object.assign(area.style, {left: `${room.x}%`, top: `${room.y}%`, width: `${room.w}%`, height: `${room.h}%`});
      const roomButton = button(room.label, roomLamps.map(light => light.id), true, "plan-room-action");
      roomButton.textContent = room.label;
      roomButton.setAttribute("aria-label", `Allumer ou éteindre la pièce · ${room.label}`);
      const layer = document.createElement("div");
      layer.className = "plan-lamps";
      layer.style.setProperty("--plan-columns", room.columns);
      const slots = placeLamps(room, roomLamps);
      for (const slot of slots) {
        if (!slot.light) continue;
        visibleLamps++;
        const {id, name} = slot.light;
        const lamp = button(name, [id], false, "plan-lamp");
        lamp.dataset.planLamp = id;
        lamp.style.gridArea = `${slot.row + 1} / ${slot.column + 1}`;
        lamp.setAttribute("aria-label", (editMode ? "Déplacer " : "Allumer ou éteindre ") + name);
        if (editMode) enableLampMove(lamp, room, layer, slots, slot);
        layer.append(lamp);
      }
      area.append(roomButton, layer);
      surface.append(area);
    }
    plan.append(header, surface);
    if (editMode) {
      const editor = document.createElement("div");
      editor.className = "plan-editor";
      const help = document.createElement("p");
      help.textContent = "Choisis la pièce de chaque lampe, puis déplace son repère au doigt ou avec les flèches du clavier. Les positions sont enregistrées sur cet appareil.";
      editor.append(help);
      for (const light of entries) {
        const label = document.createElement("label");
        label.textContent = light.name;
        const select = document.createElement("select");
        select.dataset.planAssignment = light.id;
        select.setAttribute("aria-label", "Pièce de " + light.name);
        for (const option of [{key: "", label: "Hors plan"}, ...planRooms]) {
          select.append(new Option(option.label, option.key));
        }
        select.value = assignments.get(light.id);
        select.addEventListener("change", () => {
          planConfig[light.id] = {room: select.value};
          saveConfig(`[data-plan-assignment="${CSS.escape(light.id)}"]`);
        });
        label.append(select);
        editor.append(label);
      }
      plan.append(editor);
    }
    return {plan, outsideCount: entries.length - visibleLamps};
  }

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
    const key = JSON.stringify([editMode, showCards, planConfig, snapshot.lights.map(light => [light.id, light.name]), visibleCards.map(group => [
      group.kind, group.name, group.light_ids,
    ])]);
    if (layout !== key) {
      layout = key;
      controls = [];
      const {plan, outsideCount} = makePlan(visibleCards, lights);
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "plan-cards-toggle";
      toggle.textContent = showCards ? "Masquer la liste des pièces" : "Afficher la liste des pièces";
      if (!showCards && outsideCount) toggle.textContent += ` · ${outsideCount} hors plan`;
      toggle.setAttribute("aria-expanded", String(showCards));
      toggle.addEventListener("click", () => { showCards = !showCards; redraw(".plan-cards-toggle"); });
      grid.classList.toggle("plan-cards-expanded", showCards);
      grid.replaceChildren(plan, toggle, ...visibleCards.map(group => {
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
      const waiting = control.ids.some(id => pendingPower.has(id));
      const moving = editMode && control.element.classList.contains("plan-lamp");
      control.element.disabled = !moving && (waiting || !snapshot.connected || !available.length
        || (editMode && control.element.classList.contains("plan-room-action")));
      control.element.setAttribute("aria-busy", String(waiting));
      control.element.setAttribute("aria-pressed", mixed ? "mixed" : String(control.on));
      control.element.title = control.group
        ? `${control.on ? "Éteindre" : "Allumer"} ${control.name}`
        : control.name;
    }
    notice.textContent = storageFailed ? "Impossible de sauvegarder le plan sur cet appareil."
      : failed ? "Pièces indisponibles sur le pont."
      : !snapshot.connected ? "En attente du pont Hue…"
      : !loaded ? "Recherche des pièces du pont…"
      : !visibleCards.length ? "Aucune pièce ou lampe sur ce pont."
      : "";
  }

  function button(name, ids, group = false, planClass = "") {
    const element = document.createElement("button");
    element.type = "button";
    element.className = planClass || (group ? "room-power" : "room-lamp");
    element.setAttribute("aria-label", group ? `Commande de groupe · ${name}` : name);
    if (!planClass && group) {
      element.innerHTML = '<span class="switch" aria-hidden="true"><span></span></span>';
    } else if (!planClass) {
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
    element.addEventListener("click", () => {
      if (!planClass || !editMode) changePower(control.targets, !control.on);
    });
    return element;
  }

  async function update(snapshot) {
    if (bridge !== snapshot.bridge_ip) {
      loadConfig(snapshot.bridge_ip);
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

  window.HueRooms = {update, render};
})();
