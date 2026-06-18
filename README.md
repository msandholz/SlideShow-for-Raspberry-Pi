# Raspberry Pi 3B Slideshow-Kiosk mit USB-Stick

## Ziel

Ein Raspberry Pi 3B mit Raspberry Pi OS Bookworm soll als robuster Slideshow-Viewer betrieben werden.

### Anforderungen

* Automatische WLAN-Verbindung zur SSID `WLAN`
* mDNS-Auflösung über `SlideShow.local`
* Automatische Anzeige von Bildern eines USB-Sticks
* Anzeige eines Standardbildes, wenn:

  * kein USB-Stick vorhanden ist
  * keine Bilder auf dem USB-Stick vorhanden sind
* Automatische Reaktion auf Einstecken und Entfernen von USB-Sticks
* Kiosk-Modus ohne Desktop-Bedienung
* Logging zur Fehleranalyse

---

## 1. System aktualisieren und konfigurieren
### 1.1 System akutalisieren
```bash
sudo apt update
sudo apt -y full-upgrade
sudo reboot
```

### 1.2 Hostname und mDNS konfigurieren
Hostname setzen:
```bash
sudo hostnamectl set-hostname SlideShow
```

Avahi installieren:
```bash
sudo apt install -y avahi-daemon && sudo systemctl enable --now avahi-daemon
```

Neustart:
```bash
sudo reboot
```

Danach sollte der Raspberry Pi erreichbar sein über:
```text
SlideShow.local
```


### 1.3 Benötigte Software installieren

```bash
sudo apt install -y \
    feh \
    xorg \
    xinit \
    openbox \
    unclutter \
    imagemagick \
    python3 \
    python3-pip \
    udisks2 \
    exfatprogs
```

### 1.4 WLAN konfigurieren

SSID: `WLAN`

```bash
sudo nmcli dev wifi connect "WLAN" password "DEIN_PASSWORT"
```

Verbindung prüfen:

```bash
nmcli connection show
ip a
```

---
## 2. Verzeichnisstruktur anlegen
Für die SildeShow sollte folgende Struktur vorhanden sein bzw. hergestellt werden.
```bash
Executeable Files:
/opt/slideshow/
├── default.jpg
├── default1.jpg
├── test-default-jpg.py
├── mount-usb.sh
└── slideshow.py

Log Files:
/var/log/slideshow/
├── slideshow.log
└── mount-usb.log

Pictures:
/data/slideshow/
├── sda1/
├── sdb1/
└── sdc1/

Systemd Services:
/etc/systemd/system/
├── mount-usb.service
└── slideshow.service

udev Rules:
/etc/udev/rules.d/
└── 99-slideshow-usb.rules
```

### 2.1 Ordner anlegen

- für die Executeables
```bash
sudo mkdir -p /opt/slideshow && sudo chown -R admin:admin /opt/slideshow
```

- für Log-Files
```bash
sudo mkdir -p /var/log/slideshow && sudo chown -R admin:admin /var/log/slideshow
```
- als Quelle für die Bilder
```bash
sudo mkdir -p /data/slideshow && sudo chown admin:admin /data/slideshow && sudo chmod 755 /data/slideshow
```

---
## 3. Local image "default.jpg" generieren/laden und testen
- Standardbild "default.jpg" von GitHub ins Verzeichnis "/opt/slideshow/" laden
```bash
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/default.jpg -o /opt/slideshow/default.jpg
```

- Testscript laden
```bash
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/test-default-jpg.py -o /opt/slideshow/test-default-jpg.py
```

- Standardbild testen
```bash
python3 /opt/slideshow/test-default-jpg.py
```

### 3.1  Alternativ: Standardbild "default.jpg" generieren
```bash
convert \
  -size 1920x1080 \
  xc:black \
  -gravity center \
  -fill white \
  -pointsize 60 \
  -annotate 0 "Please insert USB-Stick!" \
  /opt/slideshow/default.jpg
```

### 3.2  Alternativ: Python Script "test-default-jpg.py" manuell anlegen
```bash
sudo nano /opt/slideshow/test-default-jpg.py
```
Inhalt:
```bash
#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path

IMAGE = "/opt/slideshow/default.jpg"

print(f"DISPLAY={os.environ.get('DISPLAY')}")
print(f"XAUTHORITY={os.environ.get('XAUTHORITY')}")

if not Path(IMAGE).exists():
    print(f"Datei nicht gefunden: {IMAGE}")
    exit(1)

subprocess.run([
    "feh",
    "--fullscreen",
    "--auto-zoom",
    IMAGE
])
```

---

## 4. Mounting USB-Stick
Für das automatiche mounten des USB-Sticks sind folgende Teile anzulegen bzw. zu konfigurieren:

- Script "mount-usb.sh" herunterladen 
```bash
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/mount-usb.sh -o /opt/slideshow/mount-usb.sh
```
```bash
sudo chmod +x /opt/slideshow/mount-usb.sh
```

