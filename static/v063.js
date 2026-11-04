/* Hue Lab v0.6.3 — copie explicite du profil complet entre lampes. */
"use strict";
(() => {
  const lamp = document.querySelector("#profile-light");
  const row = document.querySelector("#tab-profiles .v062-copy-row");
  if (!lamp || !row) return;
  const source = row.querySelector("#v062-copy-source");
  const curveButton = row.querySelector("#v062-copy");
  const help = row.querySelector("small");
  if (!source || !help) return;

  const button = document.createElement("button");
  button.id = "v063-copy-full";
  button.type = "button";
  button.className = "btn muted";
  button.textContent = "Copier le profil complet";
  row.insertBefore(button, help);
  help.textContent = "Courbe : luminosité seule. Profil complet : courbes et couleurs automatiques compatibles. Modes Manuel/Auto, état allumé/éteint et Vacances sont préservés.";
  let busy = false;

  function sync() {
    button.disabled = busy || !source.value || !lamp.value || source.value === lamp.value;
  }
  lamp.addEventListener("change", sync);
  source.addEventListener("change", sync);
  new MutationObserver(sync).observe(lamp, {childList: true});
  new MutationObserver(sync).observe(source, {childList: true});
  sync();

  button.addEventListener("click", () => safe(async () => {
    if (busy || !source.value || !selectedId || source.value === selectedId) return;
    if (curveButton && curveButton.disabled) return;
    if (window.HueProfiles?.hasUnsaved() || window.HueRGB?.hasChanges()) {
      throw Error("Enregistre ou annule les modifications en cours avant de copier le profil.");
    }
    const fromId = source.value;
    const toId = selectedId;
    const name = uid => [...lamp.options].find(option => option.value === uid)?.textContent || uid;
    const message = "Copier le profil de « " + name(fromId) + " » vers « " + name(toId) + " » ?\n"
      + "La courbe et les couleurs automatiques enregistrées seront remplacées (si compatibles). "
      + "Le mode Manuel/Auto et l'état allumé/éteint restent inchangés. "
      + "Si la destination est déjà en Auto, le nouveau profil peut être appliqué immédiatement.";
    if (!window.confirm(message)) return;
    if (selectedId !== toId || source.value !== fromId) {
      throw Error("La sélection a changé. Copie annulée.");
    }

    busy = true;
    sync();
    if (curveButton) curveButton.disabled = true;
    try {
      await api("/api/profile/copy/" + encodeURIComponent(toId), "POST", {source_uid: fromId});
      if (selectedId === toId) {
        await window.HueProfiles?.reload();
        window.HueRGB?.reloadIfClean(toId);
        await refresh();
      }
      showToast("Profil complet copié. Vérifie les couleurs et la courbe en mode Auto.");
    } finally {
      busy = false;
      if (curveButton) curveButton.disabled = !source.value || !lamp.value;
      sync();
    }
  }));
})();
