#!/usr/bin/env python3
"""Moteur indépendant de Hue Lab, lancé par systemd --user (oneshot).

Seul ce processus effectue git fetch, sauvegardes et redémarrages.
Il reste hors de ~/hue-lab afin de survivre aux modifications du dépôt.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid

HOME = Path.home()
APP = Path(os.environ.get("HUE_UPDATE_APP_DIR", HOME / "hue-lab"))
STATE = Path(os.environ.get("HUE_UPDATE_STATE_DIR", HOME / ".local/state/hue-lab-update"))
MANAGER = Path(os.environ.get("HUE_UPDATE_MANAGER_DIR", HOME / ".local/share/hue-lab-updater"))
BACKUPS = MANAGER / "backups"
CONFIG_FILES = (".hue_config.json", "hue_settings.json")
SERVICE = "hue-lab.service"
HEALTH_URL = os.environ.get("HUE_UPDATE_HEALTH_URL", "http://127.0.0.1:8765/api/state")


def cmd(*parts: str, cwd: Path | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(parts, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode:
        # Ne jamais faire remonter les sorties de processus: elles peuvent contenir des secrets.
        raise RuntimeError(f"Commande échouée : {parts[0]} (code {proc.returncode})")
    return proc


def git(*args: str, timeout: int = 120) -> str:
    return cmd("git", "-C", str(APP), *args, timeout=timeout).stdout.strip()


def write_status(phase: str, message: str, **fields: object) -> None:
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = {
        "phase": phase,
        "busy": phase in ("checking", "preparing", "installing", "restarting", "rolling_back"),
        "message": message[:300],
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        **fields,
    }
    tmp = STATE / ("status.json." + uuid.uuid4().hex + ".tmp")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(body, out, ensure_ascii=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        tmp.replace(STATE / "status.json")
    finally:
        tmp.unlink(missing_ok=True)


def fetch_versions() -> tuple[str, str]:
    if not (APP / ".git").exists():
        raise RuntimeError("Installation non migrée vers Git (lance le bootstrap Termux).")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Des fichiers du programme ont été modifiés localement : mise à jour refusée.")
    installed = git("rev-parse", "HEAD")
    git("fetch", "--no-tags", "origin", "main", timeout=180)
    remote = git("rev-parse", "FETCH_HEAD")
    if installed != remote:
        ancestor = cmd("git", "-C", str(APP), "merge-base", "--is-ancestor", installed, remote, check=False)
        if ancestor.returncode:
            raise RuntimeError("L'historique Git a divergé : intervention manuelle nécessaire.")
    return installed, remote


def backup_config(installed: str) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory = BACKUPS / (dt.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + installed[:9] + "-" + uuid.uuid4().hex[:6])
    directory.mkdir(mode=0o700)
    for name in CONFIG_FILES:
        source = APP / name
        if source.is_symlink():
            raise RuntimeError(f"Fichier de configuration symbolique non pris en charge : {name}")
        if source.is_file():
            shutil.copy2(source, directory / name)
            (directory / name).chmod(0o600)
    return directory


def restore_config(backup: Path) -> None:
    for name in CONFIG_FILES:
        file = backup / name
        if file.is_file():
            shutil.copy2(file, APP / name)
            (APP / name).chmod(0o600)


def healthy(seconds: int = 60) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
                if response.status == 200:
                    data = json.load(response)
                    if isinstance(data, dict) and "lights" in data:
                        return True
        except (OSError, ValueError, TimeoutError):
            pass
        time.sleep(2)
    return False


def install_worker_for_next_run() -> None:
    source = APP / "updater/worker.py"
    target = MANAGER / "worker.py"
    if not source.is_file():
        return
    MANAGER.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = MANAGER / ("worker." + uuid.uuid4().hex + ".tmp")
    try:
        shutil.copy2(source, temporary)
        temporary.chmod(0o700)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def update(action: str) -> None:
    write_status("checking", "Vérification du dépôt GitHub…")
    installed, remote = fetch_versions()
    if action == "check":
        write_status("ready", "Une mise à jour est disponible." if installed != remote else "Hue Lab est à jour.",
                     installed=installed[:12], remote=remote[:12], available=installed != remote)
        return
    if installed == remote:
        write_status("success", "Hue Lab est déjà à jour.", installed=installed[:12], remote=remote[:12], available=False)
        return
    write_status("preparing", "Sauvegarde des réglages et préparation de la mise à jour…", installed=installed[:12], remote=remote[:12])
    backup = backup_config(installed)
    # Le code cible est contrôlé sans l'installer dans le répertoire actif.
    current_req = git("show", "HEAD:requirements.txt")
    next_req = git("show", f"{remote}:requirements.txt")
    with tempfile.TemporaryDirectory(prefix="hue-update-") as temp:
        staging = Path(temp)
        result = subprocess.run(["git", "-C", str(APP), "archive", "--format=tar", remote], capture_output=True, timeout=100)
        if result.returncode:
            raise RuntimeError("Impossible de préparer l'archive de la nouvelle version.")
        import tarfile
        import io
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for entry in archive.getmembers():
                if not entry.isfile() and not entry.isdir():
                    raise RuntimeError("Archive Git inattendue.")
                if entry.name.startswith("/") or ".." in Path(entry.name).parts:
                    raise RuntimeError("Chemin inattendu dans l'archive Git.")
            archive.extractall(staging)  # types/chemins contrôlés ci-dessus (Python 3.11 compatible)
        # Préparer les dépendances avant tout arrêt, à partir du fichier CIBLE.
        if current_req != next_req:
            cmd(str(APP / ".venv/bin/python"), "-m", "pip", "install", "-r", str(staging / "requirements.txt"), timeout=240)
        cmd(str(APP / ".venv/bin/python"), "-m", "compileall", "-q", str(staging), timeout=120)
        test_env = dict(os.environ, PYTHONPATH=str(staging))
        tested = subprocess.run([str(APP / ".venv/bin/python"), "-m", "unittest", "discover", "-s", "tests", "-q"],
                                cwd=staging, env=test_env, capture_output=True, timeout=180)
        if tested.returncode:
            raise RuntimeError("Les tests de la nouvelle version ont échoué avant déploiement.")
    write_status("installing", "Installation de la nouvelle version…", installed=installed[:12], remote=remote[:12])
    stopped = False
    try:
        cmd("systemctl", "--user", "stop", SERVICE, timeout=30)
        stopped = True
        git("merge", "--ff-only", remote, timeout=90)
        write_status("restarting", "Redémarrage de Hue Lab et vérification…", installed=installed[:12], remote=remote[:12])
        cmd("systemctl", "--user", "start", SERVICE, timeout=45)
        if not healthy():
            raise RuntimeError("Le nouveau serveur ne répond pas après redémarrage.")
        install_worker_for_next_run()
        write_status("success", "Mise à jour installée et serveur opérationnel.",
                     installed=remote[:12], remote=remote[:12], available=False, rollback=False)
    except Exception as exc:
        if stopped:
            write_status("rolling_back", "Échec du déploiement : restauration de l'ancienne version…",
                         installed=installed[:12], remote=remote[:12])
            try:
                cmd("systemctl", "--user", "stop", SERVICE, timeout=30, check=False)
                git("reset", "--hard", installed)
                restore_config(backup)
                cmd("systemctl", "--user", "start", SERVICE, timeout=45)
                restored = healthy(seconds=30)
                write_status("error", "Mise à jour annulée. Ancienne version restaurée." if restored else "Échec : restauration effectuée mais serveur indisponible.",
                             installed=installed[:12], remote=remote[:12], available=True, rollback=True)
            except Exception:
                write_status("error", "Restauration automatique impossible. Intervention via Termux nécessaire.",
                             installed=installed[:12], remote=remote[:12], rollback=False)
        else:
            write_status("error", "Mise à jour non appliquée : " + str(exc), installed=installed[:12], remote=remote[:12])
        raise


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("check", "apply"):
        print("Usage: worker.py check|apply", file=sys.stderr)
        return 2
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / "update.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        try:
            update(sys.argv[1])
            return 0
        except Exception as exc:
            if sys.argv[1] == "check":
                write_status("error", "Vérification impossible : " + str(exc))
            else:
                try:
                    data = json.loads((STATE / "status.json").read_text(encoding="utf-8"))
                    if data.get("busy"):
                        write_status("error", "Mise à jour interrompue avant installation : " + str(exc))
                except (OSError, ValueError):
                    write_status("error", "Mise à jour interrompue.")
            print(f"Hue Update : {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(main())
