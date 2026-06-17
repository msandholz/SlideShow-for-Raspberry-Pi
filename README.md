
# Raspberry Pi Slideshow Viewer

## Ziel

Raspberry Pi 3B mit Raspberry Pi OS als automatischer Slideshow-Viewer:

* WLAN-SSID: `WLAN`
* Hostname/mDNS: `SlideShow.local`
* Benutzer: `admin`
* Bilder vom USB-Stick anzeigen
* Ohne USB-Stick oder ohne Bilder: Standardbild anzeigen
* USB-Stick kann im laufenden Betrieb gesteckt/gezogen werden
* Vollautomatischer Betrieb nach dem Einschalten

---

# 1. System aktualisieren

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

---

# 2. Hostname konfigurieren

Hostname setzen:

```bash
sudo hostnamectl set-hostname SlideShow
```

Datei prüfen:

```bash
cat /etc/hostname
```

Ausgabe:

```text
SlideShow
```

Neustart:

```bash
sudo reboot
```

Test von einem anderen Rechner:

```bash
ping SlideShow.local
```

---

# 3. WLAN konfigurieren

```bash
sudo raspi-config
```

Menü:

```text
System Options
 └── Wireless LAN
```

Eintragen:

```text
SSID: WLAN
Passphrase: <WLAN-PASSWORT>
```

Verbindung prüfen:

```bash
iwgetid
hostname -I
```

---

# 4. Benötigte Software installieren

```bash
sudo apt update
sudo apt install -y \
    feh \
    imagemagick \
    udisks2 \
    x11-xserver-utils
```

Verwendete Komponenten:

| Paket             | Zweck                  |
| ----------------- | ---------------------- |
| feh               | Bildanzeige            |
| imagemagick       | Erzeugung Standardbild |
| udisks2           | USB-Mounting           |
| x11-xserver-utils | Bildschirmsteuerung    |

---

# 5. Automatischen Login aktivieren

```bash
sudo raspi-config
```

Menü:

```text
System Options
 └── Boot / Auto Login
      └── Desktop Autologin
```

Danach:

```bash
sudo reboot
```

---

# 6. Projektverzeichnis anlegen

```bash
mkdir -p /home/admin/slideshow
mkdir -p /home/admin/slideshow/default
mkdir -p /home/admin/slideshow/runtime
```

Besitzrechte setzen:

```bash
sudo chown -R admin:admin /home/admin/slideshow
```

---

# 7. Standardbild erstellen

```bash
convert \
  -size 1920x1080 \
  xc:black \
  -fill white \
  -gravity center \
  -pointsize 60 \
  -annotate 0 "Keine Bilder gefunden" \
  /home/admin/slideshow/default/default.png
```

Alternativ kann ein eigenes Bild verwendet werden:

```bash
cp mein_bild.png /home/admin/slideshow/default/default.png
```

---

# 8. Slideshow-Skript erstellen

Datei anlegen:

```bash
nano /home/admin/slideshow/slideshow.sh
```

Inhalt:

