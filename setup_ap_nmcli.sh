#!/usr/bin/env bash
set -euo pipefail

# Erstellt einen WLAN-Access-Point per NetworkManager/nmcli.
# Die SSID ist automatisch der Hostname des Raspberry Pi.
#
# Aufruf:
#   sudo ./setup_ap_nmcli.sh "deinWlanPasswort"
#
# Hinweis: WPA-Passwoerter muessen mindestens 8 Zeichen lang sein.

PASSWORD="${1:-}"
SSID="$(hostname)"
IFACE="${WIFI_IFACE:-wlan0}"
CON_NAME="${AP_CON_NAME:-slideshow-ap}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Bitte mit sudo starten: sudo ./setup_ap_nmcli.sh \"deinWlanPasswort\""
  exit 1
fi

if [ -z "${PASSWORD}" ] || [ "${#PASSWORD}" -lt 8 ]; then
  echo "Bitte ein WLAN-Passwort mit mindestens 8 Zeichen angeben."
  exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
  echo "nmcli nicht gefunden. Bitte NetworkManager installieren/aktivieren."
  exit 1
fi

nmcli connection delete "${CON_NAME}" >/dev/null 2>&1 || true

nmcli connection add \
  type wifi \
  ifname "${IFACE}" \
  con-name "${CON_NAME}" \
  autoconnect yes \
  ssid "${SSID}"

nmcli connection modify "${CON_NAME}" \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  ipv4.method shared \
  ipv6.method disabled \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "${PASSWORD}"

nmcli connection up "${CON_NAME}"

echo
echo "Access Point aktiv."
echo "SSID: ${SSID}"
echo "Interface: ${IFACE}"
echo "Webapp nach Installation: http://${SSID}.local:8080/ oder http://10.42.0.1:8080/"
