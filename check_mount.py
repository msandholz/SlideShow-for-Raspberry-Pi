#!/usr/bin/env python3

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

USB_ROOT = Path("/data/slideshow")

images = []

for file in USB_ROOT.rglob("*"):

    if file.is_file():

        if file.suffix.lower() in IMAGE_EXTENSIONS:

            images.append(file)

print(f"{len(images)} Bild(er) gefunden:\n")

for image in images:
    print(image)
