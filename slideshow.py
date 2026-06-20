import os
import time
import pygame

USB_PATH = "/data/slideshow"
DEFAULT_IMAGE = "/opt/slideshow/default.jpg"
SUPPORTED_EXT = (".jpg", ".jpeg", ".png")

SLIDE_TIME = 5  # Sekunden
SCAN_INTERVAL = 2  # Nur alle 2 Sekunden USB-Verzeichnis neu prüfen

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
    last_scan = 0

    # aktuell angezeigtes Bild cachen
    current_path = None
    current_surface = None

    while True:
        # Exit event
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                return

            # USB-Verzeichnis nicht in jedem Frame scannen, sondern nur periodisch
            now = time.time()
            if now - last_scan >= SCAN_INTERVAL:
                images = find_images()
                last_scan = now

            # Wenn neue Bilder vorhanden oder Liste leer geworden ist
            if images != current_images:
                current_images = images
                index = 0
                last_switch = now
                current_path = None   # erzwingt Neuladen des angezeigten Bildes</span>

        # Auswahl Bild
        if len(current_images) == 0:
            path = DEFAULT_IMAGE
        else:
            path = current_images[index]


        # Bild nur neu laden, wenn sich der Pfad geändert hat
        if path != current_path:
            try:
                current_surface = load_image(path, screen_size)
                current_path = path
            except Exception as e:
                print(f"Fehler beim Laden: {path} -> {e}")
                current_surface = None

        # Immer nur die bereits geladene Surface anzeigen</span>
        if current_surface is not None:
            screen.blit(current_surface, (0, 0))

        pygame.display.flip()

        # Bildwechsel nur wenn mehrere Bilder vorhanden
        if len(current_images) > 1 and now - last_switch > SLIDE_TIME:
            index = (index + 1) % len(current_images)
            last_switch = time.time()
            last_switch = now
            current_path = None   # nächstes Bild neu laden

        clock.tick(30)


if __name__ == "__main__":
    main()
