import os
# import time  # GELÖSCHT/ERSETZT: time.time() wird durch pygame.time.get_ticks() ersetzt
import pygame

USB_PATH = "/data/slideshow"
DEFAULT_IMAGE = "/opt/slideshow/default.jpg"
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

SLIDE_TIME = 5                        # Bildanzeige in Sekunden
SLIDE_TIME_MS = SLIDE_TIME * 1000     # VERBESSERT: Zeiten in Millisekunden für pygame.time.get_ticks()
SCAN_INTERVAL_MS = 2000               # VERBESSERT: USB-Stick nicht in jedem Frame scannen


def find_images():
    """Findet Bilder auf USB-Stick oder gibt leere Liste zurück."""
    if not os.path.exists(USB_PATH):
        return []

    try:
        files = [
            os.path.join(USB_PATH, f)
            for f in os.listdir(USB_PATH)
            if f.lower().endswith(SUPPORTED_EXT)
        ]
    except OSError as e:         # VERBESSERT: USB kann kurzzeitig nicht lesbar sein
        print(f"Fehler beim Lesen von {USB_PATH}: {e}")
        return []

    return sorted(files)


def load_image(path, screen_size):
    """Lädt Bild, skaliert es proportional und zentriert es (kein Verzerren)."""

    img = pygame.image.load(path)
    img = img.convert()                     # VERBESSERT: convert() beschleunigt späteres Blitting 
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
    surface = surface.convert()       # VERBESSERT: convert() für schnellere Anzeige
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
    except Exception as e:
        print(f"Fehler beim Laden des Default-Bildes: {DEFAULT_IMAGE} -> {e}")
        default_surface = pygame.Surface(screen_size).convert()
        default_surface.fill((0, 0, 0))

    while True:
        now = pygame.time.get_ticks()

        # Exit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

        # images = find_images()  # GELÖSCHT/ERSETZT: nicht mehr in jedem Frame scannen

        # VERBESSERT: USB-Verzeichnis nur periodisch scannen
        if now >= next_scan_time:
            images = find_images()
            next_scan_time = now + SCAN_INTERVAL_MS

            # Wenn neue Bilder vorhanden oder Liste leer geworden ist
            if images != current_images:
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
            except Exception as e:
                print(f"Fehler beim Laden: {path} -> {e}")

                # VERBESSERT: Fehlerhaftes Bild überspringen
                if len(current_images) > 1:
                    index = (index + 1) % len(current_images)
                    current_path = None
                    current_surface = None
                    next_switch_time = now + 250
                    continue

                # VERBESSERT: Bei keinem gültigen Bild Default anzeigen
                current_surface = default_surface
                current_path = DEFAULT_IMAGE

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

            # VERBESSERT:
            # Nicht einfach "now + SLIDE_TIME_MS", sondern geplante Zeit fortschreiben.
            # Dadurch driftet die Slideshow weniger, wenn ein Frame mal länger dauert.
            next_switch_time += SLIDE_TIME_MS

            # VERBESSERT:
            # Falls das Programm länger blockiert war, nicht mehrere Bilder sofort überspringen.
            if now > next_switch_time + SLIDE_TIME_MS:
                next_switch_time = now + SLIDE_TIME_MS

        clock.tick(30)


if __name__ == "__main__":
    main()
