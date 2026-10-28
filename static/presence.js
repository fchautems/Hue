"use strict";
// Présentation uniquement : aucune commande n'est envoyée aux lampes.
(() => {
  const names = Object.freeze({
    light_on: "Allumage",
    light_off: "Extinction",
    zigbee_connected: "Connexion Zigbee",
    zigbee_disconnected: "Déconnexion Zigbee",
  });
  const dateFormat = new Intl.DateTimeFormat("fr-CH", {
    timeZone: "Europe/Zurich", day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
  let busy = false;
  const $ = (selector) => document.querySelector(selector);

  function formatDate(value) {
    const parsed = new Date(value);
    return Number.isFinite(parsed.getTime()) ? dateFormat.format(parsed) : "—";
  }

  function cell(row, value) {
    const td = document.createElement("td");
    td.textContent = String(value ?? "");
    row.appendChild(td);
    return td;
  }

  function render(rows) {
    const body = $("#presence-rows");
    body.replaceChildren();
    if (!rows.length) {
      const tr = document.createElement("tr");
      const td = cell(tr, "Aucun événement enregistré pour l’instant.");
      td.colSpan = 3;
      td.className = "presence-empty";
      body.appendChild(tr);
      return;
    }
    for (const item of rows) {
      const tr = document.createElement("tr");
      const time = cell(tr, formatDate(item.detected_at));
      time.className = "presence-time";
      cell(tr, item.light_name || "Ampoule");
      const event = cell(tr, names[item.event] || "Événement");
      event.className = "presence-event";
      body.appendChild(tr);
    }
  }

  async function refresh() {
    if (busy) return;
    busy = true;
    const button = $("#presence-refresh");
    button.disabled = true;
    try {
      const response = await fetch("/api/presence/events?limit=40", {cache: "no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      const result = await response.json();
      if (result.ok === false || !Array.isArray(result.data)) {
        throw new Error(result.error || "Réponse invalide");
      }
      render(result.data);
      $("#presence-status").textContent =
        result.data.length + " événement(s) récent(s) · Mis à jour à " +
        dateFormat.format(new Date()).split(" ").slice(-1)[0];
    } catch (error) {
      $("#presence-status").textContent = "Historique indisponible : " + error.message;
    } finally {
      busy = false;
      button.disabled = false;
    }
  }

  $("#presence-refresh").addEventListener("click", refresh);
  window.HuePresence = {refresh};
  setInterval(() => {
    if (!$("#tab-presence").classList.contains("hidden")) refresh();
  }, 15000);
})();
