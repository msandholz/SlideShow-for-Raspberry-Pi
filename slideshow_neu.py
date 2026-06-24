import os
# import time  # GELÖSCHT/ERSETZT: time.time() wird durch pygame.time.get_ticks() ersetzt
import pygame

# VERBESSERT: Logging ergänzt
import logging
from logging.handlers import RotatingFileHandler


USB_PATH = "/data/slideshow"
DEFAULT_IMAGE = "/opt/slideshow/default.jpg"
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

SLIDE_TIME = 5  # Sekunden

# VERBESSERT: Zeiten in Millisekunden für pygame.time.get_ticks()
SLIDE_TIME_MS = SLIDE_TIME * 1000

# VERBESSERT: USB-Stick nicht in jedem Frame scannen
SCAN_INTERVAL_MS = 2000

# VERBESSERT: Logging-Konfiguration
LOG_DIR = "/opt/slideshow/log"
LOG_FILE = os.path.join(LOG_DIR, "slideshow.log")
LOG_MAX_BYTES = 1 * 1024 * 1024  # ca. 1 MB
LOG_BACKUP_COUNT = 1             # maximal eine alte Sicherungsdatei behalten


# VERBESSERT: zentrale Logging-Funktion
def setup_logging():
    """
    Initialisiert das Logging.

    Die Logdatei wird bei jedem Programmstart neu angelegt.
    Durch RotatingFileHandler wird verhindert, dass die Datei dauerhaft
    größer als ca. 1 MB wird.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("slideshow")
    logger.setLevel(logging.INFO)

    # VERBESSERT: doppelte Handler vermeiden, falls setup_logging mehrfach aufgerufen wird
    logger.handlers.clear()

    handler = RotatingFileHandler(
        LOG_FILE,
        mode="w",                  # VERBESSERT: Logfile bei jedem Start neu anlegen
        maxBytes=LOG_MAX_BYTES,    # VERBESSERT: maximale Dateigröße ca. 1 MB
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def find_images(logger):
    """Findet Bilder auf USB-Stick oder gibt leere Liste zurück."""
    if not os.path.exists(USB_PATH):
        logger.warning(f"USB-Pfad nicht gefunden: {USB_PATH}")
        return []

    try:
        files = [
            os.path.join(USB_PATH, f)
            for f in os.listdir(USB_PATH)
            if f.lower().endswith(SUPPORTED_EXT)
        ]
    except OSError as e:
        # print(f"Fehler beim Lesen von {USB_PATH}: {e}")  # GELÖSCHT/ERSETZT
        logger.error(f"Fehler beim Lesen von {USB_PATH}: {e}")
        return []

    return sorted(files)


def load_image(path, screen_size):
    """Lädt Bild, skaliert es proportional und zentriert es (kein Verzerren)."""

    img = pygame.image.load(path)

    # VERBESSERT: convert() beschleunigt späteres Blitting
    img = img.convert()

    screen_w, screen_h = screen_size
    img_w, img_h = img.get_size()

    # VERBESSERT: Schutz gegen defekte Bilder mit 0-Größe
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"Ungültige Bildgröße: {img_w}x{img_h}")

    # Skalierungsfaktor berechnen (Aspect Ratio erhalten)
    scale = min(screen_w / img_w, screen_h / img_h)

    new_size = (int(img_w * scale), int(img_h * scale))

    img = pygame.transform.smoothscale(img, new_size)

    # schwarzes Hintergrundbild erzeugen
    surface = pygame.Surface(screen_size)

    # VERBESSERT: convert() für schnellere Anzeige
    surface = surface.convert()

    surface.fill((0, 0, 0))

    # zentrieren
    x = (screen_w - new_size[0]) // 2
    y = (screen_h - new_size[1]) // 2

    surface.blit(img, (x, y))

    return surface


def main():
    # VERBESSERT: Logging direkt beim Start initialisieren
    logger = setup_logging()
    logger.info("Slideshow wird gestartet")

    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    try:
        pygame.init()
        pygame.display.set_caption("Slideshow")

        # 👉 Cursor ausblenden
        pygame.mouse.set_visible(False)

        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen_size = screen.get_size()

        logger.info(f"Display initialisiert: {screen_size[0]}x{screen_size[1]}")

        clock = pygame.time.Clock()

        current_images = []
        index = 0

        # last_switch = time.time()  # GELÖSCHT/ERSETZT

        # VERBESSERT: pygame-interne monotone Zeitbasis
        now = pygame.time.get_ticks()
        next_switch_time = now + SLIDE_TIME_MS
        next_scan_time = 0

        # VERBESSERT: aktuelles Bild zwischenspeichern
        current_path = None
        current_surface = None

        # VERBESSERT: Default-Bild vorladen, damit bei Fehlern etwas angezeigt wird
        try:
            default_surface = load_image(DEFAULT_IMAGE, screen_size)
            logger.info(f"Default-Bild geladen: {DEFAULT_IMAGE}")
        except Exception as e:
            # print(f"Fehler beim Laden des Default-Bildes: {DEFAULT_IMAGE} -> {e}")  # GELÖSCHT/ERSETZT
            logger.error(f"Fehler beim Laden des Default-Bildes: {DEFAULT_IMAGE} -> {e}")
            default_surface = pygame.Surface(screen_size).convert()
            default_surface.fill((0, 0, 0))

        while True:
            now = pygame.time.get_ticks()

            # Exit event
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("Slideshow wird beendet: pygame.QUIT")
                    pygame.quit()
                    return

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    logger.info("Slideshow wird beendet: ESC gedrückt")
                    pygame.quit()
                    return

            # images = find_images()  # GELÖSCHT/ERSETZT: nicht mehr in jedem Frame scannen

            # VERBESSERT: USB-Verzeichnis nur periodisch scannen
            if now >= next_scan_time:
                images = find_images(logger)
                next_scan_time = now + SCAN_INTERVAL_MS

                # Wenn neue Bilder vorhanden oder Liste leer geworden ist
                if images != current_images:
                    logger.info(
                        f"Bildliste geändert: vorher={len(current_images)}, jetzt={len(images)}"
                    )

                    current_images = images
                    index = 0

                    # last_switch = time.time()  # GELÖSCHT/ERSETZT

                    # VERBESSERT: Timer sauber neu starten
                    next_switch_time = now + SLIDE_TIME_MS

                    # VERBESSERT: erzwingt Neu-Laden des nächsten Bildes
                    current_path = None
                    current_surface = None

            # Auswahl Bild
            if len(current_images) == 0:
                path = DEFAULT_IMAGE
            else:
                # VERBESSERT: Index absichern, falls sich die Liste geändert hat
                index %= len(current_images)
                path = current_images[index]

            # Bild laden & anzeigen
            # try:
            #     img = load_image(path, screen_size)
            #     screen.blit(img, (0, 0))
            # except Exception as e:
            #     print(f"Fehler beim Laden: {path} -> {e}")
            #
            # GELÖSCHT/ERSETZT:
            # Das Bild wurde bisher in jedem Frame neu geladen.
            # Das kann bei USB-I/O oder großen Bildern zu Hängern führen.

            # VERBESSERT: Bild nur laden, wenn sich der Pfad geändert hat
            if path != current_path:
                try:
                    current_surface = load_image(path, screen_size)
                    current_path = path
                    logger.info(f"Bild geladen: {path}")
                except Exception as e:
                    # print(f"Fehler beim Laden: {path} -> {e}")  # GELÖSCHT/ERSETZT
                    logger.error(f"Fehler beim Laden: {path} -> {e}")

                    # VERBESSERT: Fehlerhaftes Bild überspringen
                    if len(current_images) > 1:
                        logger.warning(f"Fehlerhaftes Bild wird übersprungen: {path}")

                        index = (index + 1) % len(current_images)
                        current_path = None
                        current_surface = None
                        next_switch_time = now + 250
                        continue

                    # VERBESSERT: Bei keinem gültigen Bild Default anzeigen
                    current_surface = default_surface
                    current_path = DEFAULT_IMAGE
                    logger.warning("Fallback auf Default-Bild")

            # VERBESSERT: Immer nur die bereits geladene Surface anzeigen
            if current_surface is not None:
                screen.blit(current_surface, (0, 0))
            else:
                screen.blit(default_surface, (0, 0))

            pygame.display.flip()

            # Bildwechsel nur wenn mehrere Bilder vorhanden
            # if len(current_images) > 1 and time.time() - last_switch > SLIDE_TIME:
            #     index = (index + 1) % len(current_images)
            #     last_switch = time.time()
            #
            # GELÖSCHT/ERSETZT:
            # time.time() kann bei Systemzeitänderungen springen.
            # Außerdem wurde das Timing an die aktuelle Frame-Zeit gekoppelt.

            # VERBESSERT: robuster Bildwechsel mit pygame.time.get_ticks()
            if len(current_images) > 1 and now >= next_switch_time:
                index = (index + 1) % len(current_images)

                # VERBESSERT: erzwingt Laden des neuen Bildes im nächsten Loop
                current_path = None

                logger.info(f"Wechsel zu Bildindex: {index}")

                # VERBESSERT:
                # Nicht einfach "now + SLIDE_TIME_MS", sondern geplante Zeit fortschreiben.
                # Dadurch driftet die Slideshow weniger, wenn ein Frame mal länger dauert.
                next_switch_time += SLIDE_TIME_MS

                # VERBESSERT:
                # Falls das Programm länger blockiert war, nicht mehrere Bilder sofort überspringen.
                if now > next_switch_time + SLIDE_TIME_MS:
                    logger.warning("Timing-Verzögerung erkannt, Timer wird neu synchronisiert")
                    next_switch_time = now + SLIDE_TIME_MS

            clock.tick(30)

    except Exception as e:
        logger.exception(f"Unerwarteter Fehler in der Slideshow: {e}")
        pygame.quit()
        raise


if __name__ == "__main__":
    main()