- systemd-Service "mount-usb.service" herunterladen
```bash
sudo curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/mount-usb.service -o /etc/systemd/system/mount-usb.service
```

- systemd-service "mount-usb.service" starten
```bash
sudo systemctl daemon-reload && sudo systemctl enable mount-usb.service
sudo systemctl status mount-usb.service
```

- udev-Regel "99-slideshow-usb.rules" anlegen 
```bash
sudo nano /etc/udev/rules.d/99-slideshow-usb.rules
```
Inhalt:
```bash
ACTION=="add", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", ENV{DEVICETYPE}="partition", RUN+="/bin/systemctl start mount-usb.service"
ACTION=="remove", SUBSYSTEM=="block", ENV{ID_BUS}=="usb", RUN+="/bin/umount -l /data/slideshow" 

```
- Laden: 
```bash
sudo udevadm control --reload
sudo udevadm trigger
```
- Testen:
```bash
findmnt /data/slideshow
ls -la /data/slideshow
sudo -u admin python3 -c 'import os; print(os.listdir("/data/slideshow"))'
tail -f /var/log/slideshow/mount-usb.log
```
Wichtig: Bei FAT/exFAT/NTFS erzwingen die Mount-Optionen uid=admin,gid=admin passende Rechte. Bei ext4-Sticks kommen die Rechte aus dem Dateisystem selbst; falls Python als admin nichts lesen kann, einmalig auf dem Stick ausführen:
```bash
sudo chown -R admin:admin /data/slideshow
```


### 4.1 Alternativ: Script "mount-usb.sh" manuell anlegen  
Datei anlegen:
```bash
sudo nano /opt/slideshow/mount-usb.sh
```
Inhalt:
```bash
#!/bin/bash

MOUNTPOINT="/data/slideshow"
LOG="/var/log/slideshow/mount-usb.log"

mkdir -p "$MOUNTPOINT"

echo "===== $(date) USB Mount Start =====" >> "$LOG"

# alle möglichen USB-Partitionen durchgehen
for DEV in /dev/sd[a-z][0-9]; do

    [ -b "$DEV" ] || continue

    echo "Prüfe: $DEV" >> "$LOG"

    # prüfen ob Dateisystem existiert
    FSTYPE=$(blkid -o value -s TYPE "$DEV" 2>/dev/null)

    if [ -z "$FSTYPE" ]; then
        echo "Kein Dateisystem auf $DEV -> skip" >> "$LOG"
        continue
    fi

    echo "FS: $DEV = $FSTYPE" >> "$LOG"

    # mountpoint sauber machen
    umount "$MOUNTPOINT" 2>/dev/null

    # Mount versuchen (auto erkennt exfat/ntfs/vfat/ext4)
    if  mount -t auto "$DEV" "$MOUNTPOINT" >> "$LOG" 2>&1; then
        echo "SUCCESS: $DEV gemountet auf $MOUNTPOINT" >> "$LOG"
        exit 0
    else
        echo "FAIL: $DEV konnte nicht gemountet werden" >> "$LOG"
    fi

done

echo "KEIN gültiger USB-Stick gefunden" >> "$LOG"
exit 1
```

### 4.2 Alternativ: Dienst "mount-usb.service" manuell anlegen  
Datei anlegen:
```bash
sudo nano /etc/systemd/system/mount-usb.service
```
Inhalt:
```INI
[Unit]
Description=Mount USB Stick
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/opt/slideshow/mount-usb.sh

[Install]
WantedBy=multi-user.target
```


---

## 5. Slideshow Anwendung

- Python Script "slideshow.py" herunterladen 
```bash
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/slideshow.py -o /opt/slideshow/slideshow.py
```
- Datei ausführbar machen:
```bash
chmod +x /opt/slideshow/slideshow.py
```

- Start-Script "slideshow.sh" herunterladen 
```bash
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/slideshow.sh -o /opt/slideshow/slideshow.sh
```
- Datei ausführbar machen:
```bash
chmod +x /opt/slideshow/slideshow.sh
```

- systemd-Service "slideshow.service" herunterladen
```bash
sudo curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/slideshow.service -o /etc/systemd/system/slideshow.service
```
- systemd-service "slideshow.service" starten
```bash
sudo systemctl daemon-reload && sudo systemctl enable slideshow.service
```

