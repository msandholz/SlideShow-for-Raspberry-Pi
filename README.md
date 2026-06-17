# Raspberry Pi 3B USB Slideshow Viewer

## Ziel

Ein Raspberry Pi 3B mit Raspberry Pi OS Bookworm soll automatisch Bilder von einem USB-Stick als Slideshow anzeigen.

### Anforderungen

* WLAN-Verbindung zur SSID `WLAN`
* Hostname `SlideShow`
* Erreichbarkeit per mDNS unter `SlideShow.local`
* Automatische Bildanzeige von USB-Sticks
* Unterstützung der gängigsten Bildformate
* Anzeige eines Standardbildes wenn:

  * kein USB-Stick vorhanden ist
  * keine Bilder auf dem USB-Stick gefunden werden
* Automatische Reaktion auf Einstecken und Entfernen von USB-Sticks

---

# 1. System aktualisieren

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

---

# 2. WLAN konfigurieren

Verbindung mit der SSID `WLAN` herstellen:

```bash
sudo nmcli dev wifi connect "WLAN" password "DEIN_PASSWORT"
```

Verbindung prüfen:

```bash
nmcli connection show
ip addr show wlan0
```

---

# 3. Hostname konfigurieren

Hostname setzen:

```bash
sudo hostnamectl set-hostname SlideShow
```

Neustart durchführen:

```bash
sudo reboot
```

---

# 4. mDNS (Avahi) installieren

Installation:

```bash
sudo apt install -y avahi-daemon avahi-utils
```

Dienst aktivieren:

```bash
sudo systemctl enable --now avahi-daemon
```

Status prüfen:

```bash
systemctl status avahi-daemon
```

Danach sollte der Raspberry Pi erreichbar sein über:

```text
SlideShow.local
```

Test:

```bash
ping SlideShow.local
```

---

# 5. Benötigte Pakete installieren

```bash
sudo apt install -y \
    feh \
    udisks2 \
    imagemagick \
    rsync \
    x11-xserver-utils
```

---

# 6. Automatischen Desktop-Login aktivieren

```bash
sudo raspi-config
```

Menü:

```text
System Options
 └── Boot / Auto Login
      └── Desktop Autologin
```

Anschließend neu starten:

```bash
sudo reboot
```

---

# 7. Verzeichnisstruktur anlegen

```bash
mkdir -p /home/admin/slideshow
mkdir -p /home/admin/slideshow/runtime
```

Besitzer setzen:

```bash
sudo chown -R admin:admin /home/admin/slideshow
```

---

# 8. Standardbild erstellen

```bash
convert \
  -size 1920x1080 \
  xc:black \
  -fill white \
  -gravity center \
  -pointsize 60 \
  -annotate 0 "Keine Bilder gefunden" \
  /home/admin/slideshow/default.jpg
```

---

# 9. Slideshow-Skript erstellen

Datei anlegen:

```bash
nano /home/admin/slideshow/slideshow.sh
```

Inhalt:

```bash
#!/usr/bin/env bash

set -euo pipefail

DEFAULT_IMAGE="/home/admin/slideshow/default.jpg"
WORKDIR="/home/admin/slideshow/runtime"
LISTFILE="$WORKDIR/images.txt"
PIDFILE="$WORKDIR/feh.pid"

INTERVAL_SECONDS=10

mkdir -p "$WORKDIR"

start_feh() {

    if [[ -f "$PIDFILE" ]]; then
        OLD_PID=$(cat "$PIDFILE")

        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID"
            sleep 1
        fi
    fi

    feh \
        --fullscreen \
        --hide-pointer \
        --borderless \
        --auto-zoom \
        --slideshow-delay "$INTERVAL_SECONDS" \
        --filelist "$1" &

    echo $! > "$PIDFILE"
}

while true
do

    TMPFILE="$WORKDIR/images.new"
    > "$TMPFILE"

    for ROOT in /media/admin /run/media/admin
    do
        if [[ -d "$ROOT" ]]; then

            find "$ROOT" -type f \
            \( \
                -iname "*.jpg" -o \
                -iname "*.jpeg" -o \
                -iname "*.png" -o \
                -iname "*.gif" -o \
                -iname "*.bmp" -o \
                -iname "*.webp" -o \
                -iname "*.tif" -o \
                -iname "*.tiff" \
            \) \
            >> "$TMPFILE" 2>/dev/null
        fi
    done

    if [[ ! -s "$TMPFILE" ]]; then
        echo "$DEFAULT_IMAGE" > "$TMPFILE"
    fi

    NEW_HASH=$(sha256sum "$TMPFILE" | awk '{print $1}')

    if [[ "${LAST_HASH:-}" != "$NEW_HASH" ]]; then

        mv "$TMPFILE" "$LISTFILE"

        start_feh "$LISTFILE"

        LAST_HASH="$NEW_HASH"

    else
        rm -f "$TMPFILE"
    fi

    sleep 3

done
```

