# ------------------------------------------------------------------
# SlideShow 
#
# Version: 2.0
# Date: 24.06.2026
# ------------------------------------------------------------------

import os
import pygame

# VERBESSERT: Logging ergänzt
import logging
from logging.handlers import RotatingFileHandler

USB_PATH = "/opt/slideshow/pics"
DEFAULT_IMAGE = "/opt/slideshow/default.jpg"
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

SLIDE_TIME = 8  # Sekunden

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
        logger.error(f"Fehler beim Lesen von {USB_PATH}: {e}")
        return []

    return sorted(files)


def load_image(path, screen_size):
    """Lädt Bild, skaliert es proportional und zentriert es, ohne es zu verzerren."""

    img = pygame.image.load(path)

    # VERBESSERT: convert() beschleunigt späteres Blitting
    img = img.convert()

    screen_w, screen_h = screen_size
    img_w, img_h = img.get_size()

    # VERBESSERT: Schutz gegen defekte Bilder mit 0-Größe
    if img_w <= 0 or img_h <= 0:
        raise ValueError(f"Ungültige Bildgröße: {img_w}x{img_h}")

    # Skalierungsfaktor berechnen, Aspect Ratio bleibt erhalten
    scale = min(screen_w / img_w, screen_h / img_h)

    # VERBESSERT: max(1, ...) verhindert theoretisch eine Zielgröße von 0 Pixeln
    new_size = (
        max(1, int(img_w * scale)),
        max(1, int(img_h * scale))
    )

    img = pygame.transform.smoothscale(img, new_size)

    # Schwarzes Hintergrundbild erzeugen
    surface = pygame.Surface(screen_size)

    # VERBESSERT: convert() für schnellere Anzeige
    surface = surface.convert()

    surface.fill((0, 0, 0))

    # Zentrieren
    x = (screen_w - new_size[0]) // 2
    y = (screen_h - new_size[1]) // 2

    surface.blit(img, (x, y))

    return surface


def get_image_path(current_images, index):
    """
    Gibt den Bildpfad für den aktuellen Index zurück.

    Wenn keine USB-Bilder vorhanden sind, wird das Default-Bild verwendet.
    """
    if len(current_images) == 0:
        return DEFAULT_IMAGE

    index %= len(current_images)
    return current_images[index]


def get_next_usb_image_path(current_images, index):
    """
    Gibt den Pfad des nächsten USB-Bildes zurück.

    Wichtig:
    - Das Default-Bild wird hier bewusst nicht vorgeladen.
    - Vorgeladen wird nur, wenn mindestens zwei USB-Bilder vorhanden sind.
    """
    if len(current_images) <= 1:
        return None

    next_index = (index + 1) % len(current_images)
    return current_images[next_index]


