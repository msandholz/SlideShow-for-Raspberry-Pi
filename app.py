#!/usr/bin/env python3
"""
Flask-Weboberflaeche fuer eine Raspberry-Pi-Slideshow.

Funktionen:
- Konfiguration: Anzeigedauer, Werbung aktiv, Werbung jedes x-te Bild
- Upload von normalen Bildern und Werbebildern
- Automatische Bildaufbereitung auf 1920 x 1080 ohne Verzerrung
- Live-Logansicht mit Auto-Refresh
- JSON-API fuer ein separates Slideshow-Programm

Standardpfad ist absichtlich /opt/sildeshow, weil er in der Anforderung so
geschrieben wurde. Falls dein Projekt /opt/slideshow heisst:
    export SLIDESHOW_BASE_DIR=/opt/slideshow
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.utils import secure_filename


BASE_DIR = Path(os.environ.get("SLIDESHOW_BASE_DIR", "/opt/sildeshow"))
PICS_DIR = BASE_DIR / "pics"
SPONSORS_DIR = BASE_DIR / "sponsors"
USB_DIR = Path(os.environ.get("SLIDESHOW_USB_DIR", "/mnt/slideshow"))
USB_PICS_DIR = Path(os.environ.get("SLIDESHOW_USB_PICS_DIR", str(USB_DIR / "pics")))
USB_SPONSORS_DIR = Path(os.environ.get("SLIDESHOW_USB_SPONSORS_DIR", str(USB_DIR / "sponsors")))
LOG_DIR = BASE_DIR / "logs"
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = Path(os.environ.get("SLIDESHOW_LOG_FILE", str(LOG_DIR / "webapp.log")))

TARGET_SIZE = (1920, 1080)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp", "gif", "tif", "tiff"}
MAX_UPLOAD_MB = int(os.environ.get("SLIDESHOW_MAX_UPLOAD_MB", "512"))

DEFAULT_CONFIG: dict[str, Any] = {
    "display_seconds": 10,
    "ads_enabled": False,
    "sponsor_every_n": 5,
    "image_width": TARGET_SIZE[0],
    "image_height": TARGET_SIZE[1],
    "updated_at": None,
}

_config_lock = threading.Lock()

app = Flask(__name__)
app.secret_key = os.environ.get("SLIDESHOW_SECRET_KEY", "change-me-on-the-pi")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def ensure_directories() -> None:
    for directory in (BASE_DIR, PICS_DIR, SPONSORS_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    ensure_directories()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_config() -> dict[str, Any]:
    ensure_directories()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, json.JSONDecodeError):
        logging.exception("Konfiguration konnte nicht gelesen werden. Nutze Defaults.")
        return DEFAULT_CONFIG.copy()

    config = DEFAULT_CONFIG.copy()
    config.update(loaded)
    return config


def save_config(config: dict[str, Any]) -> None:
    ensure_directories()
    with _config_lock:
        config["updated_at"] = datetime.now().isoformat(timespec="seconds")
        tmp_file = CONFIG_FILE.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as file:
            json.dump(config, file, indent=2, ensure_ascii=False)
        tmp_file.replace(CONFIG_FILE)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_jpeg_path(destination_dir: Path, original_filename: str) -> Path:
    safe_name = secure_filename(original_filename)
    if not safe_name:
        safe_name = f"upload-{uuid.uuid4().hex}.jpg"

    stem = Path(safe_name).stem[:80] or f"upload-{uuid.uuid4().hex}"
    candidate = destination_dir / f"{stem}.jpg"

    if not candidate.exists():
        return candidate

    for counter in range(1, 10000):
        candidate = destination_dir / f"{stem}-{counter:04d}.jpg"
        if not candidate.exists():
            return candidate

    return destination_dir / f"{stem}-{uuid.uuid4().hex}.jpg"


def normalize_image_to_full_hd(source_file, target_file: Path) -> None:
    """
    Schneidet das Bild auf 16:9 und skaliert es dann auf 1920 x 1080.

    ImageOps.fit arbeitet ohne Verzerrung:
    - zu breite Bilder werden links/rechts beschnitten
    - zu hohe Bilder werden oben/unten beschnitten
    - kleinere Bilder werden hochskaliert
    - EXIF-Rotation wird vorher korrigiert
    """
    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:  # Pillow < 9
        resample_filter = Image.LANCZOS

    with Image.open(source_file) as img:
        img = ImageOps.exif_transpose(img)

        # GIF/TIFF koennen mehrere Frames haben. Hier wird der erste Frame genutzt.
        if getattr(img, "is_animated", False):
            img.seek(0)

        # JPEG kann keinen Alphakanal speichern. Transparenz wird weiss hinterlegt.
        if img.mode in ("RGBA", "LA") or (
            img.mode == "P" and "transparency" in img.info
        ):
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.convert("RGBA").split()[-1]
            background.paste(img.convert("RGBA"), mask=alpha)
            img = background
        else:
            img = img.convert("RGB")

        fitted = ImageOps.fit(
            img,
            TARGET_SIZE,
            method=resample_filter,
            centering=(0.5, 0.5),
        )
        fitted.save(target_file, "JPEG", quality=90, optimize=True, progressive=True)


def count_images(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".jpg")


def usb_source_for(kind: str) -> Path:
    if kind == "pics":
        return USB_PICS_DIR
    if kind == "sponsors":
        return USB_SPONSORS_DIR
    raise ValueError(f"Unbekannter USB-Import-Typ: {kind}")


def iter_image_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []

    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and allowed_file(path.name)
    )


def tail_file(path: Path, lines: int = 200) -> str:
    lines = max(10, min(lines, 1000))
    if not path.exists():
        return f"Noch keine Logdatei vorhanden: {path}"

    try:
        with path.open("rb") as file:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            block_size = 4096
            data = b""
            blocks = 0

            while file_size > 0 and data.count(b"\n") <= lines:
                blocks += 1
                read_size = min(block_size, file_size)
                file.seek(file_size - read_size)
                data = file.read(read_size) + data
                file_size -= read_size

                if blocks > 256:
                    break

        text = data.decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])
    except OSError as exc:
        logging.exception("Logdatei konnte nicht gelesen werden.")
        return f"Logdatei konnte nicht gelesen werden: {exc}"


@app.context_processor
def inject_globals() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "base_dir": str(BASE_DIR),
        "pics_dir": str(PICS_DIR),
        "sponsors_dir": str(SPONSORS_DIR),
        "usb_dir": str(USB_DIR),
        "usb_pics_dir": str(USB_PICS_DIR),
        "usb_sponsors_dir": str(USB_SPONSORS_DIR),
        "log_file": str(LOG_FILE),
    }


@app.get("/")
def index() -> str:
    config = load_config()
    return render_template(
        "index.html",
        config=config,
        pics_count=count_images(PICS_DIR),
        sponsors_count=count_images(SPONSORS_DIR),
    )


@app.post("/config")
def update_config() -> Response:
    try:
        display_seconds = int(request.form.get("display_seconds", "10"))
        sponsor_every_n = int(request.form.get("sponsor_every_n", "5"))
    except ValueError:
        flash("Bitte nur ganze Zahlen eingeben.", "error")
        return redirect(url_for("index"))

    if not 1 <= display_seconds <= 86400:
        flash("Die Anzeigedauer muss zwischen 1 und 86400 Sekunden liegen.", "error")
        return redirect(url_for("index"))

    if not 1 <= sponsor_every_n <= 10000:
        flash("Werbung jedes x-te Bild muss zwischen 1 und 10000 liegen.", "error")
        return redirect(url_for("index"))

    config = load_config()
    config["display_seconds"] = display_seconds
    config["ads_enabled"] = request.form.get("ads_enabled") == "on"
    config["sponsor_every_n"] = sponsor_every_n
    config["image_width"] = TARGET_SIZE[0]
    config["image_height"] = TARGET_SIZE[1]
    save_config(config)

    logging.info(
        "Konfiguration gespeichert: display_seconds=%s ads_enabled=%s sponsor_every_n=%s",
        display_seconds,
        config["ads_enabled"],
        sponsor_every_n,
    )
    flash("Konfiguration gespeichert.", "success")
    return redirect(url_for("index"))


@app.get("/upload")
def upload_page() -> str:
    return render_template(
        "upload.html",
        pics_count=count_images(PICS_DIR),
        sponsors_count=count_images(SPONSORS_DIR),
    )


@app.post("/upload/<kind>")
def upload_images(kind: str) -> Response:
    if kind == "pics":
        destination_dir = PICS_DIR
        label = "normale Anzeigebilder"
    elif kind == "sponsors":
        destination_dir = SPONSORS_DIR
        label = "Werbebilder"
    else:
        flash("Unbekannter Upload-Typ.", "error")
        return redirect(url_for("upload_page"))

    files = request.files.getlist("images")
    if not files or all(not file.filename for file in files):
        flash("Bitte mindestens eine Bilddatei auswaehlen.", "error")
        return redirect(url_for("upload_page"))

    ok_count = 0
    error_count = 0

    for uploaded in files:
        if not uploaded.filename:
            continue

        if not allowed_file(uploaded.filename):
            error_count += 1
            logging.warning("Datei abgelehnt, falscher Dateityp: %s", uploaded.filename)
            continue

        target_file = unique_jpeg_path(destination_dir, uploaded.filename)

        try:
            normalize_image_to_full_hd(uploaded.stream, target_file)
            ok_count += 1
            logging.info("Upload gespeichert: %s -> %s", uploaded.filename, target_file)
        except UnidentifiedImageError:
            error_count += 1
            logging.warning("Datei ist kein lesbares Bild: %s", uploaded.filename)
        except Exception:
            error_count += 1
            logging.exception("Fehler beim Verarbeiten von %s", uploaded.filename)

    if ok_count:
        flash(f"{ok_count} Datei(en) fuer {label} hochgeladen und auf 1920 x 1080 verarbeitet.", "success")
    if error_count:
        flash(f"{error_count} Datei(en) konnten nicht verarbeitet werden.", "error")

    return redirect(url_for("upload_page"))


@app.post("/import-usb/<kind>")
def import_usb_images(kind: str) -> Response:
    if kind == "pics":
        destination_dir = PICS_DIR
        label = "normale Anzeigebilder"
    elif kind == "sponsors":
        destination_dir = SPONSORS_DIR
        label = "Werbebilder"
    else:
        flash("Unbekannter USB-Import-Typ.", "error")
        return redirect(url_for("upload_page"))

    source_dir = usb_source_for(kind)
    image_files = iter_image_files(source_dir)

    if not source_dir.exists():
        flash(f"USB-Quellverzeichnis nicht gefunden: {source_dir}", "error")
        logging.warning("USB-Import abgebrochen, Quelle fehlt: %s", source_dir)
        return redirect(url_for("upload_page"))

    if not image_files:
        flash(f"Keine Bilddateien in {source_dir} gefunden.", "error")
        logging.warning("USB-Import ohne Treffer: %s", source_dir)
        return redirect(url_for("upload_page"))

    ok_count = 0
    error_count = 0

    for source_file in image_files:
        target_file = unique_jpeg_path(destination_dir, source_file.name)
        try:
            with source_file.open("rb") as file:
                normalize_image_to_full_hd(file, target_file)
            ok_count += 1
            logging.info("USB-Import gespeichert: %s -> %s", source_file, target_file)
        except Exception:
            error_count += 1
            logging.exception("Fehler beim USB-Import von %s", source_file)

    if ok_count:
        flash(f"{ok_count} Datei(en) fuer {label} vom USB-Stick importiert und auf 1920 x 1080 verarbeitet.", "success")
    if error_count:
        flash(f"{error_count} Datei(en) konnten beim USB-Import nicht verarbeitet werden.", "error")

    return redirect(url_for("upload_page"))


@app.get("/logs")
def logs_page() -> str:
    return render_template("logs.html")


@app.get("/api/logs")
def api_logs() -> Response:
    try:
        lines = int(request.args.get("lines", "200"))
    except ValueError:
        lines = 200

    return jsonify(
        {
            "log_file": str(LOG_FILE),
            "text": tail_file(LOG_FILE, lines=lines),
            "refreshed_at": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.get("/api/config")
def api_config() -> Response:
    """
    Diese Route kann dein Slideshow-Prozess lesen, z. B.:
        curl http://127.0.0.1:8080/api/config
    """
    return jsonify(load_config())


@app.get("/api/status")
def api_status() -> Response:
    return jsonify(
        {
            "hostname": socket.gethostname(),
            "base_dir": str(BASE_DIR),
            "pics_dir": str(PICS_DIR),
            "sponsors_dir": str(SPONSORS_DIR),
            "usb_dir": str(USB_DIR),
            "usb_pics_dir": str(USB_PICS_DIR),
            "usb_sponsors_dir": str(USB_SPONSORS_DIR),
            "pics_count": count_images(PICS_DIR),
            "sponsors_count": count_images(SPONSORS_DIR),
            "log_file": str(LOG_FILE),
        }
    )


@app.errorhandler(413)
def file_too_large(_error) -> tuple[str, int]:
    flash(f"Upload zu gross. Limit: {MAX_UPLOAD_MB} MB.", "error")
    return redirect(url_for("upload_page")), 303


setup_logging()
ensure_directories()
logging.info("Slideshow-Webapp gestartet. BASE_DIR=%s", BASE_DIR)

if __name__ == "__main__":
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", "8080"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