Datei ausführbar machen:

```bash
chmod +x /home/admin/slideshow/slideshow.sh
```

---

# 10. systemd User Service erstellen

Verzeichnis erstellen:

```bash
mkdir -p /home/admin/.config/systemd/user
```

Service-Datei anlegen:

```bash
nano /home/admin/.config/systemd/user/slideshow.service
```

Inhalt:

```ini
[Unit]
Description=USB Slideshow Viewer
After=graphical-session.target

[Service]
Type=simple
ExecStart=/home/admin/slideshow/slideshow.sh
Restart=always
RestartSec=3
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

Aktivieren:

```bash
systemctl --user daemon-reload
systemctl --user enable slideshow.service
systemctl --user start slideshow.service
```

Linger aktivieren:

```bash
sudo loginctl enable-linger admin
```

---

# 11. Bildschirmabschaltung deaktivieren

Verzeichnis anlegen:

```bash
mkdir -p /home/admin/.config/lxsession/LXDE-pi
```

Datei erstellen:

```bash
nano /home/admin/.config/lxsession/LXDE-pi/autostart
```

Inhalt:

```text
@xset s off
@xset -dpms
@xset s noblank
```

---

# 12. Neustart

```bash
sudo reboot
```

---

# 13. Funktionstest

## Test 1

System ohne USB-Stick starten.

**Erwartung:**

* Standardbild wird angezeigt.

---

## Test 2

USB-Stick mit Bildern einstecken.

**Erwartung:**

* Slideshow startet automatisch.

---

## Test 3

USB-Stick entfernen.

**Erwartung:**

* Nach wenigen Sekunden wird wieder das Standardbild angezeigt.

---

## Test 4

USB-Stick ohne Bilder einstecken.

**Erwartung:**

* Standardbild bleibt sichtbar.

---

# 14. Unterstützte Bildformate

```text
jpg
jpeg
png
gif
bmp
webp
tif
tiff
```

---

# 15. Service überwachen

Status:

```bash
systemctl --user status slideshow.service
```

Logs:

```bash
journalctl --user -u slideshow.service -f
```

---

# 16. Fehleranalyse

## USB-Stick erkannt?

```bash
lsblk
```

```bash
mount | grep media
```

---

## mDNS prüfen

```bash
systemctl status avahi-daemon
```

```bash
avahi-resolve-host-name SlideShow.local
```

---

## Slideshow prüfen

```bash
journalctl --user -u slideshow.service -n 100
```

```bash
cat /home/admin/slideshow/runtime/images.txt
```

---

# Ergebnis

Nach Abschluss der Installation erfüllt das System folgende Anforderungen:

✅ Verbindung zum WLAN `WLAN`

✅ Hostname `SlideShow`

✅ Erreichbar über `SlideShow.local`

✅ Automatische Bildersuche auf USB-Sticks

✅ Anzeige von JPG, PNG, GIF, BMP, WEBP und TIFF

✅ Standardbild bei fehlendem USB-Stick

✅ Standardbild bei fehlenden Bildern

✅ Automatische Umschaltung beim Einstecken oder Entfernen eines USB-Sticks


=====================

# Raspberry Pi USB-Bilderrahmen mit automatischer Diashow

## Ziel

Diese Anleitung beschreibt, wie ein Raspberry Pi automatisch:

1. eingesteckte USB-Sticks erkennt,
2. diese mountet,
3. Bilddateien auf dem Stick sucht,
4. eine laufende Diashow beendet,
5. automatisch eine neue Diashow mit den Bildern des eingesteckten Sticks startet.

Die Lösung basiert auf:

- udev (USB-Erkennung)
- systemd (Service-Management)
- feh (Bildbetrachter und Diashow)

---

# Voraussetzungen

## Unterstützte Dateisysteme

Die Anleitung unterstützt:

- FAT32
- exFAT
- NTFS

## Pakete installieren

```bash
sudo apt update
sudo apt install feh exfatprogs ntfs-3g
```

---

# Mount-Verzeichnis anlegen

```bash
sudo mkdir -p /media/slideshow
sudo chmod 755 /media/slideshow
```

---

# Slideshow-Skript erstellen

Datei anlegen:

```bash
sudo nano /usr/local/bin/usb-slideshow.sh
```

Inhalt:

```bash
#!/bin/bash

DEVICE="$1"
MOUNTPOINT="/media/slideshow"
USER_NAME="admin"
DISPLAY_ID=":0"
XAUTH="/home/admin/.Xauthority"

# laufende Diashow beenden
pkill -u "$USER_NAME" feh 2>/dev/null

# vorheriges Medium aushängen
sudo umount "$MOUNTPOINT" 2>/dev/null

# USB-Stick mounten
sudo mount "$DEVICE" "$MOUNTPOINT" || exit 1

sleep 1

