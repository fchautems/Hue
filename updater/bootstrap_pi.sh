#!/usr/bin/env bash
# Première migration Raspberry Hue Lab archive -> dépôt Git + mise à jour autonome.
# Depuis Termux, en SSH sur le Raspberry, lancer ce fichier sans sudo.
set -Eeuo pipefail
umask 077

APP="$HOME/hue-lab"
MANAGER="$HOME/.local/share/hue-lab-updater"
UNITS="$HOME/.config/systemd/user"
PIN_FILE="$HOME/.config/hue-lab/update-pin.json"
REPOSITORY="https://github.com/fchautems/Hue.git"

fail() { printf 'ERREUR : %s\n' "$*" >&2; exit 1; }
[[ $EUID -ne 0 ]] || fail 'Ne lance pas ce script avec sudo.'
command -v git >/dev/null || fail 'Git absent : installe git sur le Raspberry avant de poursuivre.'
command -v systemctl >/dev/null || fail 'systemctl est introuvable.'
[[ -d "$APP" && -x "$APP/.venv/bin/python" ]] || fail "Installation existante introuvable : $APP"
[[ ! -e "$APP/.git" ]] || fail 'Le dossier est déjà un dépôt Git : migration initiale inutile.'
[[ -f "$UNITS/hue-lab.service" ]] || fail 'Service utilisateur hue-lab.service introuvable.'
if ! systemctl --user is-active --quiet hue-lab.service; then
  fail 'Hue Lab ne fonctionne pas. Répare le service avant une migration.'
fi

printf '\nMigration Hue Lab v0.4 — aucune action effectuée sur les lampes.\n'
printf 'Le dossier actuel sera conservé comme sauvegarde du code et des réglages.\n'
printf 'Saisis un code de mise à jour (au moins 8 caractères) : '
IFS= read -rs PIN
printf '\nConfirme le code : '
IFS= read -rs PIN2
printf '\n'
[[ ${#PIN} -ge 8 && ${#PIN} -le 128 ]] || fail 'Le code doit contenir de 8 à 128 caractères.'
[[ "$PIN" == "$PIN2" ]] || fail 'Les deux codes sont différents.'

STAMP="$(date +%Y%m%d-%H%M%S)"
STAGING="$HOME/.hue-lab-stage-$STAMP-$$"
BACKUP="$HOME/hue-lab-avant-v04-$STAMP"
[[ ! -e "$STAGING" && ! -e "$BACKUP" ]] || fail 'Dossier temporaire ou sauvegarde déjà présent.'
printf '\n1/5 — Téléchargement GitHub dans un nouveau dossier...\n'
git clone --depth 1 --branch main "$REPOSITORY" "$STAGING"
[[ -f "$STAGING/updater/worker.py" && -f "$STAGING/hue_update_api.py" ]] || fail 'GitHub ne contient pas encore la v0.4 complète.'

# Les tests du nouveau code sont effectués AVANT d'arrêter le serveur.
printf '2/5 — Contrôles de syntaxe et tests...\n'
"$APP/.venv/bin/python" -m compileall -q "$STAGING"
PYTHONPATH="$STAGING" "$APP/.venv/bin/python" -m unittest discover -s "$STAGING/tests" -q

# Créer le code PIN avant activation du bouton. Pas de secret stocké dans Git.
mkdir -p "$(dirname "$PIN_FILE")"
PIN="$PIN" PIN_FILE="$PIN_FILE" "$APP/.venv/bin/python" - <<'PY'
import hashlib, json, os, pathlib, secrets
p = pathlib.Path(os.environ['PIN_FILE'])
salt = secrets.token_bytes(16)
record = {'salt': salt.hex(), 'iterations': 180000,
          'hash': hashlib.pbkdf2_hmac('sha256', os.environ['PIN'].encode(), salt, 180000).hex()}
tmp = p.with_name(p.name + '.tmp')
tmp.write_text(json.dumps(record) + '\n', encoding='utf-8')
tmp.chmod(0o600)
tmp.replace(p)
PY
unset PIN PIN2

# Conserver le processus updater en DEHORS du dépôt, pour pouvoir remplacer le code.
mkdir -p "$MANAGER" "$UNITS" "$HOME/.local/state/hue-lab-update"
chmod 700 "$MANAGER" "$HOME/.local/state/hue-lab-update" "$(dirname "$PIN_FILE")"
install -m 700 "$STAGING/updater/worker.py" "$MANAGER/worker.py"
install -m 600 "$STAGING/systemd/hue-lab-update@.service" "$UNITS/hue-lab-update@.service"
install -m 600 "$STAGING/systemd/hue-lab-update-check.timer" "$UNITS/hue-lab-update-check.timer"

# Aucun nouveau service ne sera démarré si la migration du dossier échoue.
printf '3/5 — Sauvegarde complète puis migration sans perdre tes réglages...\n'
switched=0
rollback() {
  local code=$?
  trap - ERR
  if [[ $switched == 1 ]]; then
    printf 'Échec : restauration de l’ancienne installation...\n' >&2
    systemctl --user stop hue-lab.service || true
    if [[ -d "$APP/.venv" && ! -e "$BACKUP/.venv" ]]; then mv "$APP/.venv" "$BACKUP/.venv" || true; fi
    if [[ -d "$APP" ]]; then mv "$APP" "${STAGING}-failed" || true; fi
    if [[ -d "$BACKUP" ]]; then mv "$BACKUP" "$APP" || true; fi
    systemctl --user start hue-lab.service || true
  fi
  exit "$code"
}
trap rollback ERR
systemctl --user stop hue-lab.service
mv "$APP" "$BACKUP"
switched=1
mv "$STAGING" "$APP"
mv "$BACKUP/.venv" "$APP/.venv"
for name in .hue_config.json hue_settings.json; do
  if [[ -f "$BACKUP/$name" ]]; then cp -p "$BACKUP/$name" "$APP/$name"; fi
done
if [[ -d "$BACKUP/logs" ]]; then cp -a "$BACKUP/logs" "$APP/logs"; fi
# Tous les autres fichiers restent disponibles dans le dossier de sauvegarde.

printf '4/5 — Réactivation du service Hue...\n'
systemctl --user daemon-reload
systemctl --user start hue-lab.service
APP="$APP" "$APP/.venv/bin/python" - <<'PY'
import json, time, urllib.request
for i in range(30):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/state', timeout=3) as r:
            if r.status == 200 and 'lights' in json.load(r):
                break
    except (OSError, ValueError):
        pass
    time.sleep(2)
else:
    raise RuntimeError('Le nouveau serveur ne répond pas : migration annulée.')
PY

printf '5/5 — Activation des vérifications horaires GitHub...\n'
systemctl --user enable --now hue-lab-update-check.timer
trap - ERR
printf '\nSUCCÈS : Hue Lab v0.4 est installé.\n'
printf 'Interface : http://10.0.0.12:8765/\n'
printf 'Sauvegarde du code et des réglages conservée ici : %s\n' "$BACKUP"
printf 'Tu peux désormais installer les prochaines versions depuis l’interface.\n'
