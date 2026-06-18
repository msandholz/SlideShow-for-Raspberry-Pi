
#!/usr/bin/env python3

import os
import time
import hashlib
import logging
import subprocess
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff"
}

MEDIA_ROOTS = [
    Path("/data/slideshow"),
    Path("/media/admin"),
    Path("/media"),
    Path("/mnt")
]

DEFAULT_IMAGE = Path("/opt/slideshow/default.jpg")
FILELIST = Path("/tmp/slideshow_images.txt")

LOGFILE = "/var/log/slideshow/slideshow.log"

SLIDE_DELAY = 10

logging.basicConfig(
    filename=LOGFILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def find_images():
    images = []

    for root in MEDIA_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            try:
                if path.is_file():
                    if path.suffix.lower() in IMAGE_EXTENSIONS:
                        images.append(path)
            except Exception:
                pass

    if not images:
        return [DEFAULT_IMAGE]

    return sorted(images)


def image_signature(images):
    data = ""

    for img in images:
        try:
            stat = img.stat()
            data += f"{img}{stat.st_mtime}{stat.st_size}"
        except Exception:
            pass

    return hashlib.sha256(data.encode()).hexdigest()


def write_filelist(images):
    with open(FILELIST, "w") as f:
        for image in images:
            f.write(str(image) + "\n")


def start_feh():
    env = os.environ.copy()
    env["DISPLAY"] = ":0"

    return subprocess.Popen(
        [
            "feh",
            "--fullscreen",
            "--auto-zoom",
            "--borderless",
            "--hide-pointer",
            "--slideshow-delay",
            str(SLIDE_DELAY),
            "--reload",
            "5",
            "--filelist",
            str(FILELIST),
        ],
        env=env
    )

def main():
    logging.info("Slideshow gestartet")

    current_hash = ""
    feh_process = None

    while True:

        images = find_images()
        new_hash = image_signature(images)

        if new_hash != current_hash:
            
            # ---------------------------
            # FALLBACK: nur Standardbild
            # ---------------------------           
            if images == [DEFAULT_IMAGE]:
                logging.info("Keine Bilder gefunden. Standardbild wird angezeigt.")
                
                # laufende Slideshow beenden
                if feh_process:
                    feh_process.terminate()
                    feh_process = None

                subprocess.Popen([
                    "feh",
                    "--fullscreen",
                    "--auto-zoom",
                    DEFAULT_IMAGE
                ])

                current_hash = new_hash
                time.sleep(3)
                continue   # <<< WICHTIG: Rest überspringen

            # ---------------------------
            # NORMALFALL: Slideshow
            # ---------------------------
            logging.info(f"{len(images)} Bilder gefunden.")

            write_filelist(images)

            if feh_process:
                feh_process.terminate()

            feh_process = start_feh()

            current_hash = new_hash
            
         time.sleep(3)

if __name__ == "__main__":
    main()
