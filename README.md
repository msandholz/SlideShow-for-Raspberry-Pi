````markdown
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
USER_NAME="pi"
DISPLAY_ID=":0"
XAUTH="/home/pi/.Xauthority"

# laufende Diashow beenden
pkill -u "$USER_NAME" feh 2>/dev/null

# vorheriges Medium aushängen
umount "$MOUNTPOINT" 2>/dev/null

# USB-Stick mounten
mount "$DEVICE" "$MOUNTPOINT" || exit 1

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
USER_NAME="markus"
XAUTH="/home/markus/.Xauthority"
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

[Service]
Type=oneshot
ExecStart=/usr/local/bin/usb-slideshow.sh /dev/%i
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
````