```bash
#!/bin/bash

DEFAULT_IMAGE="/home/admin/slideshow/default/default.png"

RUNTIME_DIR="/home/admin/slideshow/runtime"

PLAYLIST="$RUNTIME_DIR/playlist.txt"
CURRENT_PLAYLIST="$RUNTIME_DIR/current_playlist.txt"

IMAGE_EXTENSIONS="jpg jpeg png gif bmp webp tif tiff"

export DISPLAY=:0

mkdir -p "$RUNTIME_DIR"

xset s off
xset -dpms
xset s noblank

mount_usb_devices() {

    lsblk -rpo NAME,TRAN,TYPE,MOUNTPOINT |

    awk '$2=="usb" && $3=="part" {print $1}' |

    while read DEV
    do
        if ! lsblk -rpo NAME,MOUNTPOINT | grep -q "^$DEV .*"
        then
            udisksctl mount -b "$DEV" >/dev/null 2>&1
        fi
    done
}

create_playlist() {

    > "$PLAYLIST"

    for BASE in \
        /media/admin \
        /run/media/admin \
        /mnt
    do

        [ -d "$BASE" ] || continue

        for EXT in $IMAGE_EXTENSIONS
        do
            find "$BASE" \
                -type f \
                -iname "*.$EXT" \
                2>/dev/null \
                >> "$PLAYLIST"
        done

    done

    sort -u "$PLAYLIST" -o "$PLAYLIST"

    if [ ! -s "$PLAYLIST" ]
    then
        echo "$DEFAULT_IMAGE" > "$PLAYLIST"
    fi
}

start_viewer() {

    pkill -x feh 2>/dev/null

    feh \
        --fullscreen \
        --auto-zoom \
        --hide-pointer \
        --slideshow-delay 8 \
        --reload 5 \
        --filelist "$CURRENT_PLAYLIST" &
}

echo "$DEFAULT_IMAGE" > "$CURRENT_PLAYLIST"

start_viewer

while true
do

    mount_usb_devices

    create_playlist

    if ! cmp -s "$PLAYLIST" "$CURRENT_PLAYLIST"
    then
        cp "$PLAYLIST" "$CURRENT_PLAYLIST"
        start_viewer
    fi

    sleep 5

done
```

Datei speichern.

Ausführbar machen:

```bash
chmod +x /home/admin/slideshow/slideshow.sh
```

---

# 9. LXDE Autostart konfigurieren

Ordner erstellen:

```bash
mkdir -p /home/admin/.config/lxsession/LXDE-pi
```

Datei anlegen:

```bash
nano /home/admin/.config/lxsession/LXDE-pi/autostart
```

Inhalt:

```text
@xset s off
@xset -dpms
@xset s noblank
@/home/admin/slideshow/slideshow.sh
```

---

# 10. Testen

Skript manuell starten:

```bash
/home/admin/slideshow/slideshow.sh
```

---

# 11. Neustart

```bash
sudo reboot
```

---

# Verhalten

## Fall 1

USB-Stick mit Bildern vorhanden:

```text
Boot
 ↓
USB erkannt
 ↓
Bilder gefunden
 ↓
Slideshow startet
```

---

## Fall 2

USB-Stick vorhanden aber keine Bilder:

```text
Boot
 ↓
USB erkannt
 ↓
Keine Bilder
 ↓
Standardbild anzeigen
```

---

## Fall 3

Kein USB-Stick vorhanden:

```text
Boot
 ↓
Kein USB-Stick
 ↓
Standardbild anzeigen
```

---

## Fall 4

USB-Stick wird gezogen:

```text
USB entfernt
 ↓
Playlist leer
 ↓
Standardbild anzeigen
```

---

## Fall 5

USB-Stick wird gesteckt:

```text
USB eingesteckt
 ↓
Automatische Erkennung
 ↓
Bildsuche
 ↓
Slideshow startet
```

---

# Unterstützte Bildformate

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

# Slideshow-Geschwindigkeit ändern

Im Skript:

```bash
--slideshow-delay 8
```

Beispiel:

```bash
--slideshow-delay 15
```

= 15 Sekunden pro Bild

---

# Fehleranalyse

## WLAN prüfen

```bash
iwgetid
ip addr
```

---

## Hostname prüfen

```bash
hostname
```

Ausgabe:

```text
SlideShow
```

---

## mDNS prüfen

Von einem anderen Rechner:

```bash
ping SlideShow.local
```

---

## USB-Stick prüfen

```bash
lsblk
```

---

## Laufende Anzeige prüfen

```bash
pgrep feh
```

---

## Slideshow stoppen

```bash
pkill feh
```

---

# Ergebnis

Nach dem Einschalten arbeitet der Raspberry Pi vollständig autonom:

* verbindet sich mit WLAN `WLAN`
* ist unter `SlideShow.local` erreichbar
* zeigt Bilder von USB-Sticks automatisch an
* zeigt bei fehlenden Bildern ein Standardbild
* reagiert automatisch auf Einstecken und Entfernen von USB-Sticks
* benötigt keine Tastatur oder Maus im Betrieb































================



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
