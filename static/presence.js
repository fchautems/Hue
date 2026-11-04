"use strict";
// Hue Lab v0.6.4 : historique paginé, uniquement en lecture.
(() => {
  const names = Object.freeze({
    light_on: "Allumage",
    light_off: "Extinction",
    zigbee_connected: "Connexion Zigbee",
    zigbee_disconnected: "Déconnexion Zigbee"
  });
  const dateFormat = new Intl.DateTimeFormat("fr-CH", {
    timeZone: "Europe/Zurich", day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false
  });
  const PAGE_SIZE = 40;
  const MAX_PAGE = 250;  // Offset plafonné côté serveur à 10 000 observations.
  let busy = false;
  let page = 0;
  let hasOlder = false;
  const $ = selector => document.querySelector(selector);
  const refreshButton = $("#presence-refresh");
  const newerButton = $("#presence-newer");
  const olderButton = $("#presence-older");
  const pageLabel = $("#presence-page-status");

  function controls() {
    refreshButton.disabled = busy;
    newerButton.disabled = busy || page === 0;
    olderButton.disabled = busy || !hasOlder || page >= MAX_PAGE;
    pageLabel.textContent = "Page " + (page + 1);
  }

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

  function render(items) {
    const body = $("#presence-rows");
    body.replaceChildren();
    if (!items.length) {
      const tr = document.createElement("tr");
      const td = cell(tr, page === 0
        ? "Aucun événement enregistré pour l’instant."
        : "Aucun événement plus ancien.");
      td.colSpan = 3;
      td.className = "presence-empty";
      body.appendChild(tr);
      return;
    }
    for (const item of items) {
      const tr = document.createElement("tr");
      const time = cell(tr, formatDate(item.detected_at));
      time.className = "presence-time";
      cell(tr, item.light_name || "Ampoule");
      const event = cell(tr, names[item.event] || "Événement");
      event.className = "presence-event";
      body.appendChild(tr);
    }
  }

  async function load(targetPage = page) {
    if (busy || targetPage < 0 || targetPage > MAX_PAGE) return;
    busy = true;
    controls();
    try {
      const query = "?limit=" + (PAGE_SIZE + 1) + "&offset=" + (targetPage * PAGE_SIZE);
      const response = await fetch("/api/presence/events" + query, {cache: "no-store"});
      if (!response.ok) throw new Error("HTTP " + response.status);
      const result = await response.json();
      if (result.ok === false || !Array.isArray(result.data)) {
        throw new Error(result.error || "Réponse invalide");
      }
      page = targetPage;
      hasOlder = result.data.length > PAGE_SIZE && page < MAX_PAGE;
      render(result.data.slice(0, PAGE_SIZE));
      $("#presence-status").textContent =
        "Événements " + (result.data.length ? (page * PAGE_SIZE + 1) : 0)
        + " à " + (page * PAGE_SIZE + Math.min(PAGE_SIZE, result.data.length))
        + " · " + (page === 0 ? "Actualisé" : "Archives consultées")
        + " à " + dateFormat.format(new Date()).split(" ").slice(-1)[0];
    } catch (error) {
      $("#presence-status").textContent = "Historique indisponible : " + error.message;
    } finally {
      busy = false;
      controls();
    }
  }

  refreshButton.addEventListener("click", () => load(0));
  newerButton.addEventListener("click", () => load(page - 1));
  olderButton.addEventListener("click", () => load(page + 1));
  window.HuePresence = {refresh: () => load(page)};
  controls();
  setInterval(() => {
    // Ne pas déplacer une page d'archives sous les yeux de l'utilisateur.
    if (page === 0 && !$("#tab-presence").classList.contains("hidden")) load(0);
  }, 15000);
})();
