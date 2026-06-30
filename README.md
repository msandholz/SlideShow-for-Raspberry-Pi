# Slideshow Webapp fuer Raspberry Pi

Diese Webanwendung stellt eine lokale Konfigurationsoberflaeche fuer eine
Raspberry-Pi-Slideshow bereit.

## Funktionen

- Konfiguration:
  - Anzeigedauer pro Bild
  - Werbung ein/aus
  - Werbung jedes x-te Bild
- Upload normaler Bilder nach `/opt/sildeshow/pics`
- Upload von Werbebildern nach `/opt/sildeshow/sponsors`
- Import vom lokal gemounteten USB-Stick:
  - normale Bilder aus `/mnt/slideshow/pics`
  - Werbebilder aus `/mnt/slideshow/sponsors`
- Automatisches Zuschneiden/Skalieren jedes Uploads auf `1920 x 1080`
- Live-Loganzeige mit automatischem Refresh alle 2 Sekunden
- JSON-API fuer das Slideshow-Programm: `/api/config`
- Optionales AP-Setup: WLAN-SSID entspricht dem Hostnamen

> Der Pfad `/opt/sildeshow` ist absichtlich so gesetzt, weil er in der
> Anforderung so geschrieben wurde. Falls du eigentlich `/opt/slideshow`
> verwendest, installiere mit:
>
> `sudo SLIDESHOW_BASE_DIR=/opt/slideshow ./install.sh`

## Installation

Auf dem Raspberry Pi:

```bash
cd slideshow_webapp
chmod +x install.sh scripts/setup_ap_nmcli.sh
sudo ./install.sh
```

Danach:

```bash
sudo systemctl status slideshow-web.service
```

Weboberflaeche:

```text
http://<hostname>.local:8080/
http://<ip-des-raspberry>:8080/
```

## AP-Modus einrichten

Wenn Raspberry Pi OS mit NetworkManager laeuft:

```bash
sudo ./scripts/setup_ap_nmcli.sh "mindestens8zeichen"
```

Die SSID ist automatisch der aktuelle Hostname:

```bash
hostname
```

Hostname aendern:

```bash
sudo raspi-config
```

Danach neu starten.

## Verzeichnisstruktur

```text
/opt/sildeshow/
  config.json
  pics/
  sponsors/
  logs/
    webapp.log
  webapp/
```

## Konfigurationsdatei

Beispiel `/opt/sildeshow/config.json`:

```json
{
  "display_seconds": 10,
  "ads_enabled": false,
  "sponsor_every_n": 5,
  "image_width": 1920,
  "image_height": 1080,
  "updated_at": "2026-06-30T12:00:00"
}
```

## API

Konfiguration lesen:

```bash
curl http://127.0.0.1:8080/api/config
```

Status lesen:

```bash
curl http://127.0.0.1:8080/api/status
```

Logs lesen:

```bash
curl http://127.0.0.1:8080/api/logs
```

## Hinweise fuer dein Slideshow-Programm

Dein Anzeigeprogramm kann entweder die JSON-Datei lesen:

```text
/opt/sildeshow/config.json
```

oder die Web-API:

```text
http://127.0.0.1:8080/api/config
```

Die Bilder liegen nach dem Upload oder USB-Import bereits korrekt als Full-HD-JPEGs vor:

```text
/opt/sildeshow/pics/*.jpg
/opt/sildeshow/sponsors/*.jpg
```

## Rechte

Der Installer erstellt einen Systembenutzer `slideshow` und macht ihn zum
Besitzer von `/opt/sildeshow`. Dadurch darf die Webapp Uploads speichern und
Logs schreiben, ohne als root zu laufen.


## USB-Import

Standardpfade:

```text
/mnt/slideshow/pics
/mnt/slideshow/sponsors
```

Andere USB-Pfade sind per Environment-Variable moeglich, z. B. in der
systemd-Datei:

```ini
Environment=SLIDESHOW_USB_DIR=/mnt/slideshow
Environment=SLIDESHOW_USB_PICS_DIR=/mnt/slideshow/meine-bilder
Environment=SLIDESHOW_USB_SPONSORS_DIR=/mnt/slideshow/werbung
```