### 5.1 Alternativ: Datei "slideshow.py" manuell anlegen
Datei anlegen:
```bash
sudo nano /opt/slideshow/slideshow.py
```
Inhalt:
```python

import os
import time
import pygame

USB_PATH = "/data/slideshow"
DEFAULT_IMAGE = "/opt/slideshow/default.jpg"
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

SLIDE_TIME = 5  # Sekunden

def find_images():
    """Findet Bilder auf USB-Stick oder gibt leere Liste zurück."""
    if not os.path.exists(USB_PATH):
        return []

    files = [
        os.path.join(USB_PATH, f)
        for f in os.listdir(USB_PATH)
        if f.lower().endswith(SUPPORTED_EXT)
    ]

    return sorted(files)


def load_image(path, screen_size):
    """Lädt Bild, skaliert es proportional und zentriert es (kein Verzerren)."""

    img = pygame.image.load(path)

    screen_w, screen_h = screen_size
    img_w, img_h = img.get_size()

    # Skalierungsfaktor berechnen (Aspect Ratio erhalten)
    scale = min(screen_w / img_w, screen_h / img_h)

    new_size = (int(img_w * scale), int(img_h * scale))

    img = pygame.transform.smoothscale(img, new_size)

    # schwarzes Hintergrundbild erzeugen
    surface = pygame.Surface(screen_size)
    surface.fill((0, 0, 0))

    # zentrieren
    x = (screen_w - new_size[0]) // 2
    y = (screen_h - new_size[1]) // 2

    surface.blit(img, (x, y))

    return surface

def main():
    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
    pygame.init()
    pygame.display.set_caption("Slideshow")

     # 👉 Cursor ausblenden
    pygame.mouse.set_visible(False)

    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    screen_size = screen.get_size()

    clock = pygame.time.Clock()

    current_images = []
    index = 0
    last_switch = time.time()

    while True:
        # Exit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

        images = find_images()

        # Wenn neue Bilder vorhanden oder Liste leer geworden ist
        if images != current_images:
            current_images = images
            index = 0
            last_switch = time.time()

        # Auswahl Bild
        if len(current_images) == 0:
            path = DEFAULT_IMAGE
        else:
            path = current_images[index]

        # Bild laden & anzeigen
        try:
            img = load_image(path, screen_size)
            screen.blit(img, (0, 0))
        except Exception as e:
            print(f"Fehler beim Laden: {path} -> {e}")

        pygame.display.flip()

        # Bildwechsel nur wenn mehrere Bilder vorhanden
        if len(current_images) > 1 and time.time() - last_switch > SLIDE_TIME:
            index = (index + 1) % len(current_images)
            last_switch = time.time()

        clock.tick(30)


if __name__ == "__main__":
    main()

```

Datei ausführbar machen:
```bash
chmod +x /opt/slideshow/slideshow.py
```

### 5.2 Alternativ: Systemd-Service "slideshow.service" manuell erstellen
Datei anlegen:
```bash
sudo nano /etc/systemd/system/slideshow.service
```

Inhalt:
```ini
[Unit]
Description=USB Slideshow
After=display-manager.service
Wants=display-manager.service

[Service]
User=admin
WorkingDirectory=/opt/slideshow

Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/admin/.Xauthority

ExecStart=/usr/bin/python3 /opt/slideshow/slideshow.py

Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```


Aktivieren:

```bash
sudo systemctl daemon-reload
sudo systemctl enable slideshow.service
sudo systemctl start slideshow.service
```

---

# 10. Bildschirm-Standby deaktivieren

```bash
sudo raspi-config
```

Menü:
```text
Display Options
 → Screen Blanking
   → Disable
```

---

# 11. Neustart

```bash
sudo reboot
```

---

# 12. Logging

Anwendungslog:

```bash
tail -f /var/log/slideshow/slideshow.log
```

Service-Log:
```bash
journalctl -u slideshow.service -f
```

Status:
```bash
systemctl status slideshow.service
```

---

# 13. Unterstützte Bildformate

Die Anwendung sucht rekursiv nach:

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

Unterordner werden automatisch durchsucht.

---

# 14. Verhalten

| Ereignis                        | Verhalten                         |
| ------------------------------- | --------------------------------- |
| Raspberry startet mit USB-Stick | Bilder werden angezeigt           |
| USB-Stick enthält keine Bilder  | Standardbild                      |
| USB-Stick wird entfernt         | Standardbild                      |
| USB-Stick wird eingesteckt      | Bilder werden automatisch erkannt |
| Bilder werden ergänzt           | Slideshow wird neu geladen        |
| Fehler                          | Eintrag im Logfile                |

---

# 15. Wartung

Service neu starten:
```bash
sudo systemctl restart slideshow.service
```

Service stoppen:
```bash
sudo systemctl stop slideshow.service
```

Service deaktivieren:
```bash
sudo systemctl disable slideshow.service
```

Logfile leeren:
```bash
sudo truncate -s 0 /var/log/slideshow/slideshow.log
```

---

# Ergebnis

Nach dem Einschalten startet der Raspberry Pi automatisch in den Kiosk-Modus und zeigt:

* Bilder vom USB-Stick
* automatisch aktualisierte Inhalte nach Einstecken/Entfernen
* Standardbild bei fehlenden Bildern
* Logfiles zur Diagnose

Der Raspberry Pi ist über mDNS erreichbar unter:

```text
SlideShow.local
```


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
