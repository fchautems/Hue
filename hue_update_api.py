"""Interface sécurisée entre Hue Lab et le service systemd de mise à jour.

Le serveur Web ne manipule jamais Git directement et n'arrête jamais son propre
processus. Toutes les commandes systemctl utilisent des noms d'unités fixes.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import subprocess
import time

HOME = Path.home()
PIN_FILE = Path(os.environ.get("HUE_UPDATE_PIN_FILE", HOME / ".config/hue-lab/update-pin.json"))
STATUS_FILE = Path(os.environ.get("HUE_UPDATE_STATUS_FILE", HOME / ".local/state/hue-lab-update/status.json"))
APP_DIR = Path(os.environ.get("HUE_UPDATE_APP_DIR", HOME / "hue-lab"))
UNITS = {"check": "hue-lab-update@check.service", "apply": "hue-lab-update@apply.service"}
# Une protection simple contre les essais répétés, en plus du hachage PBKDF2.
_failures: dict[str, tuple[int, float]] = {}


def authorize_pin(pin: object, client_ip: str = "") -> bool:
    if not isinstance(pin, str) or len(pin) > 128:
        return False
    now = time.monotonic()
    count, until = _failures.get(client_ip, (0, 0.0))
    if until > now:
        return False
    try:
        record = json.loads(PIN_FILE.read_text(encoding="utf-8"))
        salt = bytes.fromhex(record["salt"])
        expected = bytes.fromhex(record["hash"])
        iterations = int(record["iterations"])
        if not 100_000 <= iterations <= 1_000_000 or len(salt) != 16 or len(expected) != 32:
            return False
    except (OSError, ValueError, TypeError, KeyError):
        return False
    supplied = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    valid = hmac.compare_digest(supplied, expected)
    if valid:
        _failures.pop(client_ip, None)
    else:
        count += 1
        _failures[client_ip] = (count, now + 60 if count >= 5 else 0.0)
    return valid


def status() -> dict:
    data = {"configured": PIN_FILE.is_file(), "phase": "idle", "busy": False}
    if STATUS_FILE.is_file():
        try:
            raw = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key in ("phase", "busy", "message", "installed", "remote", "available", "updated_at", "rollback"):
                    if key in raw:
                        data[key] = raw[key]
        except (OSError, ValueError, TypeError):
            pass
    return data


def trigger(action: str) -> None:
    if action not in UNITS:
        raise ValueError("Action de mise à jour non reconnue")
    if not PIN_FILE.is_file():
        raise RuntimeError("Le service de mise à jour n'a pas encore été installé.")
    current = status()
    if current.get("busy"):
        raise RuntimeError("Une opération de mise à jour est déjà en cours.")
    try:
        result = subprocess.run(
            ["systemctl", "--user", "start", "--no-block", UNITS[action]],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Impossible de contacter le service de mise à jour.") from exc
    if result.returncode:
        raise RuntimeError("Le service de mise à jour n'a pas pu être lancé. Consulte les journaux systemd.")
