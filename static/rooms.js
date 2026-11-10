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
    {key:"salon", label:"Salon", x:2,y:2,w:58,h:30},
    {key:"cuisine",label:"Cuisine",x:61,y:2,w:37,h:30},
    {key:"chambre",label:"Chambre",x:2,y:34,w:40,h:30},
    {key:"bureau",label:"Bureau",x:2,y:66,w:40,h:32},
    {key:"couloir",label:"Couloir",x:72,y:34,w:26,h:30},
    {key:"bain",label:"Salle de bain",x:55,y:66,w:43,h:32},
  ];
  const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
  function matchRoom(name, key) {
    const n=normalize(name);
    return key==="bain" ? /bain|douche|wc/.test(n) : n.includes(key);
  }
  let editMode = false;
  let showCards = false;
  let planConfig = {};
  let configBridge = "";
  const storageKey = ip => "hue-apartment-plan-v1:" + (ip || "offline");
  function loadConfig(ip) {
    configBridge = ip || "";
    try {
      const parsed = JSON.parse(localStorage.getItem(storageKey(configBridge)) || "{}");
      planConfig = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch { planConfig = {}; }
  }
  function saveConfig() {
    try { localStorage.setItem(storageKey(configBridge), JSON.stringify(planConfig)); }
    catch { notice.textContent = "Impossible de sauvegarder le plan sur cet appareil."; }
    layout = "";
    if (state) render(state);
  }
  function roomForLight(id, cards) {
    const saved = planConfig[id]?.room;
    if (Object.prototype.hasOwnProperty.call(planConfig, id)) return planRooms.some(r => r.key === saved) ? saved : "";
    const group = cards.find(g => g.light_ids.includes(id) && planRooms.some(r => matchRoom(g.name, r.key)));
    return group ? planRooms.find(r => matchRoom(group.name, r.key)).key : "";
  }
  function makePlan(cards, lights) {
    const plan = document.createElement("section");
    plan.className = "apartment-plan";
    plan.setAttribute("aria-label", "Plan interactif de l’appartement");
    const title = document.createElement("div");
    title.className = "apartment-plan-title";
    title.textContent = "Plan de l’appartement";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.className = "plan-edit-toggle";
    edit.textContent = editMode ? "Terminer" : "Modifier le plan";
    edit.setAttribute("aria-pressed", String(editMode));
    edit.addEventListener("click", () => { editMode = !editMode; layout = ""; render(state); });
    const header = document.createElement("div");
    header.className = "plan-header";
    header.append(title, edit);
    const surface = document.createElement("div");
    surface.className = "apartment-plan-surface";
    const entries = [...lights.values()];
    for (const room of planRooms) {
      const ids = entries.filter(light => roomForLight(light.id, cards) === room.key).map(light => light.id);
      const area = document.createElement("div");
      area.className = "plan-room";
      Object.assign(area.style, {left:room.x+"%",top:room.y+"%",width:room.w+"%",height:room.h+"%"});
      const roomButton = button(room.label, ids, true);
      roomButton.className = "plan-room-action";
      roomButton.textContent = room.label;
      if (editMode) roomButton.disabled = true;
      area.append(roomButton);
      const lamps = document.createElement("div");
      lamps.className = "plan-lamps";
      ids.forEach((id, index) => {
        const light = lights.get(id);
        const lamp = button(light.name, [id]);
        lamp.className = "plan-lamp";
        lamp.textContent = "●";
        lamp.setAttribute("aria-label", "Allumer ou éteindre " + light.name);
        lamp.title = light.name;
        const point = planConfig[id];
        if (point && Number.isFinite(point.x) && Number.isFinite(point.y)) {
          lamp.style.left = Math.max(3, Math.min(97, point.x)) + "%";
          lamp.style.top = Math.max(5, Math.min(95, point.y)) + "%";
        } else {
          lamp.style.left = (20 + (index % 3) * 30) + "%";
          lamp.style.top = (65 + Math.floor(index / 3) * 20) + "%";
        }
        if (editMode) {
          lamp.disabled = false;
          lamp.classList.add("plan-lamp-draggable");
          lamp.addEventListener("pointerdown", event => {
            if (event.button !== 0) return;
            event.preventDefault();
            lamp.setPointerCapture(event.pointerId);
            const move = e => {
              const rect = area.getBoundingClientRect();
              const x = Math.max(3, Math.min(97, (e.clientX-rect.left)/rect.width*100));
              const y = Math.max(5, Math.min(95, (e.clientY-rect.top)/rect.height*100));
              lamp.style.left = x+"%"; lamp.style.top = y+"%";
            };
            const stop = e => {
              move(e);
              lamp.removeEventListener("pointermove", move);
              lamp.removeEventListener("pointerup", stop);
              lamp.removeEventListener("pointercancel", cancel);
              planConfig[id] = {...planConfig[id], room:room.key, x:parseFloat(lamp.style.left), y:parseFloat(lamp.style.top)};
              saveConfig();
            };
            const cancel = () => {lamp.removeEventListener("pointermove",move);lamp.removeEventListener("pointerup",stop);lamp.removeEventListener("pointercancel",cancel);};
            lamp.addEventListener("pointermove",move);
            lamp.addEventListener("pointerup",stop);
            lamp.addEventListener("pointercancel",cancel);
          });
          lamp.addEventListener("click", e => e.stopImmediatePropagation(), true);
        }
        area.append(lamp);
      });
      surface.append(area);
    }
    plan.append(header,surface);
    if (editMode) {
      const editor = document.createElement("div");
      editor.className = "plan-editor";
      const help = document.createElement("p");
      help.textContent = "Choisis la pièce de chaque lampe, puis déplace son point dans la pièce. Les réglages sont conservés sur cet appareil.";
      editor.append(help);
      for (const light of entries) {
        const label = document.createElement("label");
        label.textContent = light.name + " ";
        const select = document.createElement("select");
        select.setAttribute("aria-label", "Pièce de " + light.name);
        for (const option of [{key:"",label:"Hors plan"}, ...planRooms]) {
          const node = document.createElement("option");
          node.value = option.key; node.textContent = option.label;
          select.append(node);
        }
        select.value = roomForLight(light.id, cards);
        select.addEventListener("change", () => {
          planConfig[light.id] = {room:select.value};
          saveConfig();
        });
        label.append(select); editor.append(label);
      }
      plan.append(editor);
    }
    return plan;
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
    const key = JSON.stringify([editMode, showCards, planConfig, [...lights.keys()], visibleCards.map(group => [
      group.kind, group.name, group.light_ids.map(id => [id, lights.get(id).name]),
    ])]);
    if (layout !== key) {
      layout = key;
      controls = [];
      const toggle = document.createElement("button");
      toggle.type = "button"; toggle.className = "plan-cards-toggle";
      toggle.textContent = showCards ? "Masquer la liste des pièces" : "Afficher la liste des pièces";
      toggle.setAttribute("aria-expanded", String(showCards));
      toggle.addEventListener("click", () => { showCards = !showCards; layout = ""; render(state); });
      grid.classList.toggle("plan-cards-expanded", showCards);
      grid.replaceChildren(makePlan(visibleCards, lights), toggle, ...visibleCards.map(group => {
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
      control.element.disabled = (editMode && control.element.classList.contains("plan-room-action")) || waiting || !snapshot.connected || !available.length;
      control.element.setAttribute("aria-busy", String(waiting));
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
      element.innerHTML = '<span class="switch" aria-hidden="true"><span></span></span>';
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
    element.addEventListener("click", () => changePower(control.targets, !control.on));
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