def main():
    # VERBESSERT: Logging direkt beim Start initialisieren
    logger = setup_logging()
    logger.info("Slideshow wird gestartet")

    os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"

    try:
        pygame.init()
        pygame.display.set_caption("Slideshow")

        # Cursor ausblenden
        pygame.mouse.set_visible(False)

        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen_size = screen.get_size()

        logger.info(f"Display initialisiert: {screen_size[0]}x{screen_size[1]}")

        clock = pygame.time.Clock()

        current_images = []
        index = 0

        # VERBESSERT: pygame-interne monotone Zeitbasis
        now = pygame.time.get_ticks()
        next_switch_time = now + SLIDE_TIME_MS
        next_scan_time = 0

        # VERBESSERT: aktuelles Bild zwischenspeichern
        current_path = None
        current_surface = None

        # ------------------------------------------------------------------
        # NEU: Variablen für echtes Vorladen des nächsten USB-Bildes.
        #
        # preloaded_path:
        #     Pfad des Bildes, das bereits im Voraus geladen wurde.
        #
        # preloaded_surface:
        #     Fertig geladene, skalierte und zentrierte Surface.
        #
        # Diese Surface kann beim Bildwechsel sofort verwendet werden,
        # ohne dass beim Umschalten erneut vom USB-Stick gelesen werden muss.
        # ------------------------------------------------------------------
        preloaded_path = None
        preloaded_surface = None

        # VERBESSERT: Default-Bild vorladen, damit bei Fehlern etwas angezeigt wird
        try:
            default_surface = load_image(DEFAULT_IMAGE, screen_size)
            logger.info(f"Default-Bild geladen: {DEFAULT_IMAGE}")
        except Exception as e:
            logger.error(f"Fehler beim Laden des Default-Bildes: {DEFAULT_IMAGE} -> {e}")
            default_surface = pygame.Surface(screen_size).convert()
            default_surface.fill((0, 0, 0))

        while True:
            # Zeit am Anfang der Schleife holen.
            # Diese Zeit wird für Scan-Entscheidungen und den allgemeinen Ablauf genutzt.
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

            # VERBESSERT: USB-Verzeichnis nur periodisch scannen
            if now >= next_scan_time:
                images = find_images(logger)
                next_scan_time = now + SCAN_INTERVAL_MS

                # Wenn neue Bilder vorhanden sind oder die Liste leer geworden ist
                if images != current_images:
                    logger.info(
                        f"Bildliste geändert: vorher={len(current_images)}, jetzt={len(images)}"
                    )

                    current_images = images
                    index = 0

                    # VERBESSERT: Timer sauber neu starten
                    next_switch_time = now + SLIDE_TIME_MS

                    # VERBESSERT: erzwingt Neu-Laden des aktuellen Bildes
                    current_path = None
                    current_surface = None

                    # ------------------------------------------------------------------
                    # NEU:
                    # Wenn sich die Bildliste ändert, ist ein eventuell vorgeladenes
                    # Bild nicht mehr vertrauenswürdig.
                    #
                    # Beispiel:
                    # - USB-Stick wurde gewechselt
                    # - Bild wurde gelöscht
                    # - Reihenfolge hat sich geändert
                    #
                    # Deshalb wird der Preload-Cache hier verworfen.
                    # ------------------------------------------------------------------
                    preloaded_path = None
                    preloaded_surface = None

            # Auswahl des aktuellen Bildes
            if len(current_images) > 0:
                index %= len(current_images)

            path = get_image_path(current_images, index)

            # ------------------------------------------------------------------
            # AKTUELLES BILD LADEN ODER AUS PRELOAD ÜBERNEHMEN
            #
            # Wenn das gewünschte aktuelle Bild bereits vorgeladen wurde,
            # wird es sofort übernommen.
            #
            # Andernfalls wird es normal geladen. Das ist zum Beispiel beim
            # Programmstart nötig oder wenn der USB-Stick gewechselt wurde.
            # ------------------------------------------------------------------
            if path != current_path:
                if preloaded_path == path and preloaded_surface is not None:
                    # NEU: Vorgeladenes Bild wird zum aktuellen Bild
                    current_surface = preloaded_surface
                    current_path = preloaded_path

                    logger.info(f"Vorgeladenes Bild übernommen: {current_path}")

                    # Preload-Cache leeren, damit danach das nächste Bild vorgeladen wird
                    preloaded_path = None
                    preloaded_surface = None

                else:
                    # Fallback: Bild ist nicht vorgeladen und muss normal geladen werden
                    try:
                        current_surface = load_image(path, screen_size)
                        current_path = path
                        logger.info(f"Bild direkt geladen: {path}")
                    except Exception as e:
                        logger.error(f"Fehler beim Laden: {path} -> {e}")

                        # VERBESSERT: Fehlerhaftes Bild überspringen
                        if len(current_images) > 1:
                            logger.warning(f"Fehlerhaftes Bild wird übersprungen: {path}")

                            index = (index + 1) % len(current_images)
                            current_path = None
                            current_surface = None

                            # Auch Preload verwerfen, weil der Index geändert wurde
                            preloaded_path = None
                            preloaded_surface = None

                            next_switch_time = now + 250
                            continue

                        # VERBESSERT: Bei keinem gültigen Bild Default anzeigen
                        current_surface = default_surface
                        current_path = DEFAULT_IMAGE
                        logger.warning("Fallback auf Default-Bild")

            # Immer nur die bereits geladene Surface anzeigen
            if current_surface is not None:
                screen.blit(current_surface, (0, 0))
            else:
                screen.blit(default_surface, (0, 0))

            pygame.display.flip()

            # ------------------------------------------------------------------
            # VERBESSERUNG:
            # Zeit nach dem Anzeigen erneut holen.
            #
            # Grund:
            # Zwischen dem ersten now am Schleifenanfang und dieser Stelle können
            # langsame Operationen liegen:
            # - USB-Zugriff
            # - pygame.image.load()
            # - pygame.transform.smoothscale()
            # - pygame.display.flip()
            #
            # Wenn diese Operationen länger dauern, wäre das alte now veraltet.
            # ------------------------------------------------------------------
            now = pygame.time.get_ticks()

            # ------------------------------------------------------------------
            # NEU: Echtes Vorladen des nächsten USB-Bildes.
            #
            # Das nächste Bild wird geladen, während das aktuelle Bild bereits
            # angezeigt wird.
            #
            # Dadurch passiert der langsame USB-Zugriff nicht mehr direkt beim
            # Bildwechsel, sondern vorher.
            #
            # Wichtig:
            # Dieses Vorladen ist absichtlich nicht in einem separaten Thread.
            # pygame.image.load(), Surface.convert() und Display-Surfaces sind
            # im Hauptthread auf einem Raspberry Pi meist zuverlässiger.
            #
            # Nachteil:
            # Wenn das Vorladen sehr lange dauert, kann die Hauptschleife kurz
            # blockieren. Das aktuell sichtbare Bild bleibt aber währenddessen
            # auf dem Display stehen.
            # ------------------------------------------------------------------
            next_preload_path = get_next_usb_image_path(current_images, index)

            if next_preload_path is not None:
                preload_missing = (
                    preloaded_path != next_preload_path or
                    preloaded_surface is None
                )

                if preload_missing:
                    try:
                        preloaded_surface = load_image(next_preload_path, screen_size)
                        preloaded_path = next_preload_path
                        logger.info(f"Nächstes Bild vorgeladen: {preloaded_path}")
                    except Exception as e:
                        logger.error(
                            f"Fehler beim Vorladen des nächsten Bildes: "
                            f"{next_preload_path} -> {e}"
                        )

                        # Fehlerhaften Preload verwerfen.
                        # Das Bild wird beim eigentlichen Anzeigen nochmals
                        # über die normale Fehlerbehandlung behandelt.
                        preloaded_path = None
                        preloaded_surface = None

            else:
                # Wenn es kein nächstes USB-Bild gibt, darf kein alter Preload
                # weiter im Speicher bleiben.
                preloaded_path = None
                preloaded_surface = None

            # ------------------------------------------------------------------
            # Robuste Timer-Logik.
            #
            # Die Anzeigezeit des nächsten Bildes wird ab dem tatsächlichen
            # Umschaltzeitpunkt neu gezählt.
            # ------------------------------------------------------------------
            if len(current_images) > 1 and now >= next_switch_time:
                index = (index + 1) % len(current_images)

                # Erzwingt im nächsten Loop die Übernahme des vorgeladenen Bildes
                # oder, falls es nicht vorgeladen werden konnte, ein direktes Laden.
                current_path = None

                logger.info(f"Wechsel zu Bildindex: {index}")

                # Timer ab aktueller Zeit neu starten.
                next_switch_time = now + SLIDE_TIME_MS

            clock.tick(30)

    except Exception as e:
        logger.exception(f"Unerwarteter Fehler in der Slideshow: {e}")
        pygame.quit()
        raise


if __name__ == "__main__":
    main()
