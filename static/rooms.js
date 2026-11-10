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
  function makePlan(cards, lights) {
    const plan=document.createElement("section");
    plan.className="apartment-plan";
    plan.setAttribute("aria-label","Plan interactif de l’appartement");
    const title=document.createElement("div"); title.className="apartment-plan-title"; title.textContent="Plan de l’appartement";
    const surface=document.createElement("div"); surface.className="apartment-plan-surface";
    for (const room of planRooms) {
      const group=cards.find(g=>matchRoom(g.name,room.key));
      const area=document.createElement("div"); area.className="plan-room";
      Object.assign(area.style,{left:room.x+"%",top:room.y+"%",width:room.w+"%",height:room.h+"%"});
      const roomButton=button(room.label,group?.light_ids || [],true);
      roomButton.className="plan-room-action";
      roomButton.textContent=room.label;
      area.append(roomButton);
      const ids=(group?.light_ids || []).filter(id=>lights.has(id));
      const lamps=document.createElement("div"); lamps.className="plan-lamps";
      for(const id of ids) {
        const lamp=button(lights.get(id).name,[id]);
        lamp.className="plan-lamp"; lamp.textContent="●";
        lamp.setAttribute("aria-label","Allumer ou éteindre "+lights.get(id).name);
        lamp.title=lights.get(id).name;
        lamps.append(lamp);
      }
      area.append(lamps);surface.append(area);
    }
    plan.append(title,surface);
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
    const key = JSON.stringify(visibleCards.map(group => [
      group.kind, group.name, group.light_ids.map(id => [id, lights.get(id).name]),
    ]));
    if (layout !== key) {
      layout = key;
      controls = [];
      grid.replaceChildren(makePlan(visibleCards, lights), ...visibleCards.map(group => {
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
      control.element.disabled = waiting || !snapshot.connected || !available.length;
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
