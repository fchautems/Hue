/* Hue Lab v0.6.1 — navigation fusionnée, sans changement de logique Hue. */
"use strict";
(() => {
  const profiles = document.querySelector('#tab-profiles');
  const lamp = document.querySelector('#profile-light');
  const toggle = document.querySelector('#v051-simulation-toggle');
  const rgbSection = document.querySelector('#tab-colors');
  if (!profiles || !lamp || !toggle || !rgbSection) return;

  // La v0.5.1 cachait tout le simulateur sur mobile.
  // Désormais, seule sa carte de commandes est repliable ; l'horloge reste visible.
  toggle.onclick = () => {
    const expanded = document.body.classList.toggle('v051-show-simulator');
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.textContent = expanded
      ? 'Masquer les commandes de simulation'
      : 'Afficher les commandes de simulation';
  };

  // Le sélecteur commun change simultanément la lampe de l'éditeur de
  // luminosité et celle de la roue RGB, sans supprimer les garde-fous v0.5.x.
  lamp.addEventListener('change', event => {
    if (lamp.value === selectedId) return;
    if (window.HueRGB?.hasChanges() && !window.HueRGB.discardPrompt()) {
      lamp.value = selectedId || '';
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  lamp.addEventListener('change', () => {
    // L'éditeur des courbes peut refuser un changement si un brouillon existe.
    if (lamp.value && lamp.value === selectedId) {
      window.HueRGB?.open(selectedId, true);
    }
  });

  window.HueMerged = {
    afterRgbSave(id) {
      // Le mode Auto RGB peut activer la courbe Simple ; mettre à jour
      // l'ancien éditeur uniquement en l'absence d'un brouillon non sauvé.
      if (id === selectedId && !window.HueProfiles?.hasUnsaved()) {
        window.HueProfiles?.reload();
      }
    },
  };
})();
