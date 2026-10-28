"""Hue Web: interface locale, automatismes et diagnostics. Ne modifie pas hue.py."""
from __future__ import annotations

import argparse
import copy
import ipaddress
from datetime import datetime, timedelta
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import urllib3

import hue_update_api
from hue_presence_log import PresenceLog
from hue_vacation import build_schedule, desired_states, validate_selection, GRACE_SECONDS, LOCAL_TZ
from hue_v03_runtime import HueEventStream, reconnect_transition_ms
from hue_core import DEFAULT_POINTS, brightness_at, public_sim, simulated_minutes, validate_points, wall_clock_minutes
from hue_simple_profile import DEFAULT_SIMPLE_PROFILE, simple_brightness_at, validate_simple_profile
from hue_rgb import DEFAULT_RGB_PHASES, DEFAULT_MANUAL_COLOR, rgb_at, hsv_to_xy, xy_distance, validate_hs, validate_rgb_phases

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
        self.presence_log = PresenceLog(self.settings_path.parent / "logs" / "presence_events.csv", self.log)
        # Migration v0.4 -> v0.5 : le mode global historique reste lisible,
        # mais chaque ampoule dispose désormais de son propre contrôle.
        self.settings = {"auto": False, "mode": "manuel", "profiles": {},
                         "light_modes": {}, "manual_states": {},
                         "simple_profiles": {}, "profile_types": {},
                         "rgb_profiles": {}, "rgb_manual": {}, "rgb_auto_enabled": {}}
        self._legacy_default_auto = False
        self.vacation = {"enabled": False, "light_ids": [], "seed": "",
                         "plan_date": "", "schedule": [], "overrides": {}}
        if self.settings_path.exists():
            try:
                loaded = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    saved_vacation = loaded.get("vacation")
                    if isinstance(saved_vacation, dict):
                        ids = saved_vacation.get("light_ids")
                        if isinstance(ids, list) and all(isinstance(uid, str) for uid in ids):
                            self.vacation["light_ids"] = ids[:30]
                            self.vacation["enabled"] = saved_vacation.get("enabled") is True and bool(ids)
                        if isinstance(saved_vacation.get("seed"), str):
                            self.vacation["seed"] = saved_vacation["seed"][:100]
                        if isinstance(saved_vacation.get("plan_date"), str):
                            self.vacation["plan_date"] = saved_vacation["plan_date"]
                        if isinstance(saved_vacation.get("schedule"), list):
                            self.vacation["schedule"] = saved_vacation["schedule"][:3000]
                        if isinstance(saved_vacation.get("overrides"), dict):
                            self.vacation["overrides"] = {
                                k: v for k, v in saved_vacation["overrides"].items()
                                if isinstance(k, str) and isinstance(v, dict)
                                and type(v.get("on")) is bool and isinstance(v.get("until"), (int, float))
                            }
                    self.settings["profiles"] = {k: validate_points(v) for k, v in loaded.get("profiles", {}).items()}
                    simple = loaded.get("simple_profiles", {})
                    if isinstance(simple, dict):
                        for uid, raw in simple.items():
                            if not isinstance(uid, str):
                                continue
                            try:
                                self.settings["simple_profiles"][uid] = validate_simple_profile(raw)
                            except (ValueError, TypeError):
                                self.log.warning("Profil simple invalide ignoré pour une lampe.")
                    profile_types = loaded.get("profile_types", {})
                    if isinstance(profile_types, dict):
                        self.settings["profile_types"] = {
                            uid: kind for uid, kind in profile_types.items()
                            if isinstance(uid, str) and kind in ("simple", "custom")
                        }
                    rgb_profiles = loaded.get("rgb_profiles", {})
                    if isinstance(rgb_profiles, dict):
                        for uid, raw in rgb_profiles.items():
                            if not isinstance(uid, str):
                                continue
                            try:
                                self.settings["rgb_profiles"][uid] = validate_rgb_phases(raw)
                            except (ValueError, TypeError):
                                self.log.warning("Couleurs automatiques invalides ignorées pour une lampe.")
                    rgb_manual = loaded.get("rgb_manual", {})
                    if isinstance(rgb_manual, dict):
                        for uid, raw in rgb_manual.items():
                            if not isinstance(uid, str):
                                continue
                            try:
                                self.settings["rgb_manual"][uid] = validate_hs(raw)
                            except (ValueError, TypeError):
                                self.log.warning("Couleur manuelle invalide ignorée pour une lampe.")
                    enabled_colors = loaded.get("rgb_auto_enabled", {})
                    if isinstance(enabled_colors, dict):
                        self.settings["rgb_auto_enabled"] = {
                            uid: True for uid, value in enabled_colors.items()
                            if isinstance(uid, str) and value is True and uid in self.settings["rgb_profiles"]
                        }
                    legacy_mode = loaded.get("mode")
                    self.settings["mode"] = legacy_mode if legacy_mode in ("manuel", "reel") else "manuel"
                    self._legacy_default_auto = legacy_mode == "reel"
                    modes = loaded.get("light_modes", {})
                    if isinstance(modes, dict):
                        self.settings["light_modes"] = {
                            k: v for k, v in modes.items()
                            if isinstance(k, str) and v in ("manuel", "auto")
                        }
                    states = loaded.get("manual_states", {})
                    if isinstance(states, dict):
                        for uid, value in states.items():
                            if not isinstance(uid, str) or not isinstance(value, dict):
                                continue
                            on, brightness = value.get("on"), value.get("brightness")
                            if (isinstance(on, bool) and isinstance(brightness, (int, float))
                                    and not isinstance(brightness, bool) and 1 <= brightness <= 100):
                                self.settings["manual_states"][uid] = {
                                    "on": on, "brightness": float(brightness)}
            except (OSError, ValueError, TypeError) as e:
                self.log.warning("Paramètres non chargés : %s", e)
        # Une horloge accélérée ne redémarre jamais automatiquement après reboot.
        self.clock_mode = "reel"
        self.settings["auto"] = any(v == "auto" for v in self.settings["light_modes"].values())
        # Restaurer une seule fois l'état manuel au démarrage du service, pas après
        # chaque coupure Zigbee. Un interrupteur mural doit garder son effet.
        self.manual_restore_pending = set(self.settings["manual_states"])
        if self.vacation["enabled"]:
            self.manual_restore_pending.difference_update(self.vacation["light_ids"])
        self.auto_transition_pending = set()
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
        self.vacation_last_commands = {}  # id -> dernière commande ON/OFF du moteur
        self.vacation_test = None  # simulation accélérée 60 s, jamais persistée
        self._history_resume_after = 0.0  # latence de remontée après simulation horaire
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
        # Sauvegarde atomique : toutes les courbes et préférences restent locales.
        # Le vieux champ "mode" est conservé pour les configurations v0.4.
        payload = {
            "profiles": self.settings["profiles"],
            "mode": self.settings["mode"] if self.settings["mode"] in ("manuel", "reel") else "manuel",
            "light_modes": self.settings["light_modes"],
            "manual_states": self.settings["manual_states"],
            "simple_profiles": self.settings["simple_profiles"],
            "profile_types": self.settings["profile_types"],
            "rgb_profiles": self.settings["rgb_profiles"],
            "rgb_manual": self.settings["rgb_manual"],
            "rgb_auto_enabled": self.settings["rgb_auto_enabled"],
            "vacation": self.vacation,
        }
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
            self.vacation_last_commands.clear()
            self.vacation_test = None
            self.vacation.update({"enabled": False, "light_ids": [], "schedule": [],
                                  "overrides": {}, "plan_date": ""})
            # Les anciens identifiants restent stockés pour retrouver les préférences
            # si une ampoule est temporairement absente du pont.
            self.manual_restore_pending.clear()
            self.auto_transition_pending.clear()
            self.clock_mode = "reel"
            self.settings["mode"] = "manuel"
            self._legacy_default_auto = False
            self.settings["auto"] = False
            # Un nouveau pont est une nouvelle installation : aucune lampe
            # ne doit passer automatiquement en Auto après l'association.
            for uid in self.settings["light_modes"]:
                self.settings["light_modes"][uid] = "manuel"
            self.sim["enabled"] = False
            self.sim["running"] = False
            self.sim["apply"] = False
            self.reconnect_at.clear()
            self.reconnect_latency.clear()
            self.save()
            self._events.interrupt()
            self._event_wakeup.set()

    def _vacation_test_blocks_override(self, uid):
        """Un retour du test ne doit pas activer les 10 minutes de priorité manuelle."""
        test = self.vacation_test
        return bool(test and (
            test["running"] or (
                uid in test.get("light_ids", ())
                and time.monotonic() < test.get("log_block_until", 0)
            )
        ))

    def _presence_history_suppressed(self, uid):
        """Aucun apprentissage en Vacances, test rapide ou horloge accélérée.

        Distinct de la détection d'une commande manuelle : le bouton Hue doit
        continuer à bénéficier de sa priorité de dix minutes en mode Vacances.
        Appel sous self.lock pendant poll().
        """
        if self.vacation["enabled"]:
            return True
        if self.clock_mode == "accelere" or time.monotonic() < self._history_resume_after:
            return True
        return self._vacation_test_blocks_override(uid)

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
                        if not self._presence_history_suppressed(uid):
                            self.presence_log.record(uid, l.get("metadata", {}).get("name", uid), "zigbee_connected")
                        if trial and trial.get("offline_at") is not None and trial["status"] == "hors ligne observé":
                            trial["observed_offline_seconds"] = round(time.monotonic() - trial["offline_at"], 2)
                            trial["status"] = "reconnecté"
                            trial["reconnected_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
                            self.log.info("TEST SECTEUR | %s | retour Zigbee observé après %.2fs d'état hors-ligne observé (sondage %.1fs)",
                                          l.get("metadata", {}).get("name", uid), trial["observed_offline_seconds"],
                                          POLL_INTERVAL_SECONDS)
                    elif old_online is True and online is False:
                        self.log.warning("DÉCONNEXION | %s | connexion Zigbee perdue", l.get("metadata", {}).get("name", uid))
                        if not self._presence_history_suppressed(uid):
                            self.presence_log.record(uid, l.get("metadata", {}).get("name", uid), "zigbee_disconnected")
                        if trial and trial["status"] == "armé":
                            trial["offline_at"] = time.monotonic()
                            trial["status"] = "hors ligne observé"
                            self.log.info("TEST SECTEUR | %s | perte Zigbee observée", l.get("metadata", {}).get("name", uid))
                    if uid not in self.settings["profiles"]:
                        self.settings["profiles"][uid] = copy.deepcopy(DEFAULT_POINTS)
                    if uid not in self.settings["light_modes"]:
                        self.settings["light_modes"][uid] = (
                            "auto" if self._legacy_default_auto else "manuel")
                        self.save()
                    if uid not in self.settings["manual_states"]:
                        brightness = l.get("dimming", {}).get("brightness")
                        on_value = l.get("on", {}).get("on")
                        if (isinstance(on_value, bool) and isinstance(brightness, (int, float))
                                and not isinstance(brightness, bool) and 1 <= brightness <= 100):
                            self.settings["manual_states"][uid] = {
                                "on": on_value, "brightness": float(brightness)}
                            self.save()
                    is_on = l.get("on", {}).get("on")
                    old_on = self.previous_on.get(uid)
                    # Commande externe (télécommande Hue, app Hue, bouton logiciel) :
                    # priorité 10 minutes sur cette lampe, sans apprendre nos propres commandes.
                    command = self.vacation_last_commands.get(uid)
                    own_change = (
                        command is not None and command["on"] is is_on
                        and time.time() - command["at"] < 12
                    )
                    if (self.vacation["enabled"] and uid in self.vacation["light_ids"]
                            and not self._vacation_test_blocks_override(uid)
                            and isinstance(old_on, bool) and isinstance(is_on, bool)
                            and old_on is not is_on and online is True
                            and old_online is not False and not own_change):
                        self.vacation["overrides"][uid] = {
                            "on": is_on, "until": time.time() + GRACE_SECONDS}
                        self.save()
                        self.log.info("VACANCES | priorité manuelle %s pendant 10 min | %s",
                                      "ON" if is_on else "OFF", l.get("metadata", {}).get("name", uid))
                    if old_on is False and is_on is True:
                        self.log.info("ÉTAT | %s | ON observé", l.get("metadata", {}).get("name", uid))
                        if not own_change and not self._presence_history_suppressed(uid):
                            self.presence_log.record(uid, l.get("metadata", {}).get("name", uid), "light_on")
                    elif old_on is True and is_on is False:
                        self.log.info("ÉTAT | %s | OFF observé", l.get("metadata", {}).get("name", uid))
                        if not own_change and not self._presence_history_suppressed(uid):
                            self.presence_log.record(uid, l.get("metadata", {}).get("name", uid), "light_off")
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
        # Compatibilité avec les clients API de v0.4 uniquement.
        return self.settings["mode"] if self.clock_mode == "reel" else "accelere"

    def set_clock_mode(self, mode):
        """Sélectionne l'heure réelle ou accélérée SANS changer Manuel/Auto."""
        if mode not in ("reel", "accelere"):
            raise ValueError("Horloge inconnue : reel ou accelere.")
        with self._automation_lock:
            with self.lock:
                previous = self.clock_mode
                if mode == previous:
                    return {"clock_mode": mode}
                if self.vacation["enabled"] and mode == "accelere":
                    raise ValueError("Désactiver Vacances avant la simulation horaire générale.")
                self.clock_mode = mode
                if previous == "accelere" and mode == "reel":
                    self._history_resume_after = time.monotonic() + 45
                if mode == "accelere":
                    self.sim["minute"] = wall_clock_minutes()
                self.sim["enabled"] = mode == "accelere"
                self.sim["apply"] = mode == "accelere"
                self.sim["running"] = mode == "accelere"
                self.sim["started_at"] = time.monotonic()
                self.last_sent.clear()
                self.auto_transition_pending.update(
                    uid for uid, value in self.settings["light_modes"].items() if value == "auto")
        self.log.info("HORLOGE | %s -> %s", previous, mode)
        self._event_wakeup.set()
        return {"clock_mode": mode}

    def set_light_mode(self, uid, mode):
        """Un changement d'une ampoule ne touche pas aux autres."""
        if mode not in ("manuel", "auto"):
            raise ValueError("Choisir Manuel ou Auto.")
        with self._automation_lock:
            with self.lock:
                light = self.require_light(uid)
                previous = self.settings["light_modes"].get(uid, "manuel")
                if previous == mode:
                    return {"id": uid, "mode": mode}
                if mode == "manuel":
                    # Geler l'état observé au moment où on quitte la courbe.
                    brightness = light.get("dimming", {}).get("brightness")
                    on = light.get("on", {}).get("on")
                    if isinstance(on, bool) and isinstance(brightness, (int, float)) and 1 <= brightness <= 100:
                        self.settings["manual_states"][uid] = {
                            "on": on, "brightness": float(brightness)}
                    self.auto_transition_pending.discard(uid)
                    self.manual_restore_pending.discard(uid)
                else:
                    # Prochaine passe : consigne automatique avec transition douce.
                    self.auto_transition_pending.add(uid)
                self.settings["light_modes"][uid] = mode
                self.settings["auto"] = any(v == "auto" for v in self.settings["light_modes"].values())
                self.last_sent.pop(uid, None)
                self.reconnect_pending.discard(uid)
                self.save()
        self.log.info("LAMPE | %s | %s -> %s", uid, previous, mode)
        self._event_wakeup.set()
        return {"id": uid, "mode": mode}

    def set_mode(self, mode):
        """Ancienne API globale de compatibilité ; non utilisée dans l'UI v0.5."""
        if mode not in ("manuel", "reel", "accelere"):
            raise ValueError("Mode inconnu : manuel, reel ou accelere.")
        self.set_clock_mode("accelere" if mode == "accelere" else "reel")
        with self._automation_lock:
            with self.lock:
                for light in self.lights:
                    uid = light["id"]
                    self.settings["light_modes"][uid] = "manuel" if mode == "manuel" else "auto"
                    if mode == "manuel":
                        self.auto_transition_pending.discard(uid)
                    else:
                        self.auto_transition_pending.discard(uid)  # Comportement historique API.
                self._legacy_default_auto = mode != "manuel"
                self.settings["mode"] = mode
                self.settings["auto"] = mode == "reel"
                self.last_sent.clear()
                self.save()
        self._event_wakeup.set()
        return {"mode": mode}

    def automate(self):
        # Même sans pont disponible, le test ne doit pas rester marqué actif
        # indéfiniment si ses 60 secondes sont déjà écoulées.
        with self.lock:
            test = self.vacation_test
            if test and test["running"] and time.monotonic() - test["started_monotonic"] >= 60:
                test["running"] = False
                test["status"] = "terminé"
                test["log_block_until"] = max(test.get("log_block_until", 0),
                                               time.monotonic() + 45)
                self.log.info("VACANCES TEST | délai écoulé ; reprise dès retour du pont")
        if not self.client or self.last_error:
            return
        if not self._automation_lock.acquire(blocking=False):
            return
        try:
            self._automate_locked()
            self._vacation_test_tick_locked()
            self._vacation_apply_locked()
        finally:
            self._automation_lock.release()

    def _automate_locked(self):
        with self.lock:
            clock_mode = self.clock_mode
            minute = simulated_minutes(self.sim) if clock_mode == "accelere" else wall_clock_minutes()
            lights = copy.deepcopy(self.lights)
            modes = dict(self.settings["light_modes"])
            profiles = copy.deepcopy(self.settings["profiles"])
            simple_profiles = copy.deepcopy(self.settings["simple_profiles"])
            profile_types = dict(self.settings["profile_types"])
            rgb_profiles = copy.deepcopy(self.settings["rgb_profiles"])
            rgb_enabled = dict(self.settings["rgb_auto_enabled"])
            manual = copy.deepcopy(self.settings["manual_states"])
            status = {c.get("owner", {}).get("rid"): c.get("status") for c in self.connectivity}
            reconnecting = set(self.reconnect_pending)
            restoring = set(self.manual_restore_pending)
            transitioning = set(self.auto_transition_pending)
        for light in lights:
            uid = light["id"]
            if self.vacation["enabled"] and uid in self.vacation["light_ids"]:
                continue  # Le mode Vacances a priorité sur les courbes et restaurations.
            online = status.get(light.get("owner", {}).get("rid"))
            if modes.get(uid) != "auto":
                if uid in restoring:
                    # Premier passage uniquement. Ne pas rejouer cette commande lors
                    # d'une reconnexion Zigbee ultérieure.
                    with self.lock:
                        self.manual_restore_pending.discard(uid)
                    if online == "connected" and uid in manual:
                        preference = manual[uid]
                        desired_on = preference["on"]
                        desired_brightness = preference["brightness"]
                        current_on = light.get("on", {}).get("on")
                        current_brightness = light.get("dimming", {}).get("brightness")
                        payload = {}
                        if current_on is not desired_on:
                            payload["on"] = {"on": desired_on}
                        if (desired_on and "dimming" in light and
                                (not isinstance(current_brightness, (float, int)) or
                                 abs(current_brightness - desired_brightness) >= 1)):
                            payload["dimming"] = {"brightness": desired_brightness}
                            if "dynamics" in light:
                                payload["dynamics"] = {"duration": 1500}
                        if "color" in light and uid in self.settings["rgb_manual"] and desired_on:
                            desired_xy = hsv_to_xy(
                                self.settings["rgb_manual"][uid], light["color"].get("gamut"))
                            if xy_distance(light["color"].get("xy"), desired_xy) >= 0.008:
                                payload["color"] = {"xy": desired_xy}
                                if "dynamics" in light:
                                    payload.setdefault("dynamics", {"duration": 1200})
                        if payload:
                            try:
                                self.client.resource(f"light/{uid}", "PUT", payload)
                                self.log.info("MANUEL RESTAURÉ | %s", uid)
                            except HueError as exc:
                                self.log.warning("Restauration manuelle impossible | %s | %s", uid, exc)
                continue
            if "dimming" not in light or not light.get("on", {}).get("on", False):
                continue  # Auto ne rallume jamais une ampoule éteinte.
            if online is not None and online != "connected":
                continue
            target = self._target_for(uid, minute, profiles, simple_profiles, profile_types)
            target_xy = None
            if ("color" in light and profile_types.get(uid) == "simple" and
                    rgb_enabled.get(uid) is True and uid in rgb_profiles):
                target_xy = hsv_to_xy(
                    rgb_at(rgb_profiles[uid], simple_profiles.get(uid, DEFAULT_SIMPLE_PROFILE), minute),
                    light["color"].get("gamut"))
            current = light.get("dimming", {}).get("brightness")
            last = self.last_sent.get(uid, {})
            now = time.monotonic()
            xy_changed = target_xy is not None and xy_distance(last.get("xy"), target_xy) >= 0.003
            observed_xy = light.get("color", {}).get("xy") if "color" in light else None
            # Le pont peut encore être en transition. Attendre pour détecter un
            # changement externe plutôt que répéter la même commande en boucle.
            xy_drift = (target_xy is not None and observed_xy is not None
                        and (not last or now-last["at"] >= 8)
                        and xy_distance(observed_xy, target_xy) >= 0.025)
            reconnect = uid in reconnecting
            transition = uid in transitioning
            observed_drift = (
                not reconnect and bool(last)
                and abs(target - last["target"]) < 1.0
                and isinstance(current, (float, int))
                and abs(target - current) >= 1.0
            )
            urgent_correction = reconnect or observed_drift or transition or xy_drift
            if last and now - last["at"] < COMMAND_COOLDOWN_SECONDS:
                continue
            if (not urgent_correction and last and abs(target - last["target"]) < 1.0
                    and not xy_changed and now - last["at"] < 60):
                continue
            if (isinstance(current, (float, int)) and abs(target - current) < 1.0
                    and not xy_changed and not xy_drift):
                with self.lock:
                    self.auto_transition_pending.discard(uid)
                    self.reconnect_pending.discard(uid)
                continue
            payload = {"dimming": {"brightness": max(1, min(100, target))}}
            if target_xy is not None:
                payload["color"] = {"xy": target_xy}
            if "dynamics" in light:
                payload["dynamics"] = {"duration": (2000 if transition else
                    reconnect_transition_ms(current, target) if urgent_correction else
                    1800 if clock_mode == "accelere" else
                    8000 if target_xy is not None else 3000)}
            try:
                self.client.resource(f"light/{uid}", "PUT", payload)
                with self.lock:
                    self.last_sent[uid] = {"at": now, "target": target, "xy": target_xy}
                    self.reconnect_pending.discard(uid)
                    self.auto_transition_pending.discard(uid)
                    if reconnect:
                        elapsed = round((time.monotonic() - self.reconnect_at.get(uid, now)) * 1000)
                        self.reconnect_latency[uid] = elapsed
                        self.log.info("CORRECTION RECONNEXION | %s | délai API observé %d ms", uid, elapsed)
                self.log.info("AUTO | %s | cible %.1f%% | horloge=%s", uid, target, clock_mode)
            except HueError as exc:
                self.log.error("AUTO refusé | %s | %s", uid, exc)


    def _ensure_vacation_plan(self, when):
        """Appelé sous self.lock ; une nouvelle journée recalcule 7 jours à l'avance."""
        day = when.astimezone(LOCAL_TZ).date().isoformat()
        if self.vacation["plan_date"] != day or not self.vacation["schedule"]:
            self.vacation["seed"] = self.vacation["seed"] or uuid4().hex
            self.vacation["schedule"] = build_schedule(
                self.vacation["light_ids"], self.presence_log.path,
                self.vacation["seed"], when)
            self.vacation["plan_date"] = day
            self.save()

    def set_vacation(self, enabled, light_ids=None):
        if type(enabled) is not bool:
            raise ValueError("enabled doit être true ou false.")
        with self._automation_lock:
            with self.lock:
                if enabled:
                    if self.vacation_test and self.vacation_test["running"]:
                        raise ValueError("Arrêter le test rapide avant de reconfigurer Vacances.")
                    if self.client is None or self.last_poll is None or self.last_error:
                        raise ValueError("Pont Hue non connecté.")
                    if self.clock_mode != "reel":
                        raise ValueError("Repasser l'horloge en heure réelle avant Vacances.")
                    known = {light["id"] for light in self.lights}
                    chosen = validate_selection(light_ids, known)
                    # L'activation explicite (ou la modification de sélection) renouvelle le scénario.
                    self.vacation = {"enabled": True, "light_ids": chosen, "seed": uuid4().hex,
                                     "plan_date": "", "schedule": [], "overrides": {}}
                    self.manual_restore_pending.difference_update(chosen)
                    self.auto_transition_pending.difference_update(chosen)
                    self._ensure_vacation_plan(datetime.now(LOCAL_TZ))
                else:
                    if self.vacation["enabled"]:
                        # Les commandes Vacances peuvent encore parvenir du pont après
                        # l'arrêt : exclure 45 s pour ne pas fausser les habitudes.
                        self._history_resume_after = max(
                            self._history_resume_after, time.monotonic() + 45)
                    self.vacation["enabled"] = False
                    self.vacation["overrides"] = {}
                    if self.vacation_test and self.vacation_test["running"]:
                        self.vacation_test["running"] = False
                        self.vacation_test["status"] = "interrompu"
                        self.vacation_test["log_block_until"] = time.monotonic() + 45
                self.vacation_last_commands.clear()
                self.save()
        self.log.info("VACANCES | %s", "activé" if enabled else "désactivé")
        self._event_wakeup.set()
        return self.vacation_state()

    def vacation_state(self):
        with self.lock:
            now = datetime.now(LOCAL_TZ)
            if self.vacation["enabled"]:
                self._ensure_vacation_plan(now)
            upcoming = []
            if self.vacation["enabled"]:
                for item in self.vacation["schedule"]:
                    if not isinstance(item, dict):
                        continue
                    try:
                        scheduled_time = datetime.fromisoformat(item["at"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if scheduled_time.timestamp() >= now.timestamp():
                        upcoming.append(item)
                        if len(upcoming) >= 16:
                            break
            return {
                "enabled": self.vacation["enabled"],
                "light_ids": list(self.vacation["light_ids"]),
                "test": self._vacation_test_status_locked(),
                "next_actions": upcoming,
                "overrides": {uid: val["until"] for uid, val in
                              self.vacation["overrides"].items()
                              if val["until"] > time.time()},
            }


    def set_vacation_test(self, action):
        """Test de 24 h en 60 secondes sur les lampes réelles, sans modifier le planning."""
        if action not in ("start", "stop"):
            raise ValueError("Action de test inconnue.")
        with self._automation_lock:
            with self.lock:
                if action == "stop":
                    if self.vacation_test and self.vacation_test["running"]:
                        self.vacation_test["running"] = False
                        self.vacation_test["status"] = "interrompu"
                        self.vacation_test["log_block_until"] = time.monotonic() + 45
                    self._event_wakeup.set()
                    return self._vacation_test_status_locked()

                if not self.vacation["enabled"]:
                    raise ValueError("Activer le mode Vacances avant le test rapide.")
                if self.clock_mode != "reel":
                    raise ValueError("Le test exige l'horloge en temps réel.")
                if self.vacation_test and self.vacation_test["running"]:
                    raise ValueError("Un test est déjà en cours.")
                if self.last_error or not self.client:
                    raise ValueError("Pont Hue indisponible.")
                now = datetime.now(LOCAL_TZ)
                self._ensure_vacation_plan(now)
                # Journée complète du lendemain, même si l'on lance le test le soir.
                tomorrow = now.date() + timedelta(days=1)
                full_day = []
                for item in self.vacation["schedule"]:
                    if item.get("light_id") not in self.vacation["light_ids"]:
                        continue
                    try:
                        at = datetime.fromisoformat(item["at"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if at.astimezone(LOCAL_TZ).date() == tomorrow:
                        full_day.append((at.timestamp(), item["light_id"], item["on"] is True))
                if not full_day:
                    raise ValueError("Aucun événement disponible pour le test.")
                full_day.sort()
                # Premier allumage dans environ 3 s, plutôt que 20 à 30 s de silence.
                origin = full_day[0][0] - 72 * 60
                events = []
                for item in self.vacation["schedule"]:
                    try:
                        at = datetime.fromisoformat(item["at"]).timestamp()
                    except (KeyError, TypeError, ValueError):
                        continue
                    if origin <= at < origin + 86400 and item.get("light_id") in self.vacation["light_ids"]:
                        events.append({"due": (at - origin) / 1440.0,
                                       "at": item["at"], "light_id": item["light_id"],
                                       "on": item["on"] is True})
                events.sort(key=lambda e: (e["due"], e["light_id"]))
                # À vitesse ×1440, une session de 20 min durerait 0,8 s.
                # Préserver au moins 2 s allumées par lampe pour voir le résultat.
                last_on_due = {}
                for event in events:
                    uid = event["light_id"]
                    if event["on"]:
                        last_on_due[uid] = event["due"]
                    elif uid in last_on_due:
                        event["due"] = max(event["due"], last_on_due[uid] + 2)
                events.sort(key=lambda e: (e["due"], e["light_id"]))
                started = time.monotonic()
                self.vacation_test = {
                    "running": True, "status": "en cours", "started_monotonic": started,
                    "origin": origin, "events": events, "index": 0, "duration": 60,
                    "initialized": False, "last_event": None,
                    "last_commands": {},
                    "light_ids": list(self.vacation["light_ids"]),
                    # Le pont peut annoncer les transitions après la fin de la démo.
                    # Conserver 45 s de marge pour ne pas polluer l'historique.
                    "log_block_until": started + 60 + 45,
                }
                self.log.info("VACANCES TEST | démarrage 24 heures simulées en 60 secondes")
                self._event_wakeup.set()
                return self._vacation_test_status_locked()

    def _vacation_test_status_locked(self):
        test = self.vacation_test
        if test is None:
            return {"running": False, "status": "inactif", "duration_seconds": 60}
        elapsed = max(0, min(60, time.monotonic() - test["started_monotonic"]))
        simulated = datetime.fromtimestamp(test["origin"] + elapsed * 1440, LOCAL_TZ)
        return {
            "running": bool(test["running"]), "status": test["status"],
            "elapsed_seconds": round(elapsed, 1), "duration_seconds": test["duration"],
            "simulated_time": simulated.isoformat(timespec="seconds"),
            "processed": test["index"], "total": len(test["events"]),
            "last_event": copy.deepcopy(test["last_event"]),
        }

    def _vacation_test_tick_locked(self):
        """Traite toutes les actions échues ; aucune transition courte n'est sautée."""
        with self.lock:
            test = self.vacation_test
            if not test or not test["running"]:
                return
            elapsed = time.monotonic() - test["started_monotonic"]
            if elapsed >= 60:
                test["running"] = False
                test["status"] = "terminé"
                test["log_block_until"] = max(test.get("log_block_until", 0),
                                               time.monotonic() + 45)
                self.log.info("VACANCES TEST | terminé, reprise du planning réel")
                return
            lights = {light["id"]: light for light in self.lights}
            connected = {c.get("owner", {}).get("rid"): c.get("status")
                         for c in self.connectivity}
            selected = list(self.vacation["light_ids"])
            if not test["initialized"]:
                # Partir d'une habitation éteinte au début de la journée simulée.
                test["initialized"] = True
                to_send = [(uid, False, None) for uid in selected]
            else:
                to_send = []
            while test["index"] < len(test["events"]):
                event = test["events"][test["index"]]
                if event["due"] > elapsed:
                    break
                test["index"] += 1
                to_send.append((event["light_id"], event["on"], event))

        for uid, on, event in to_send:
            light = lights.get(uid)
            if not light or connected.get(light.get("owner", {}).get("rid")) != "connected":
                continue
            # En début de simulation, n'éteindre que les lampes actuellement ON.
            if event is None and light.get("on", {}).get("on") is not True:
                continue
            payload = {"on": {"on": on}}
            if on and "dimming" in light:
                payload["dimming"] = {"brightness": 55}
                if "dynamics" in light:
                    payload["dynamics"] = {"duration": 600}
            try:
                self.client.resource(f"light/{uid}", "PUT", payload)
                with self.lock:
                    self.vacation_last_commands[uid] = {"on": on, "at": time.time()}
                    if event and self.vacation_test is test:
                        test["last_event"] = {
                            "light_id": uid, "on": on, "at": event["at"]}
                self.log.info("VACANCES TEST | %s | %s",
                              light.get("metadata", {}).get("name", uid), "ON" if on else "OFF")
            except HueError as exc:
                self.log.warning("VACANCES TEST | commande refusée sur %s : %s", uid, exc)

        with self.lock:
            if self.vacation_test is test and test["running"]:
                # Fin normale : retour immédiat au planning Vacances réel.
                if time.monotonic() - test["started_monotonic"] >= 60:
                    test["running"] = False
                    test["status"] = "terminé"
                    test["log_block_until"] = max(test.get("log_block_until", 0),
                                                   time.monotonic() + 45)
                    self.log.info("VACANCES TEST | terminé, reprise du planning réel")

    def _vacation_apply_locked(self):
        """Appelé uniquement sous _automation_lock, jamais en parallèle des autres commandes."""
        with self.lock:
            if not self.vacation["enabled"] or (
                    self.vacation_test and self.vacation_test["running"]):
                return
            now = datetime.now(LOCAL_TZ)
            self._ensure_vacation_plan(now)
            selected = list(self.vacation["light_ids"])
            desired = desired_states(self.vacation["schedule"], now, selected)
            current_time = time.time()
            overrides = self.vacation["overrides"]
            expired = [uid for uid, val in overrides.items() if val["until"] <= current_time]
            if expired:
                for uid in expired:
                    del overrides[uid]
                self.save()
            for uid, val in overrides.items():
                if uid in desired:
                    desired[uid] = val["on"]
            lights = {light["id"]: light for light in self.lights}
            connected = {c.get("owner", {}).get("rid"): c.get("status")
                         for c in self.connectivity}

        for uid, should_on in desired.items():
            light = lights.get(uid)
            if not light or connected.get(light.get("owner", {}).get("rid")) != "connected":
                continue  # Courant coupé ou état inconnu : aucune commande dangereuse.
            currently_on = light.get("on", {}).get("on")
            if not isinstance(currently_on, bool) or currently_on == should_on:
                continue
            previous = self.vacation_last_commands.get(uid)
            if previous and previous["on"] == should_on and current_time - previous["at"] < 5:
                continue
            payload = {"on": {"on": should_on}}
            if should_on and "dimming" in light:
                brightness = light.get("dimming", {}).get("brightness", 55)
                payload["dimming"] = {"brightness": min(75, max(25, brightness or 55))}
                if "dynamics" in light:
                    payload["dynamics"] = {"duration": 1200}
            try:
                self.client.resource(f"light/{uid}", "PUT", payload)
                with self.lock:
                    self.vacation_last_commands[uid] = {"on": should_on, "at": time.time()}
                self.log.info("VACANCES | %s | %s", light.get("metadata", {}).get("name", uid),
                              "ON" if should_on else "OFF")
            except HueError as exc:
                self.log.warning("VACANCES | lampe %s non commandée : %s", uid, exc)

    def get_lights(self):
        with self.lock:
            m = self.simulated_time()
            connections = {c.get("owner", {}).get("rid"): c.get("status") for c in self.connectivity}
            devices = {d.get("id"): d for d in self.devices}
            result = []
            for l in self.lights:
                owner = l.get("owner", {}).get("rid")
                dev = devices.get(owner, {})
                uid = l["id"]
                result.append({
                    "id": l["id"],
                    "name": l.get("metadata", {}).get("name", "Ampoule"),
                    "on": l.get("on", {}).get("on"),
                    "brightness": l.get("dimming", {}).get("brightness"),
                    "target": self._target_for(uid, m),
                    "profile_type": self.settings["profile_types"].get(uid, "custom"),
                    "rgb_auto": bool(self.settings["rgb_auto_enabled"].get(uid)),
                    "color_xy": copy.deepcopy(l.get("color", {}).get("xy")),
                    "control_mode": self.settings["light_modes"].get(l["id"], "manuel"),
                    "manual_state": copy.deepcopy(self.settings["manual_states"].get(l["id"])),
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
                "auto": self.settings["auto"],  # Ancien indicateur compatible v0.4.
                "auto_count": sum(l.get("control_mode") == "auto" for l in self.get_lights()),
                "clock_mode": self.clock_mode,
                "simulation": public_sim(self.sim),
                "mode": self._mode(),
                "minute": round(self.simulated_time(), 3),
                "lights": self.get_lights(),
            }

    def _target_for(self, uid, minute, profiles=None, simple_profiles=None, profile_types=None):
        """Consigne calculée selon le type actif de chaque lampe (verrou déjà pris)."""
        types = self.settings["profile_types"] if profile_types is None else profile_types
        if types.get(uid) == "simple":
            data = self.settings["simple_profiles"] if simple_profiles is None else simple_profiles
            return simple_brightness_at(data.get(uid, DEFAULT_SIMPLE_PROFILE), minute)
        data = self.settings["profiles"] if profiles is None else profiles
        return brightness_at(data.get(uid, DEFAULT_POINTS), minute)

    def profile(self, uid):
        with self.lock:
            self.require_light(uid)
            return copy.deepcopy(self.settings["profiles"].get(uid, DEFAULT_POINTS))

    def simple_profile(self, uid):
        with self.lock:
            self.require_light(uid)
            return {
                "type": self.settings["profile_types"].get(uid, "custom"),
                "params": copy.deepcopy(self.settings["simple_profiles"].get(uid, DEFAULT_SIMPLE_PROFILE)),
            }

    def _profile_changed(self, uid):
        """Laisse la transition automatique rejoindre la nouvelle consigne en douceur."""
        self.last_sent.pop(uid, None)
        self.auto_transition_pending.add(uid)

    def set_simple_profile(self, uid, params):
        cleaned = validate_simple_profile(params)
        with self.lock:
            self.require_light(uid)
            self.settings["simple_profiles"][uid] = cleaned
            self.settings["profile_types"][uid] = "simple"
            self._profile_changed(uid)
            self.save()
        self.log.info("PROFIL SIMPLE | %s | courbe activée", uid)
        return {"type": "simple", "params": copy.deepcopy(cleaned)}

    def set_profile_type(self, uid, kind):
        if kind not in ("simple", "custom"):
            raise ValueError("Type de courbe inconnu.")
        with self.lock:
            self.require_light(uid)
            if kind == "simple":
                self.settings["simple_profiles"].setdefault(uid, copy.deepcopy(DEFAULT_SIMPLE_PROFILE))
            if self.settings["profile_types"].get(uid, "custom") != kind:
                self.settings["profile_types"][uid] = kind
                self._profile_changed(uid)
                self.save()
        self.log.info("PROFIL ACTIF | %s | %s", uid, kind)
        return self.simple_profile(uid)

    def rgb_profile(self, uid):
        """Données du sélecteur, sans exposer la clé Hue ni les autres lampes."""
        with self.lock:
            light = self.require_light(uid)
            manual = self.settings["manual_states"].get(uid, {})
            return {
                "mode": self.settings["light_modes"].get(uid, "manuel"),
                "profile_type": self.settings["profile_types"].get(uid, "custom"),
                "simple_params": copy.deepcopy(self.settings["simple_profiles"].get(uid, DEFAULT_SIMPLE_PROFILE)),
                "colors": copy.deepcopy(self.settings["rgb_profiles"].get(uid, DEFAULT_RGB_PHASES)),
                "manual": {**copy.deepcopy(self.settings["rgb_manual"].get(uid, DEFAULT_MANUAL_COLOR)),
                           "b": int(round(manual.get("brightness", light.get("dimming", {}).get("brightness", 65)) or 65))},
                "enabled": bool(self.settings["rgb_auto_enabled"].get(uid)),
                "capable": "color" in light and "dimming" in light,
                "on": light.get("on", {}).get("on") is True,
                "online": (next((c.get("status") for c in self.connectivity
                                 if c.get("owner", {}).get("rid") == light.get("owner", {}).get("rid")), None)
                           == "connected"),
            }

    def save_rgb_profile(self, uid, data):
        """Validation intégrale puis sauvegarde atomique par lampe.

        Manuel : appliquer la teinte uniquement si la lampe est déjà allumée.
        Auto : activer le profil Simple et laisser le worker gérer la transition.
        """
        if not isinstance(data, dict) or set(data) != {"mode", "colors", "simple_params", "manual"}:
            raise ValueError("Configuration RGB incomplète.")
        mode = data["mode"]
        if mode not in ("manuel", "auto"):
            raise ValueError("Mode RGB invalide.")
        colors = validate_rgb_phases(data["colors"])
        params = validate_simple_profile(data["simple_params"])
        manual_raw = data["manual"]
        if not isinstance(manual_raw, dict) or set(manual_raw) != {"h", "s", "b"}:
            raise ValueError("Couleur manuelle incomplète.")
        manual = validate_hs({"h": manual_raw["h"], "s": manual_raw["s"]})
        brightness = manual_raw["b"]
        if type(brightness) is not int or not 1 <= brightness <= 100:
            raise ValueError("Luminosité manuelle : 1 à 100 %.")
        with self._automation_lock:
            with self.lock:
                light = self.require_light(uid)
                if "color" not in light or "dimming" not in light:
                    raise ValueError("Cette lampe ne permet pas le pilotage RGB.")
                current_on = light.get("on", {}).get("on") is True
                online = (next((c.get("status") for c in self.connectivity
                                if c.get("owner", {}).get("rid") == light.get("owner", {}).get("rid")), None)
                          == "connected")
                xy = hsv_to_xy(manual, light["color"].get("gamut"))
            if mode == "manuel" and current_on and online:
                payload = {"color": {"xy": xy}, "dimming": {"brightness": float(brightness)}}
                if "dynamics" in light:
                    payload["dynamics"] = {"duration": 900}
                # Si le pont refuse, ne pas prétendre avoir enregistré.
                self.client.resource(f"light/{uid}", "PUT", payload)
            with self.lock:
                self.settings["rgb_profiles"][uid] = colors
                self.settings["rgb_manual"][uid] = manual
                self.settings["simple_profiles"][uid] = params
                self.settings["rgb_auto_enabled"][uid] = True
                self.settings["light_modes"][uid] = mode
                if mode == "auto":
                    self.settings["profile_types"][uid] = "simple"
                    self.auto_transition_pending.add(uid)
                else:
                    self.auto_transition_pending.discard(uid)
                    self.manual_restore_pending.discard(uid)
                    self.settings["manual_states"][uid] = {
                        "on": current_on, "brightness": float(brightness)}
                self.settings["auto"] = any(v=="auto" for v in self.settings["light_modes"].values())
                self.last_sent.pop(uid, None)
                self.save()
        self.log.info("RGB | %s | %s | couleurs enregistrées", uid, mode)
        self._event_wakeup.set()
        return self.rgb_profile(uid)

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
            self.settings["profile_types"][uid] = "custom"
            self._profile_changed(uid)
            self.save()
        self.log.info("PROFIL | %s | %d points sauvegardés", uid, len(cleaned))
        return cleaned

    def set_sim(self, data):
        allowed = {"running", "seconds_per_day", "minute"}
        if not isinstance(data, dict) or set(data) - allowed:
            raise ValueError("Paramètres de simulation invalides.")
        with self.lock:
            if self.clock_mode != "accelere":
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
        if not isinstance(on, bool):
            raise ValueError("on doit être vrai ou faux")
        with self._automation_lock:
            with self.lock:
                light = self.require_light(uid)
                supports_dimming = "dimming" in light
                name = light.get("metadata", {}).get("name", uid)
                mode = self.settings["light_modes"].get(uid, "manuel")
                current_brightness = light.get("dimming", {}).get("brightness")
                stored = self.settings["manual_states"].get(uid, {})
                if mode == "auto":
                    target = self._target_for(uid, self.simulated_time())
                else:
                    target = stored.get("brightness", current_brightness or 50)
            payload = {"on": {"on": on}}
            if on and supports_dimming:
                selected = brightness if brightness is not None else target
                if isinstance(selected, bool) or not isinstance(selected, (float, int)) or not 1 <= selected <= 100:
                    raise ValueError("Luminosité : 1 à 100 %")
                payload["dimming"] = {"brightness": float(selected)}
            if on and "color" in light:
                choice = None
                if mode == "manuel":
                    choice = self.settings["rgb_manual"].get(uid)
                elif (self.settings["profile_types"].get(uid, "custom") == "simple"
                      and self.settings["rgb_auto_enabled"].get(uid)
                      and uid in self.settings["rgb_profiles"]):
                    choice = rgb_at(
                        self.settings["rgb_profiles"][uid],
                        self.settings["simple_profiles"].get(uid, DEFAULT_SIMPLE_PROFILE),
                        self.simulated_time())
                if choice:
                    payload["color"] = {"xy": hsv_to_xy(choice, light["color"].get("gamut"))}
            self.client.resource(f"light/{uid}", "PUT", payload)
            with self.lock:
                self.last_user_action[uid] = time.monotonic()
                self.last_sent.pop(uid, None)
                if mode == "manuel":
                    self.manual_restore_pending.discard(uid)
                    self.settings["manual_states"][uid] = {
                        "on": on, "brightness": float(payload.get("dimming", {}).get("brightness", target))}
                    self.save()
                else:
                    self.auto_transition_pending.add(uid)
        self.log.info("COMMANDE | %s | %s", name, payload)
        self._event_wakeup.set()

    def set_brightness(self, uid, brightness):
        if isinstance(brightness, bool) or not isinstance(brightness, (float, int)) or not 1 <= brightness <= 100:
            raise ValueError("La luminosité doit être entre 1 et 100 %.")
        with self._automation_lock:
            with self.lock:
                light = self.require_light(uid)
                if self.settings["light_modes"].get(uid, "manuel") == "auto":
                    raise ValueError("Passe cette lampe en Manuel pour régler librement sa luminosité.")
                if "dimming" not in light:
                    raise ValueError("Cette ampoule ne propose pas le réglage de luminosité.")
            payload = {"dimming": {"brightness": float(brightness)}}
            if "dynamics" in light:
                payload["dynamics"] = {"duration": 400}
            self.client.resource(f"light/{uid}", "PUT", payload)
            with self.lock:
                manual = self.settings["manual_states"].get(uid, {})
                self.settings["manual_states"][uid] = {
                    "on": bool(manual.get("on", light.get("on", {}).get("on", True))),
                    "brightness": float(brightness)}
                self.manual_restore_pending.discard(uid)
                self.last_sent.pop(uid, None)
                self.save()
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
    # Compatibilité des scripts existants (choisit toutes les lampes).
    return ok(controller.set_mode(data.get("mode")))


@app.post("/api/clock-mode")
def clock_mode(data: dict = Body(...)):
    return ok(controller.set_clock_mode(data.get("mode")))


@app.post("/api/light/{uid}/control-mode")
def light_control_mode(uid: str, data: dict = Body(...)):
    return ok(controller.set_light_mode(uid, data.get("mode")))


@app.post("/api/simulation")
def simulation(data: dict = Body(...)):
    return ok(controller.set_sim(data))


@app.get("/api/profile/{uid}")
def profile(uid: str):
    return ok(controller.profile(uid))


@app.put("/api/profile/{uid}")
def set_profile(uid: str, data: dict = Body(...)):
    return ok(controller.set_profile(uid, data.get("points")))


@app.get("/api/profile/simple/{uid}")
def simple_profile(uid: str):
    return ok(controller.simple_profile(uid))


@app.put("/api/profile/simple/{uid}")
def update_simple_profile(uid: str, data: dict = Body(...)):
    return ok(controller.set_simple_profile(uid, data.get("params")))


@app.post("/api/profile/type/{uid}")
def update_profile_type(uid: str, data: dict = Body(...)):
    return ok(controller.set_profile_type(uid, data.get("type")))


@app.get("/api/rgb/{uid}")
def rgb_profile(uid: str):
    return ok(controller.rgb_profile(uid))


@app.put("/api/rgb/{uid}")
def save_rgb_profile(uid: str, data: dict = Body(...)):
    return ok(controller.save_rgb_profile(uid, data))


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


@app.post("/api/vacation/test")
def vacation_test(data: dict = Body(...)):
    return ok(controller.set_vacation_test(data.get("action")))


@app.get("/api/vacation")
def get_vacation():
    return ok(controller.vacation_state())


@app.post("/api/vacation")
def post_vacation(data: dict = Body(...)):
    return ok(controller.set_vacation(data.get("enabled"), data.get("light_ids")))


@app.get("/api/presence/events")
def presence_events(limit: int = 40):
    """Lecture seule : observations récentes, jamais les clés du pont."""
    return ok(controller.presence_log.recent(limit))


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
