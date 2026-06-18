
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
    """Lädt Bild und skaliert es auf Bildschirmgröße."""
    img = pygame.image.load(path)
    img = pygame.transform.scale(img, screen_size)
    return img


def main():
    pygame.init()
    pygame.display.set_caption("Slideshow")

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