IMAGE_LIST="/tmp/slideshow-images.txt"

# Nur Grafikdateien sammeln
find "$MOUNTPOINT" -type f \( \
  -iname "*.jpg" -o \
  -iname "*.jpeg" -o \
  -iname "*.png" -o \
  -iname "*.gif" -o \
  -iname "*.bmp" -o \
  -iname "*.webp" \
\) > "$IMAGE_LIST"

# Diashow starten, wenn Bilder vorhanden sind
if [ -s "$IMAGE_LIST" ]; then
  sudo -u "$USER_NAME" DISPLAY="$DISPLAY_ID" XAUTHORITY="$XAUTH" \
    feh --fullscreen \
        --hide-pointer \
        --auto-zoom \
        --slideshow-delay 5 \
        --randomize \
        --filelist "$IMAGE_LIST" &
fi
```

Datei speichern und ausführbar machen:

```bash
sudo chmod +x /usr/local/bin/usb-slideshow.sh
```

---

## Benutzername anpassen

Standardmäßig wird der Benutzer `pi` verwendet.

Falls ein anderer Benutzer verwendet wird:

```bash
USER_NAME="pi"
XAUTH="/home/pi/.Xauthority"
```

anpassen, z.B.:

```bash
USER_NAME="admin"
XAUTH="/home/admin/.Xauthority"
```

---

# systemd-Service erstellen

Datei anlegen:

```bash
sudo nano /etc/systemd/system/usb-slideshow@.service
```

Inhalt:

```ini
[Unit]
Description=USB Slideshow for %i
After=graphical.target
Requires=graphical.target

[Service]
Type=simple
User=admin
Group=admin
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
Environment=XDG_RUNTIME_DIR=/run/user/1000
ExecStart=/usr/local/bin/usb-slideshow.sh /dev/%i
KillMode=process

[Install]
WantedBy=graphical.target

```

Systemd neu laden:

```bash
sudo systemctl daemon-reload
```

---

# udev-Regel erstellen

Datei anlegen:

```bash
sudo nano /etc/udev/rules.d/99-usb-slideshow.rules
```

Inhalt:

```udev
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{DEVTYPE}=="partition", TAG+="systemd", ENV{SYSTEMD_WANTS}="usb-slideshow@%k.service"
```

Regeln neu laden:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

---

# Energiesparfunktionen deaktivieren

Damit der Bildschirm dauerhaft eingeschaltet bleibt:

```bash
mkdir -p ~/.config/lxsession/LXDE-pi
nano ~/.config/lxsession/LXDE-pi/autostart
```

Folgende Zeilen eintragen:

```text
@xset s off
@xset -dpms
@xset s noblank
```

---

# Funktionsweise

## USB-Stick einstecken

1. udev erkennt den neuen USB-Stick.
2. systemd startet den Service.
3. Das Skript mountet den Stick.
4. Alle Bilddateien werden gesucht.
5. Eine vorhandene Diashow wird beendet.
6. feh startet mit den neuen Bildern.

---

# Unterstützte Bildformate

Folgende Dateitypen werden berücksichtigt:

| Format | Endung |
|----------|----------|
| JPEG | .jpg, .jpeg |
| PNG | .png |
| GIF | .gif |
| BMP | .bmp |
| WEBP | .webp |

Andere Dateien werden ignoriert.

---

# Testen

## Manuelle Ausführung

Beispiel:

```bash
sudo /usr/local/bin/usb-slideshow.sh /dev/sda1
```

---

## Service prüfen

```bash
systemctl status "usb-slideshow@*.service"
```

---

## Log-Ausgabe prüfen

```bash
journalctl -u usb-slideshow@sda1.service
```

---

# Erweiterungsmöglichkeiten

## Diashow-Geschwindigkeit ändern

Im Skript:

```bash
--slideshow-delay 5
```

ändern, z.B.:

```bash
--slideshow-delay 10
```

für 10 Sekunden pro Bild.

---

## Zufallsreihenfolge deaktivieren

Entfernen:

```bash
--randomize
```

---

## Rekursive Bildsuche

Die aktuelle Lösung durchsucht automatisch alle Unterordner des USB-Sticks.

Beispiel:

```text
USB-Stick
├── Urlaub
│   ├── Bild1.jpg
│   └── Bild2.jpg
└── Familie
    └── Bild3.png
```

Alle Bilder werden automatisch gefunden.

---

# Fehlerbehebung

## USB-Stick wird nicht erkannt

Gerät prüfen:

```bash
lsblk
```

udev-Ereignisse anzeigen:

```bash
udevadm monitor
```

---

## feh startet nicht

Display prüfen:

```bash
echo $DISPLAY
```

Typischer Wert:

```text
:0
```

---

## Keine Bilder gefunden

Prüfen:

```bash
find /media/slideshow -type f
```

---

# Lizenz

Diese Anleitung darf frei verwendet, angepasst und erweitert werden.
