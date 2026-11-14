"use strict";
(() => {
  const lamp = document.querySelector("#profile-light");
  const target = document.querySelector("#profile-copy-target");
  const button = document.querySelector("#v063-copy-full");
  const details = button.closest("details");
  let busy = false;

  function sync() {
    const previous = target.value;
    const others = [...lamp.options].filter(option => option.value && option.value !== lamp.value);
    target.replaceChildren(new Option("Choisir une lampe", ""), ...others.map(
      option => new Option(option.textContent, option.value)
    ));
    target.value = others.some(option => option.value === previous) ? previous : "";
    details.hidden = others.length === 0;
    target.disabled = busy;
    button.disabled = busy || !target.value;
  }
  lamp.addEventListener("change", () => { target.value = ""; sync(); });
  target.addEventListener("change", () => { button.disabled = !target.value; });
  new MutationObserver(sync).observe(lamp, {childList: true});
  sync();

  button.addEventListener("click", () => safe(async () => {
    const fromId = selectedId;
    const toId = target.value;
    if (busy || !fromId || !target.selectedOptions[0] || !toId || fromId === toId) return;
    if (window.HueProfiles?.hasUnsaved() || window.HueRGB?.hasChanges()) {
      throw Error("Enregistre ou annule les modifications en cours avant de copier le profil.");
    }
    const from = lamp.selectedOptions[0].textContent;
    const to = target.selectedOptions[0].textContent;
    if (!window.confirm(`Copier le profil de « ${from} » vers « ${to} » ? La courbe et les couleurs automatiques compatibles de la destination seront remplacées.`)) return;
    busy = true;
    sync();
    try {
      await api("/api/profile/copy/" + encodeURIComponent(toId), "POST", {source_uid: fromId});
      if (selectedId === toId && !window.HueProfiles?.hasUnsaved() && !window.HueRGB?.hasChanges()) {
        await window.HueProfiles?.reload();
        window.HueRGB?.reloadIfClean(toId);
      }
      await refresh();
      details.open = false;
      target.value = "";
      showToast("Profil complet copié.");
    } finally {
      busy = false;
      sync();
    }
  }));
})();
