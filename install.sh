#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${SLIDESHOW_BASE_DIR:-/opt/sildeshow}"
APP_DIR="${BASE_DIR}/webapp"
SERVICE_USER="${SLIDESHOW_USER:-slideshow}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte mit sudo starten: sudo ./install.sh"
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip rsync

if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --user-group --home "${BASE_DIR}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

mkdir -p "${BASE_DIR}/pics" "${BASE_DIR}/sponsors" "${BASE_DIR}/logs" "${APP_DIR}"

# Projektdateien kopieren. install.sh liegt im Projektordner.
rsync -a --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude "venv" \
  ./ "${APP_DIR}/"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip wheel
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

cp "${APP_DIR}/systemd/slideshow-web.service" /etc/systemd/system/slideshow-web.service
sed -i \
  -e "s|__USER__|${SERVICE_USER}|g" \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__BASE_DIR__|${BASE_DIR}|g" \
  /etc/systemd/system/slideshow-web.service

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${BASE_DIR}"

systemctl daemon-reload
systemctl enable slideshow-web.service
systemctl restart slideshow-web.service

echo
echo "Fertig."
echo "Weboberflaeche: http://$(hostname).local:8080/"
echo "Oder im AP-Netz: http://<IP-des-Raspberry>:8080/"
echo "Status: sudo systemctl status slideshow-web.service"
