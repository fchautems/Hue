"""Hue Web: interface locale, automatismes et diagnostics. Ne modifie pas hue.py."""
from __future__ import annotations

import argparse
import copy
import ipaddress
from datetime import datetime
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import urllib3

import hue_update_api
from hue_v03_runtime import HueEventStream, reconnect_transition_ms
from hue_core import DEFAULT_POINTS, brightness_at, public_sim, simulated_minutes, validate_points, wall_clock_minutes

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / ".hue_config.json"
CONFIG_EXAMPLE = ROOT / "hue_config.example.json"
SETTINGS_PATH = ROOT / "hue_settings.json"
LOG_DIR = ROOT / "logs"
POLL_INTERVAL_SECONDS = 1.0
COMMAND_COOLDOWN_SECONDS = 1.25
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("hue_web")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    log_file = RotatingFileHandler(LOG_DIR / "hue.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    log_file.setFormatter(fmt)
    logger.addHandler(log_file)
    log_console = logging.StreamHandler()
    log_console.setFormatter(fmt)
    logger.addHandler(log_console)

app = FastAPI(title="Hue Lab", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


class HueError(Exception):
    pass


class HueClient:
    def __init__(self, ip, key):
        if not ip or not key:
            raise HueError("Configuration Hue invalide (ip/key).")
        self.ip = ip
        self.session = requests.Session()
        self.session.headers.update({"hue-application-key": key})
        self.session.verify = False  # HTTPS local Hue: certificat non validé dans ce prototype.

    def resource(self, resource, method="GET", payload=None):
        try:
            response = self.session.request(
                method,
                f"https://{self.ip}/clip/v2/resource/{resource}",
                json=payload,
                timeout=4,
            )
        except requests.RequestException as e:
            raise HueError(f"Pont {self.ip}: {type(e).__name__}: {e}") from e

        try:
            data = response.json()
        except ValueError as e:
            try:
                response.raise_for_status()
            except requests.RequestException as http_error:
                raise HueError(
                    f"Pont {self.ip}: erreur HTTP {response.status_code} sans détail exploitable."
                ) from http_error
            raise HueError("Le pont Hue a renvoyé une réponse JSON invalide.") from e

        if isinstance(data, dict) and data.get("errors"):
            descriptions = []
            for error in data["errors"]:
                if isinstance(error, dict):
                    description = error.get("description")
                    if isinstance(description, str) and description:
                        descriptions.append(description)
            detail = "; ".join(descriptions) or "requête refusée sans détail"
            raise HueError(f"API Hue (HTTP {response.status_code}) : {detail}")
        try:
            response.raise_for_status()
        except requests.RequestException as e:
            raise HueError(f"Pont {self.ip}: erreur HTTP {response.status_code}.") from e
        if not isinstance(data, dict):
            raise HueError("Le pont Hue a renvoyé une réponse inattendue.")
        return data.get("data", [])


class HueServer:
    def __init__(self, client=None, settings_path=SETTINGS_PATH, logger_=logger, start_worker=False):
        self.lock = threading.RLock()
        self.client = client
        self.settings_path = Path(settings_path)
        self.log = logger_
        self.settings = {"auto": False, "mode": "manuel", "profiles": {}}
        if self.settings_path.exists():
            try:
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.settings["profiles"] = {k: validate_points(v) for k, v in loaded.get("profiles", {}).items()}
                    self.settings["mode"] = loaded.get("mode") if loaded.get("mode") in ("manuel", "reel") else "manuel"
                    self.settings["auto"] = self.settings["mode"] == "reel"
                    # Sécurité: démarrage toujours en mode manuel; activation explicite dans l'UI.
            except (OSError, ValueError, TypeError) as e:
                self.log.warning("Paramètres non chargés : %s", e)
        self.sim = {"enabled": False, "running": False, "apply": False,
                    "seconds_per_day": 120, "minute": 8 * 60, "started_at": time.monotonic()}
        self.lights = []
        self.devices = []
        self.connectivity = []
        self.bridge = []
        self.last_error = None
        self.last_poll = None
        self.previous_online = {}
        self.previous_on = {}
        self.reconnect_pending = set()
        self.last_sent = {}  # id -> {at, target}
        self.last_user_action = {}  # pour le diagnostic, pas pour masquer la détection physique
        self.power_tests = {}  # mesures relatives aux observations Zigbee
        self._stop = threading.Event()
        self._worker = None
        self._error_last_logged = 0
        self._event_wakeup = threading.Event()
        self._automation_lock = threading.Lock()
        self._events = HueEventStream(lambda: self.client, self._event_wakeup.set, self._stop, self.log)
        self.reconnect_at = {}
        self.reconnect_latency = {}
        if start_worker:
            self.start_worker()

    def start_worker(self):
        if self._worker is None:
            self._worker = threading.Thread(target=self._loop, name="HueMonitoring", daemon=True)
            self._worker.start()
            self._events.start()
            self.log.info("Surveillance démarrée (sondage de secours toutes les %.1f s).", POLL_INTERVAL_SECONDS)

    def stop(self):
        self._stop.set()
        self._event_wakeup.set()
        self._events.interrupt()
        if self._worker:
            self._worker.join(timeout=5)
        if self._events.thread:
            self._events.thread.join(timeout=3)

    def save(self):
        # Sauvegarde atomique. Les secrets de l'API Hue ne sont jamais enregistrés ici.
        payload = {"profiles": self.settings["profiles"], "mode": self.settings["mode"] if self.settings["mode"] in ("manuel", "reel") else "manuel"}
        tmp = self.settings_path.with_name(self.settings_path.name + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.settings_path)

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.poll()
                self.automate()
            except Exception:
                self.log.exception("Erreur inattendue dans la surveillance")
            # Les événements SSE réveillent ce worker plus tôt ; polling rapide mais borné en secours.
            self._event_wakeup.wait(POLL_INTERVAL_SECONDS)
            self._event_wakeup.clear()

    def attach_client(self, client):
        """Change de pont sans réutiliser les anciennes ampoules ou automatismes."""
        with self.lock:
            self.client = client
            self.lights = []
            self.devices = []
            self.connectivity = []
            self.last_poll = None
            self.last_error = None
            self.previous_online.clear()
            self.previous_on.clear()
            self.reconnect_pending.clear()
            self.last_sent.clear()
            self.power_tests.clear()
            self.settings["auto"] = False
            self.settings["mode"] = "manuel"
            self.sim["enabled"] = False
            self.sim["running"] = False
            self.sim["apply"] = False
            self.reconnect_at.clear()
            self.reconnect_latency.clear()
            self.save()
            self._events.interrupt()
            self._event_wakeup.set()

    def poll(self):
        with self.lock:
            client = self.client
        if not client:
            with self.lock:
                self.last_error = "Pont non associé. Ouvre l'onglet Connexion pour le configurer."
            return
        try:
            lights = client.resource("light")
            devices = client.resource("device")
            connectivity = client.resource("zigbee_connectivity")
            with self.lock:
                if self.client is not client:
                    return  # Ancienne réponse réseau après changement de pont.
                current_online = {}
                status_by_device = {c.get("owner", {}).get("rid"): c.get("status") for c in connectivity}
                for l in lights:
                    uid = l["id"]
                    status = status_by_device.get(l.get("owner", {}).get("rid"))
                    online = status == "connected" if status is not None else None
                    current_online[uid] = online
                    old_online = self.previous_online.get(uid)
                    # Une transition offline->online est une observation réseau, pas une preuve de coupure physique.
                    trial = self.power_tests.get(uid)
                    if old_online is False and online is True:
                        self.reconnect_pending.add(uid)
                        self.reconnect_at[uid] = time.monotonic()
                        self.log.info("RECONNEXION | %s | connexion Zigbee restaurée", l.get("metadata", {}).get("name", uid))
                        if trial and trial.get("offline_at") is not None and trial["status"] == "hors ligne observé":
                            trial["observed_offline_seconds"] = round(time.monotonic() - trial["offline_at"], 2)
                            trial["status"] = "reconnecté"
                            trial["reconnected_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                            self.log.info("TEST SECTEUR | %s | retour Zigbee observé après %.2fs d'état hors-ligne observé (sondage %.1fs)",
                                          l.get("metadata", {}).get("name", uid), trial["observed_offline_seconds"],
                                          POLL_INTERVAL_SECONDS)
                    elif old_online is True and online is False:
                        self.log.warning("DÉCONNEXION | %s | connexion Zigbee perdue", l.get("metadata", {}).get("name", uid))
                        if trial and trial["status"] == "armé":
                            trial["offline_at"] = time.monotonic()
                            trial["status"] = "hors ligne observé"
                            self.log.info("TEST SECTEUR | %s | perte Zigbee observée", l.get("metadata", {}).get("name", uid))
                    if uid not in self.settings["profiles"]:
                        self.settings["profiles"][uid] = copy.deepcopy(DEFAULT_POINTS)
                    is_on = l.get("on", {}).get("on")
                    old_on = self.previous_on.get(uid)
                    if old_on is False and is_on is True:
                        self.log.info("ÉTAT | %s | ON observé", l.get("metadata", {}).get("name", uid))
                    elif old_on is True and is_on is False:
                        self.log.info("ÉTAT | %s | OFF observé", l.get("metadata", {}).get("name", uid))
                    self.previous_on[uid] = is_on
                self.previous_online.update(current_online)
                self.lights = lights
                self.devices = devices
                self.connectivity = connectivity
                self.last_poll = datetime.now().astimezone().isoformat(timespec="seconds")
                self.last_error = None
        except HueError as e:
            with self.lock:
                if self.client is not client:
                    return
                self.last_error = str(e)
            if time.monotonic() - self._error_last_logged > 30:
                self._error_last_logged = time.monotonic()
                self.log.warning("Lecture Hue impossible : %s", e)

    def simulated_time(self):
        with self.lock:
            if self.sim["enabled"]:
                return simulated_minutes(self.sim)
            return wall_clock_minutes()

    def _mode(self):
        with self.lock:
            return self.settings["mode"]

    def set_mode(self, mode):
        if mode not in ("manuel", "reel", "accelere"):
            raise ValueError("Mode inconnu : manuel, reel ou accelere.")
        with self.lock:
            previous = self.settings["mode"]
            if mode == previous:
                return {"mode": mode}
            self.settings["mode"] = mode
            self.settings["auto"] = mode == "reel"
            if mode == "accelere":
                self.sim["minute"] = wall_clock_minutes()
            self.sim["enabled"] = mode == "accelere"
            self.sim["apply"] = mode == "accelere"
            self.sim["running"] = mode == "accelere"
            self.sim["started_at"] = time.monotonic()
            self.last_sent.clear()
            self.save()
        self.log.info("MODE | %s -> %s", previous, mode)
        self._event_wakeup.set()
        return {"mode": mode}

    def automate(self):
        if not self.client or self.last_error:
            return
        if not self._automation_lock.acquire(blocking=False):
            return
        try:
            self._automate_locked()
        finally:
            self._automation_lock.release()

    def _automate_locked(self):
        with self.lock:
            mode = self._mode()
            if mode == "manuel":
                return
            minute = simulated_minutes(self.sim) if mode == "accelere" else wall_clock_minutes()
            lights = copy.deepcopy(self.lights)
            profiles = copy.deepcopy(self.settings["profiles"])
            status = {c.get("owner", {}).get("rid"): c.get("status") for c in self.connectivity}
            pending = set(self.reconnect_pending)
        for light in lights:
            uid = light["id"]
            if "dimming" not in light:
                continue
            if not light.get("on", {}).get("on", False):
                continue  # Ne jamais allumer automatiquement une ampoule éteinte via l'API.
            state = status.get(light.get("owner", {}).get("rid"))
            if state is not None and state != "connected":
                continue
            target = brightness_at(profiles.get(uid, DEFAULT_POINTS), minute)
            current = light.get("dimming", {}).get("brightness")
            last = self.last_sent.get(uid, {})
            now = time.monotonic()
            reconnect = uid in pending
            observed_drift = (
                not reconnect
                and bool(last)
                and abs(target - last["target"]) < 1.0
                and isinstance(current, (float, int))
                and abs(target - current) >= 1.0
            )
            urgent_correction = reconnect or observed_drift
            # Les lectures Hue peuvent être légèrement en retard: ne pas renvoyer en boucle une même cible.
            if last and now - last["at"] < COMMAND_COOLDOWN_SECONDS:
                continue
            if not urgent_correction and last and abs(target - last["target"]) < 1.0 and now - last["at"] < 60:
                continue
            if not urgent_correction and isinstance(current, (float, int)) and abs(target - current) < 1.0:
                continue
            payload = {"dimming": {"brightness": max(1, min(100, target))}}
            if "dynamics" in light:
                payload["dynamics"] = {"duration": reconnect_transition_ms(current, target) if urgent_correction else (1800 if mode == "accelere" else 3000)}
            try:
                self.client.resource(f"light/{uid}", "PUT", payload)
                with self.lock:
                    self.last_sent[uid] = {"at": now, "target": target}
                    self.reconnect_pending.discard(uid)
                    if reconnect:
                        elapsed = round((time.monotonic() - self.reconnect_at.get(uid, now)) * 1000)
                        self.reconnect_latency[uid] = elapsed
                        self.log.info("CORRECTION RECONNEXION | %s | délai API observé %d ms | transition demandée %d ms", uid, elapsed, payload.get("dynamics", {}).get("duration", 0))
                self.log.info("AUTO | %s | cible %.1f%% | mode=%s | durée=%dms%s",
                              light.get("metadata", {}).get("name", uid), target, mode,
                              payload.get("dynamics", {}).get("duration", 0),
                              " | correction reconnexion" if reconnect else (" | correction écart observé" if observed_drift else ""))
            except HueError as e:
                self.log.error("AUTO refusé | %s | %s", uid, e)

    def get_lights(self):
        with self.lock:
            m = self.simulated_time()
            connections = {c.get("owner", {}).get("rid"): c.get("status") for c in self.connectivity}
            devices = {d.get("id"): d for d in self.devices}
            result = []
            for l in self.lights:
                owner = l.get("owner", {}).get("rid")
                dev = devices.get(owner, {})
                points = self.settings["profiles"].get(l["id"], DEFAULT_POINTS)
                result.append({
                    "id": l["id"],
                    "name": l.get("metadata", {}).get("name", "Ampoule"),
                    "on": l.get("on", {}).get("on"),
                    "brightness": l.get("dimming", {}).get("brightness"),
                    "target": brightness_at(points, m),
                    "status": connections.get(owner, "inconnu"),
                    "model": dev.get("product_data", {}).get("model_id", "inconnu"),
                    "manufacturer": dev.get("product_data", {}).get("manufacturer_name", "inconnu"),
                    "capabilities": {
                        "on": "on" in l,
                        "dimming": "dimming" in l,
                        "dynamics": "dynamics" in l,
                        "powerup": "powerup" in l,
                        "color_temperature": "color_temperature" in l,
                        "color": "color" in l,
                    },
                    "powerup": l.get("powerup"),
                })
            return result

    def state(self):
        with self.lock:
            return {
                "bridge_ip": self.client.ip if self.client else None,
                "needs_setup": self.client is None or "unauthorized" in (self.last_error or "").lower(),
                "connected": self.client is not None and self.last_poll is not None and self.last_error is None,
                "error": self.last_error,
                "last_poll": self.last_poll,
                "auto": self.settings["auto"],
                "simulation": public_sim(self.sim),
                "mode": self._mode(),
                "minute": round(self.simulated_time(), 3),
                "lights": self.get_lights(),
            }

    def profile(self, uid):
        with self.lock:
            self.require_light(uid)
            return copy.deepcopy(self.settings["profiles"].get(uid, DEFAULT_POINTS))

    def require_light(self, uid):
        light = next((l for l in self.lights if l.get("id") == uid), None)
        if not light:
            raise ValueError("Ampoule inconnue. Actualise le pont.")
        return light

    def set_profile(self, uid, points):
        cleaned = validate_points(points)
        with self.lock:
            self.require_light(uid)
            self.settings["profiles"][uid] = cleaned
            self.save()
        self.log.info("PROFIL | %s | %d points sauvegardés", uid, len(cleaned))
        return cleaned

    def set_sim(self, data):
        allowed = {"running", "seconds_per_day", "minute"}
        if not isinstance(data, dict) or set(data) - allowed:
            raise ValueError("Paramètres de simulation invalides.")
        with self.lock:
            if self.settings["mode"] != "accelere":
                raise ValueError("Activer le mode accéléré avant de régler l'horloge virtuelle.")
            # Réinitialise l'origine temporelle pour garantir une vitesse continue.
            now_min = simulated_minutes(self.sim)
            if "seconds_per_day" in data and data["seconds_per_day"] not in (30, 60, 120, 300, 600):
                raise ValueError("Choisir 30, 60, 120, 300 ou 600 secondes par jour.")
            if "minute" in data:
                v = data["minute"]
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v < 1440:
                    raise ValueError("Minute de simulation invalide.")
                now_min = float(v)
            for key in ("running",):
                if key in data and not isinstance(data[key], bool):
                    raise ValueError(f"{key} doit être un booléen.")
            self.sim.update(data)
            self.sim["minute"] = now_min
            self.sim["started_at"] = time.monotonic()
            result = public_sim(self.sim)
        self.log.info("SIMULATION | %s", json.dumps(result, ensure_ascii=False))
        return result

    def switch(self, uid, on, brightness=None):
        if not self.client:
            raise HueError("Pont non configuré")
        with self.lock:
            light = self.require_light(uid)
            supports_dimming = "dimming" in light
            name = light.get("metadata", {}).get("name", uid)
            target = self.get_lights()
            target = next(x["target"] for x in target if x["id"] == uid)
        payload = {"on": {"on": on}}
        if on and supports_dimming:
            payload["dimming"] = {"brightness": float(brightness if brightness is not None else target)}
        self.client.resource(f"light/{uid}", "PUT", payload)
        with self.lock:
            self.last_user_action[uid] = time.monotonic()
            self.last_sent.pop(uid, None)
        self.log.info("MANUEL | %s | %s", name, payload)

    def set_brightness(self, uid, brightness):
        if isinstance(brightness, bool) or not isinstance(brightness, (float, int)) or not 1 <= brightness <= 100:
            raise ValueError("La luminosité doit être entre 1 et 100 %.")
        with self.lock:
            light = self.require_light(uid)
            if "dimming" not in light:
                raise ValueError("Cette ampoule ne propose pas le réglage de luminosité.")
        payload = {"dimming": {"brightness": float(brightness)}}
        if "dynamics" in light:
            payload["dynamics"] = {"duration": 400}
        self.client.resource(f"light/{uid}", "PUT", payload)
        self.log.info("MANUEL | %s | luminosité %.1f%%", uid, brightness)

    def set_powerup(self, uid, preset, brightness=None):
        with self.lock:
            light = self.require_light(uid)
            if "powerup" not in light:
                raise ValueError("Le pont ne signale pas la capacité powerup pour cette ampoule.")
        if preset not in ("last_on_state", "safety", "powerfail", "custom"):
            raise ValueError("Preset powerup inconnu")
        powerup = {"preset": preset}
        if preset == "custom":
            if isinstance(brightness, bool) or not isinstance(brightness, (float, int)) or not 1 <= brightness <= 100:
                raise ValueError("Luminosité custom: 1 à 100 %.")
            powerup.update({
                "on": {"mode": "on", "on": {"on": True}},
                "dimming": {
                    "mode": "dimming",
                    "dimming": {"brightness": float(brightness)},
                },
            })
        self.client.resource(f"light/{uid}", "PUT", {"powerup": powerup})
        self.log.warning("POWERUP MODIFIÉ | %s | %s", uid, json.dumps(powerup))
        # Le pont accepte l'écriture avant que le firmware de l'ampoule ait fini
        # de la mémoriser. Pendant ce bref délai, la relecture renvoie configured=false.
        current = {}
        matched = False
        for attempt in range(6):
            self.poll()
            with self.lock:
                current = copy.deepcopy(self.require_light(uid).get("powerup", {}))
            actual_dimming = current.get("dimming", {}).get("dimming", {}).get("brightness")
            matched = current.get("preset") == preset and current.get("configured") is not False
            if preset == "custom":
                matched = matched and isinstance(actual_dimming, (int, float)) and abs(actual_dimming - brightness) < 0.6
            if matched:
                break
            if attempt < 5:
                time.sleep(0.4)
        result = {"requested": powerup, "readback": current, "verified_readback": bool(matched)}
        if not matched:
            self.log.warning("POWERUP NON CONFIRMÉ | %s | lecture %s", uid, json.dumps(current))
        else:
            self.log.info("POWERUP CONFIRMÉ PAR LECTURE | %s | %s (test secteur à faire)", uid, preset)
        return result

    def arm_power_test(self, uid):
        with self.lock:
            light = self.require_light(uid)
            name = light.get("metadata", {}).get("name", uid)
            self.power_tests[uid] = {
                "status": "armé",
                "armed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "offline_at": None,
                "observed_offline_seconds": None,
            }
        self.log.info("TEST SECTEUR ARMÉ | %s | couper puis remettre le courant avec l'interrupteur mural", name)
        return {"status": "armé", "light": name}

    def diagnostics(self):
        with self.lock:
            return {
                "generated": datetime.now().astimezone().isoformat(),
                "bridge_ip": self.client.ip if self.client else None,
                "last_poll": self.last_poll,
                "last_error": self.last_error,
                "lights": self.get_lights(),
                "devices": copy.deepcopy(self.devices),
                "zigbee_connectivity": copy.deepcopy(self.connectivity),
                "power_tests": copy.deepcopy(self.power_tests),
                "reconnect_latency_ms": copy.deepcopy(self.reconnect_latency),
                "event_stream": {"status": self._events.status, "last_event_epoch": self._events.last_event},
                "notes": [
                    "Clé d'accès Hue volontairement absente de ce rapport.",
                    "L'état Zigbee fourni par le pont n'est pas une mesure électrique de la coupure de courant.",
                    "Le comportement powerup dépend du modèle et de son firmware.",
                    "Les temps de réveil et les changements lumineux réels doivent être mesurés sur site.",
                ],
            }


def local_bridge_ip(value):
    """N'accepte que les IPv4 privées du LAN (pas de nom DNS ni URL)."""
    try:
        ip = ipaddress.IPv4Address(str(value).strip())
    except ipaddress.AddressValueError as e:
        raise ValueError("Adresse IPv4 du pont invalide.") from e
    networks = (ipaddress.IPv4Network("10.0.0.0/8"),
                ipaddress.IPv4Network("172.16.0.0/12"),
                ipaddress.IPv4Network("192.168.0.0/16"))
    if not any(ip in n for n in networks):
        raise ValueError("Le pont doit avoir une adresse IPv4 privée du réseau local.")
    return str(ip)


class HueOnboarding:
    """Découverte, appairage et stockage local sans étape en ligne de commande."""
    def __init__(self, config_path=CONFIG_PATH, example_path=CONFIG_EXAMPLE, session=None):
        self.path = Path(config_path)
        self.example = Path(example_path)
        self.session = session or requests.Session()
        self.lock = threading.Lock()

    def ensure_config(self):
        if self.path.exists():
            return
        # Un modèle sans clé est publié sur GitHub ; la clé réelle n'y figure jamais.
        template = {"ip": "", "key": ""}
        if self.example.is_file():
            try:
                candidate = json.loads(self.example.read_text(encoding="utf-8"))
                if isinstance(candidate, dict):
                    template["ip"] = str(candidate.get("ip") or "")
            except (OSError, ValueError) as e:
                logger.warning("Modèle de configuration illisible : %s", e)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.path.open("x", encoding="utf-8") as stream:
                json.dump(template, stream, indent=2)
                stream.write("\n")
        except FileExistsError:
            pass

    def public_status(self):
        try:
            cfg = json.loads(self.path.read_text(encoding="utf-8"))
            ip = cfg.get("ip") or ""
            try:
                ip = local_bridge_ip(ip)
            except ValueError:
                ip = ""
            return {"ip": ip, "paired": bool(cfg.get("key")), "config_exists": True}
        except (OSError, ValueError, AttributeError):
            return {"ip": "", "paired": False, "config_exists": self.path.exists()}

    def discover(self):
        try:
            response = self.session.get("https://discovery.meethue.com/", timeout=6)
            response.raise_for_status()
            result = response.json()
        except (requests.RequestException, ValueError) as e:
            raise HueError("Découverte Hue indisponible. Saisis l'adresse IP du pont, par exemple 10.0.0.2.") from e
        if not isinstance(result, list):
            raise HueError("Réponse de découverte Hue invalide. Saisis l'IP manuellement.")
        found = []
        for bridge in result:
            if not isinstance(bridge, dict):
                continue
            try:
                ip = local_bridge_ip(bridge.get("internalipaddress", ""))
            except ValueError:
                continue
            if ip not in found:
                found.append(ip)
        return found

    def pair_once(self, ip):
        ip = local_bridge_ip(ip)
        try:
            response = self.session.post(
                f"https://{ip}/api", json={"devicetype": "hue_lab#pc"},
                verify=False, timeout=3,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as e:
            raise HueError(f"Pont {ip} inaccessible. Vérifie l'adresse IP et le réseau.") from e
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise HueError("Réponse d'association inattendue du pont Hue.")
        item = payload[0]
        if "error" in item:
            err = item["error"]
            if isinstance(err, dict) and err.get("type") == 101:
                return {"paired": False, "waiting_for_button": True, "ip": ip}
            # Ne jamais afficher la réponse brute avec d'éventuelles informations privées.
            raise HueError(f"Association refusée par le pont (code {err.get('type', 'inconnu') if isinstance(err, dict) else 'inconnu'}).")
        key = item.get("success", {}).get("username") if isinstance(item.get("success"), dict) else None
        if not isinstance(key, str) or not key.strip():
            raise HueError("Le pont n'a pas fourni de clé d'application valide.")
        # Tester effectivement la clé avant d'écrire la configuration définitive.
        client = HueClient(ip, key)
        client.resource("light")
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            tmp.write_text(json.dumps({"ip": ip, "key": key}, indent=2) + "\n", encoding="utf-8")
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
            tmp.replace(self.path)
            controller.attach_client(client)
        controller.poll()
        logger.info("Pont Hue associé et configuration créée automatiquement | %s", ip)
        return {"paired": True, "waiting_for_button": False, "ip": ip, "lights": len(controller.get_lights())}


def load_client():
    try:
        setup.ensure_config()
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if not isinstance(cfg, dict) or not cfg.get("ip") or not cfg.get("key"):
            return None
        return HueClient(local_bridge_ip(cfg["ip"]), cfg["key"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        logger.warning("Configuration locale non exploitable (association via l'interface) : %s", type(e).__name__)
        return None


setup = HueOnboarding()


controller = HueServer(client=load_client(), start_worker=False)


def ok(data=None):
    return {"ok": True, "data": data}


@app.exception_handler(ValueError)
async def invalid(_request: Request, e: ValueError):
    return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.exception_handler(HueError)
async def unavailable(_request: Request, e: HueError):
    return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/state")
def state():
    return controller.state()


@app.get("/api/setup/status")
def setup_status():
    return ok(setup.public_status())


@app.get("/api/setup/discover")
def setup_discover():
    return ok({"bridges": setup.discover()})


@app.post("/api/setup/pair")
def setup_pair(data: dict = Body(...)):
    return ok(setup.pair_once(data.get("ip", "")))


@app.post("/api/auto")
def auto(data: dict = Body(...)):
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled doit être true ou false.")
    return ok(controller.set_mode("reel" if enabled else "manuel"))


@app.post("/api/mode")
def update_mode(data: dict = Body(...)):
    return ok(controller.set_mode(data.get("mode")))


@app.post("/api/simulation")
def simulation(data: dict = Body(...)):
    return ok(controller.set_sim(data))


@app.get("/api/profile/{uid}")
def profile(uid: str):
    return ok(controller.profile(uid))


@app.put("/api/profile/{uid}")
def set_profile(uid: str, data: dict = Body(...)):
    return ok(controller.set_profile(uid, data.get("points")))


@app.post("/api/light/{uid}/switch")
def switch(uid: str, data: dict = Body(...)):
    if not isinstance(data.get("on"), bool):
        raise ValueError("on doit être un booléen.")
    controller.switch(uid, data["on"])
    return ok()


@app.post("/api/light/{uid}/brightness")
def set_brightness(uid: str, data: dict = Body(...)):
    controller.set_brightness(uid, data.get("brightness"))
    return ok()


@app.post("/api/light/{uid}/powerup")
def set_powerup(uid: str, data: dict = Body(...)):
    return ok(controller.set_powerup(uid, data.get("preset"), data.get("brightness")))


@app.post("/api/power-test/{uid}/arm")
def power_test_arm(uid: str):
    return ok(controller.arm_power_test(uid))


@app.get("/api/diagnostics")
def diagnostics():
    return controller.diagnostics()


@app.get("/api/logs")
def logs():
    path = LOG_DIR / "hue.log"
    if not path.exists():
        return ok([])
    return ok(path.read_text(encoding="utf-8", errors="replace").splitlines()[-150:])


@app.get("/api/update/status")
def update_status():
    return ok(hue_update_api.status())


@app.post("/api/update/{action}")
def update_action(action: str, request: Request, data: dict = Body(...)):
    if action not in ("check", "apply"):
        raise ValueError("Action de mise à jour inconnue.")
    if not hue_update_api.authorized_browser_request(request):
        return JSONResponse({"ok": False, "error": "Mise à jour autorisée uniquement depuis l'interface locale Hue Lab."}, status_code=403)
    try:
        hue_update_api.trigger(action)
    except RuntimeError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=409)
    return ok({"queued": True, "action": action})


if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser(description="Hue Web – contrôle local")
    parser.add_argument("--host", default="127.0.0.1", help="127.0.0.1 (local) par défaut")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    controller.start_worker()
    logger.info("Serveur Hue Web sur http://%s:%s", args.host, args.port)
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        controller.stop()
