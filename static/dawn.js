"use strict";
(() => {
  const form = $("#dawn-form");
  const enabled = $("#dawn-enabled");
  const light = $("#dawn-light");
  const fields = $("#dawn-fields");
  const save = $("#dawn-save");
  const sync = $("#dawn-sync");
  const status = $("#dawn-status");
  const native = navigator.userAgent.includes("HueLabAndroid/");
  const date = new Intl.DateTimeFormat("fr-CH", {weekday:"short", day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"});
  let config, lights = [], dirty = false, busy = false, lastRead = 0, generation = 0;

  function showOptions() {
    const value = dirty ? light.value : config?.light_id;
    const options = lights.filter(item => item.capabilities?.color && item.capabilities?.dimming);
    if (value && !options.some(item => item.id === value)) {
      options.push({id:value, name:"Lampe enregistrée · indisponible"});
    }
    const choices = [{id:"", name:"Choisir une lampe"}, ...options];
    if (choices.length !== light.options.length || choices.some((item, index) =>
      item.id !== light.options[index].value || item.name !== light.options[index].text)) {
      light.replaceChildren(...choices.map(item => new Option(item.name, item.id)));
    }
    light.value = value || "";
  }

  function paint(data) {
    config = data;
    if (!dirty) {
      enabled.checked = data.enabled;
      $("#dawn-color").value = data.color;
      $("#dawn-minutes").value = data.minutes;
      $("#dawn-brightness").value = data.brightness;
      showOptions();
    }
    fields.hidden = !enabled.checked;
    light.required = enabled.checked;
    sync.hidden = !native || !data.enabled;
    const message = !data.enabled ? "Désactivé." :
      data.alarm_at > Date.now() ? "Réveil reçu · " + date.format(data.alarm_at) +
        " · synchronisé " + date.format(data.observed_at) :
      data.observed_at ? "Aucun prochain réveil reçu." : "En attente de la première synchronisation Android.";
    if (status.textContent !== message) status.textContent = message;
    save.disabled = false;
  }

  async function read() {
    if (busy || Date.now() - lastRead < 4000) return;
    lastRead = Date.now();
    const request = generation;
    try {
      const data = await api("/api/dawn");
      if (request === generation) paint(data);
    } catch (error) {
      if (request === generation) status.textContent = error.message;
    }
  }

  function askAndroid() {
    if (native) window.location.href = "huelab://sync-alarm";
  }

  form.addEventListener("input", () => {
    dirty = true;
    fields.hidden = !enabled.checked;
    light.required = enabled.checked;
  });
  sync.addEventListener("click", askAndroid);
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy) return;
    busy = true;
    generation++;
    save.disabled = true;
    try {
      const data = await api("/api/dawn", "PUT", {
        enabled: enabled.checked, light_id: light.value, color: $("#dawn-color").value,
        minutes: Number($("#dawn-minutes").value), brightness: Number($("#dawn-brightness").value)
      });
      dirty = false;
      paint(data);
      askAndroid();
      showToast("Réveil lumineux enregistré.");
    } catch (error) {
      status.textContent = error.message;
    } finally {
      busy = false;
      save.disabled = false;
    }
  });
  window.HueDawn = {checkSync(succeeded) {
    if (!succeeded) showToast("Le Raspberry n’a pas confirmé la synchronisation du réveil.", true);
    lastRead = 0;
    read();
  }, refresh(nextLights) {
    const changed = nextLights.length !== lights.length || nextLights.some((item, index) =>
      item.id !== lights[index]?.id || item.name !== lights[index]?.name ||
      item.capabilities?.color !== lights[index]?.capabilities?.color ||
      item.capabilities?.dimming !== lights[index]?.capabilities?.dimming);
    lights = nextLights;
    if (changed) showOptions();
    if (activeTab === "dashboard") read();
  }};
})();
