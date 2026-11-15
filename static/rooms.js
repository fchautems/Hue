"use strict";
(() => {
  const grid = $("#room-grid");
  const planHost = $("#room-plan");
  const notice = $("#room-notice");
  let groups = [];
  let bridge = null;
  let retryAt = 0;
  let pendingRead = false;
  let failed = false;
  let loaded = false;
  let layout = "";
  let controls = [];
  // Un seul repère pour les pièces et leurs murs, en pourcentage de la surface.
  const left = 1, right = 99, top = 1, bottom = 99.5, cornerRadius = 2;
  const kitchenX = 55, bedroomRight = 53, voidLeft = 28, officeRight = 74;
  const upperY = 29, voidTop = 54.3, bedroomBottom = 62, voidBottom = 71, bathTop = 84;
  const planRooms = [
    {key: "salon", label: "Salon", x: left, y: top, right: kitchenX, bottom: upperY, columns: 4,
      anchors: [{x: 44, y: 23}, {x: 15, y: 76}]},
    {key: "cuisine", label: "Cuisine", x: kitchenX, y: top, right, bottom: upperY, columns: 3},
    {key: "chambre", label: "Chambre", x: left, y: upperY, right: bedroomRight, bottom: bedroomBottom, columns: 3,
      points: [[left, upperY], [bedroomRight, upperY], [bedroomRight, voidTop],
        [voidLeft, voidTop], [voidLeft, bedroomBottom], [left, bedroomBottom]], anchors: [{x: 62, y: 17}]},
    {key: "couloir", label: "Couloir", x: bedroomRight, y: upperY, right, bottom: bathTop, columns: 3,
      points: [[bedroomRight, upperY], [right, upperY], [right, bathTop],
        [officeRight, bathTop], [officeRight, voidTop], [bedroomRight, voidTop]],
      anchors: [{x: 63, y: 23}, {x: 78, y: 73}]},
    {key: "bureau", label: "Bureau", x: left, y: bedroomBottom, right: officeRight, bottom, columns: 5,
      points: [[left, bedroomBottom], [voidLeft, bedroomBottom], [voidLeft, voidBottom],
        [officeRight, voidBottom], [officeRight, bottom], [left, bottom]]},
    {key: "bain", label: "Salle de bain", shortLabel: "Bain", x: officeRight, y: bathTop, right, bottom, columns: 2},
  ].map(room => {
    const w = room.right - room.x;
    const h = room.bottom - room.y;
    const outline = room.points?.map(([x, y]) => [(x - room.x) / w * 100, (y - room.y) / h * 100]);
    return {...room, w, h, outline};
  });

  function drawWalls() {
    const namespace = "http://www.w3.org/2000/svg";
    const walls = document.createElementNS(namespace, "svg");
    walls.classList.add("plan-walls");
    walls.setAttribute("viewBox", "0 0 100 100");
    walls.setAttribute("preserveAspectRatio", "none");
    walls.setAttribute("aria-hidden", "true");

    const perimeter = document.createElementNS(namespace, "rect");
    for (const [name, value] of Object.entries({
      x: left, y: top, width: right - left, height: bottom - top, rx: cornerRadius, ry: cornerRadius,
    })) perimeter.setAttribute(name, value);
    perimeter.setAttribute("vector-effect", "non-scaling-stroke");

    const solid = document.createElementNS(namespace, "path");
    solid.setAttribute("d", [
      `M ${left} ${upperY} H ${right}`,
      `M ${bedroomRight} ${upperY} V ${voidTop}`,
      `M ${left} ${bedroomBottom} H ${voidLeft}`,
      `M ${voidLeft} ${voidBottom} H ${officeRight}`,
      `M ${voidLeft} ${voidBottom} V ${voidTop} H ${officeRight} V ${bottom}`,
      `M ${officeRight} ${bathTop} H ${right}`,
    ].join(" "));
    const divider = document.createElementNS(namespace, "path");
    divider.classList.add("plan-open-divider");
    divider.setAttribute("d", `M ${kitchenX} ${top} V ${upperY}`);
    for (const path of [solid, divider]) path.setAttribute("vector-effect", "non-scaling-stroke");
    walls.append(perimeter, solid, divider);
    return walls;
  }

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
    if (focusSelector) (planHost.querySelector(focusSelector) || grid.querySelector(focusSelector))?.focus({preventScroll: true});
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

  function insideOutline(outline, x, y) {
    let inside = false;
    for (let i = 0, j = outline.length - 1; i < outline.length; j = i++) {
      const [aX, aY] = outline[i];
      const [bX, bY] = outline[j];
      if ((aY > y) !== (bY > y) && x < (bX - aX) * (y - aY) / (bY - aY) + aX) inside = !inside;
    }
    return inside;
  }

  function markerFits(room, point, width = room.w * 3 - 6, height = room.h * 3.2 - 19) {
    if (!room.outline) return true;
    const x = Math.max(16, Math.min(width - 16, point.x * width / 100)) + 3;
    const y = Math.max(16, Math.min(height - 16, point.y * height / 100)) + 18;
    return [-15, 15].every(dx => [-15, 15].every(dy =>
      insideOutline(room.outline, (x + dx) * 100 / (width + 6), (y + dy) * 100 / (height + 19))));
  }

  function placeLamps(room, lamps) {
    // Use the dimensions at 320 px so new markers are individually touchable on narrow screens.
    const width = room.w * 3 - 6;
    const height = room.h * 3.2 - 19;
    const separated = (a, b) => Math.hypot((a.x - b.x) * width / 100, (a.y - b.y) * height / 100) >= 32;
    const defaults = [...(room.anchors || []), ...Array.from({length: room.columns * 2}, (_, index) => ({
      x: (index % room.columns + 0.5) * 100 / room.columns,
      y: index < room.columns ? 25 : 75,
    }))];
    const extra = [];
    for (let y = 16; y <= height - 16; y += 8) {
      for (let x = 16; x <= width - 16; x += 8) extra.push({x: x / width * 100, y: y / height * 100});
    }
    const placed = new Map();
    for (const light of lamps) {
      const point = planConfig[light.id];
      if (Number.isFinite(point?.x) && Number.isFinite(point.y) && markerFits(room, point, width, height)) placed.set(light.id, point);
    }
    for (const light of lamps) {
      if (placed.has(light.id)) continue;
      const available = point => markerFits(room, point, width, height)
        && [...placed.values()].every(other => separated(point, other));
      const point = defaults.find(available) || extra.find(available);
      if (point) placed.set(light.id, point);
    }
    return placed;
  }

  function setMarkerPosition(lamp, point) {
    lamp.style.setProperty("--lamp-x", `${point.x}%`);
    lamp.style.setProperty("--lamp-y", `${point.y}%`);
  }

  function enableLampMove(lamp, room, layer, feedback) {
    function clampPoint(x, y, rect) {
      const inset = lamp.offsetWidth / 2;
      return {
        x: Math.min(rect.width - inset, Math.max(inset, x)),
        y: Math.min(rect.height - inset, Math.max(inset, y)),
      };
    }
    function center(button, rect) {
      const box = button.getBoundingClientRect();
      return {x: box.left - rect.left + box.width / 2, y: box.top - rect.top + box.height / 2};
    }
    function asPercent(point, rect) {
      return {x: point.x / rect.width * 100, y: point.y / rect.height * 100};
    }
    function savePosition(point, rect) {
      const normalized = asPercent(point, rect);
      if (!markerFits(room, normalized, rect.width, rect.height) || !markerFits(room, normalized)) return;
      const collision = [...layer.children].some(other => {
        if (other === lamp) return false;
        const at = center(other, rect);
        return Math.hypot(at.x - point.x, at.y - point.y) < lamp.offsetWidth - 0.5;
      });
      if (collision) {
        feedback.textContent = "Laisse un peu d’espace entre les repères pour pouvoir les toucher séparément.";
        return;
      }
      const id = lamp.dataset.planLamp;
      planConfig[id] = {room: room.key, ...normalized};
      saveConfig(`[data-plan-lamp="${CSS.escape(id)}"]`);
    }
    lamp.addEventListener("keydown", event => {
      const direction = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1]}[event.key];
      if (!direction) return;
      event.preventDefault();
      const rect = layer.getBoundingClientRect();
      const at = center(lamp, rect);
      const step = event.shiftKey ? 10 : 2;
      savePosition(clampPoint(at.x + direction[0] * step, at.y + direction[1] * step, rect), rect);
    });
    lamp.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      const rect = layer.getBoundingClientRect();
      const start = center(lamp, rect);
      const initial = {x: lamp.style.getPropertyValue("--lamp-x"), y: lamp.style.getPropertyValue("--lamp-y")};
      let lastInside = start;
      const destination = next => {
        const point = clampPoint(start.x + next.clientX - event.clientX, start.y + next.clientY - event.clientY, rect);
        const normalized = asPercent(point, rect);
        if (markerFits(room, normalized, rect.width, rect.height) && markerFits(room, normalized)) lastInside = point;
        return lastInside;
      };
      lamp.setPointerCapture(event.pointerId);
      lamp.classList.add("plan-lamp-moving");
      feedback.textContent = lamp.title;
      const move = next => setMarkerPosition(lamp, asPercent(destination(next), rect));
      const cancel = () => {
        lamp.style.setProperty("--lamp-x", initial.x);
        lamp.style.setProperty("--lamp-y", initial.y);
        lamp.classList.remove("plan-lamp-moving");
        lamp.removeEventListener("pointermove", move);
        lamp.removeEventListener("pointerup", stop);
        lamp.removeEventListener("lostpointercapture", cancel);
      };
      const stop = next => {
        cancel();
        if (Math.hypot(next.clientX - event.clientX, next.clientY - event.clientY) >= 2) {
          savePosition(destination(next), rect);
        }
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
    const feedback = document.createElement("p");
    feedback.className = "plan-feedback";
    feedback.setAttribute("role", "status");
    feedback.textContent = "Fais glisser un repère dans sa pièce. Au clavier, utilise les flèches.";

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
      const radius = `${cornerRadius / room.w * 100}% ${cornerRadius / room.h * 100}%`;
      if (room.x === left && room.y === top) roomButton.style.borderTopLeftRadius = radius;
      if (room.right === right && room.y === top) roomButton.style.borderTopRightRadius = radius;
      if (room.x === left && room.bottom === bottom) roomButton.style.borderBottomLeftRadius = radius;
      if (room.right === right && room.bottom === bottom) roomButton.style.borderBottomRightRadius = radius;
      roomButton.textContent = room.label;
      if (room.shortLabel) {
        const full = document.createElement("span");
        full.className = "plan-room-label-long";
        full.textContent = room.label;
        const short = document.createElement("span");
        short.className = "plan-room-label-short";
        short.textContent = room.shortLabel;
        roomButton.replaceChildren(full, short);
      }
      if (room.outline) {
        roomButton.classList.add("plan-room-shaped");
        roomButton.style.clipPath = `polygon(${room.outline.map(([x, y]) => `${x}% ${y}%`).join(", ")})`;
      }
      area.append(roomButton);
      roomButton.setAttribute("aria-label", `Allumer ou éteindre la pièce · ${room.label}`);
      const layer = document.createElement("div");
      layer.className = "plan-lamps";
      for (const [id, point] of placeLamps(room, roomLamps)) {
        visibleLamps++;
        const {name} = lights.get(id);
        const lamp = button(name, [id], false, "plan-lamp");
        lamp.dataset.planLamp = id;
        setMarkerPosition(lamp, point);
        lamp.setAttribute("aria-label", (editMode ? "Déplacer " : "Allumer ou éteindre ") + name);
        if (editMode) enableLampMove(lamp, room, layer, feedback);
        layer.append(lamp);
      }
      area.append(layer);
      surface.append(area);
    }
    surface.append(drawWalls());
    plan.append(header);
    if (editMode) plan.append(feedback);
    plan.append(surface);
    if (editMode) {
      const editor = document.createElement("div");
      editor.className = "plan-editor";
      const help = document.createElement("p");
      help.textContent = "Tu peux changer la pièce de chaque lampe. Les positions sont enregistrées sur cet appareil.";
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
      planHost.replaceChildren(plan);
      grid.replaceChildren(toggle, ...visibleCards.map(group => {
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
