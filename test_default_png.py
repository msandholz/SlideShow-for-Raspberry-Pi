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
