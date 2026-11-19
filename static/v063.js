"use strict";
(() => {
  const lamp = $("#profile-light");
  const panel = $("#profile-copy");
  const apply = $("#profile-copy-apply");
  const take = $("#profile-copy-take");
  const source = take.elements.source;
  const all = $("#profile-copy-all");
  const targets = $("#profile-copy-targets");
  let busy = false;

  function updateButtons() {
    const boxes = [...targets.querySelectorAll("input")];
    const checked = boxes.filter(box => box.checked).length;
    all.checked = checked > 0 && checked === boxes.length;
    all.indeterminate = checked > 0 && checked < boxes.length;
    apply.querySelector("button").disabled = busy || checked === 0;
    take.querySelector("button").disabled = busy || !source.value;
  }

  function fillChoices(reset = false) {
    const previous = reset ? "" : source.value;
    const selected = new Set(reset ? [] : [...targets.querySelectorAll("input:checked")].map(box => box.value));
    const others = lamp.value ? [...lamp.options].filter(option => option.value && option.value !== lamp.value) : [];
    source.replaceChildren(new Option("Choisir une lampe", ""), ...others.map(
      option => new Option(option.textContent, option.value)
    ));
    if (others.some(option => option.value === previous)) source.value = previous;
    targets.replaceChildren(...others.map(option => {
      const label = document.createElement("label");
      label.className = "profile-copy-choice";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.value = option.value;
      box.checked = selected.has(option.value);
      label.append(box, option.textContent);
      return label;
    }));
    panel.hidden = others.length === 0;
    updateButtons();
  }

  async function copy(form, from, to) {
    if (busy || !from || !to.length) return;
    if (window.HueProfiles?.hasUnsaved() || window.HueRGB?.hasChanges()) {
      throw Error("Enregistre ou annule les modifications en cours avant de copier.");
    }
    const current = lamp.value;
    const scope = form.elements.scope.value;
    busy = true;
    const elements = [...apply.elements, ...take.elements, ...targets.querySelectorAll("input")];
    elements.forEach(element => { element.disabled = true; });
    try {
      await api("/api/profile/copy", "POST", {source_uid: from, target_uids: to, scope});
      if (to.includes(current) && lamp.value === current
          && !window.HueProfiles?.hasUnsaved() && !window.HueRGB?.hasChanges()) {
        await window.HueProfiles?.reload();
        window.HueRGB?.reloadIfClean(current);
      }
      await refresh();
      form.closest("details").open = false;
      fillChoices(true);
      showToast(to.length === 1 ? "Réglages copiés." : `Réglages copiés sur ${to.length} lampes.`);
    } finally {
      elements.forEach(element => { element.disabled = false; });
      busy = false;
      updateButtons();
    }
  }

  all.addEventListener("change", () => {
    for (const box of targets.querySelectorAll("input")) box.checked = all.checked;
  });
  apply.addEventListener("change", updateButtons);
  take.addEventListener("change", updateButtons);
  apply.addEventListener("submit", event => {
    event.preventDefault();
    safe(() => copy(apply, lamp.value, [...targets.querySelectorAll("input:checked")].map(box => box.value)));
  });
  take.addEventListener("submit", event => {
    event.preventDefault();
    safe(() => copy(take, source.value, [lamp.value]));
  });
  lamp.addEventListener("change", () => fillChoices(true));
  new MutationObserver(() => fillChoices()).observe(lamp, {childList: true});
  fillChoices();
})();
