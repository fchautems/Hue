"""Interface sécurisée entre Hue Lab et le service systemd de mise à jour.

Le serveur Web ne manipule jamais Git directement et n'arrête jamais son propre
processus. Toutes les commandes systemctl utilisent des noms d'unités fixes.
"""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

HOME = Path.home()
STATUS_FILE = Path(os.environ.get("HUE_UPDATE_STATUS_FILE", HOME / ".local/state/hue-lab-update/status.json"))
MANAGER_WORKER = Path(os.environ.get("HUE_UPDATE_WORKER_PATH", HOME / ".local/share/hue-lab-updater/worker.py"))
UPDATE_SERVICE = Path(os.environ.get("HUE_UPDATE_SERVICE_PATH", HOME / ".config/systemd/user/hue-lab-update@.service"))
UNITS = {"check": "hue-lab-update@check.service", "apply": "hue-lab-update@apply.service"}


def _lan_address(value: str) -> bool:
    """N'autorise que les adresses locales ou privées, jamais les noms DNS."""
    if value == "localhost":
        return True
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in network for network in (
            ipaddress.IPv4Network("10.0.0.0/8"),
            ipaddress.IPv4Network("172.16.0.0/12"),
            ipaddress.IPv4Network("192.168.0.0/16"),
        ))
    return ip in ipaddress.IPv6Network("fc00::/7") or ip.is_link_local


def authorized_browser_request(request) -> bool:
    """Protège le bouton sans PIN contre CSRF, DNS rebinding et accès Internet.

    Pas d'authentification des autres utilisateurs du LAN : Hue Lab doit rester
    sur un réseau domestique de confiance, sans exposition publique du port.
    """
    if request.headers.get("x-hue-update-request") != "1":
        return False
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return False
    host = request.headers.get("host", "")
    try:
        target = urlsplit("http://" + host)
        valid_host = (bool(target.hostname) and target.username is None and
                      target.password is None and not target.path and
                      not target.query and not target.fragment and
                      target.port in (None, 8765) and _lan_address(target.hostname))
    except ValueError:
        return False
    if not valid_host:
        return False
    if not request.client or not _lan_address(request.client.host):
        return False
    origin = f"{request.url.scheme}://{host}"
    # La page elle-même doit avoir ouvert une requête, pas un site tiers.
    submitted_origin = request.headers.get("origin")
    if submitted_origin:
        if submitted_origin != origin:
            return False
    else:
        referer = request.headers.get("referer", "")
        source = urlsplit(referer)
        if not referer or f"{source.scheme}://{source.netloc}" != origin:
            return False
    if request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        return False
    return True


def worker_installed() -> bool:
    return MANAGER_WORKER.is_file() and UPDATE_SERVICE.is_file()


def status() -> dict:
    data = {"configured": worker_installed(), "phase": "idle", "busy": False}
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
    if not worker_installed():
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
