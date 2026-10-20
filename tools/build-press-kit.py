#!/usr/bin/env python3
"""
Builds the press kit at docs/press/ from the site's own assets.

    python3 tools/build-press-kit.py

What it does:
  * exports the app screenshots as JPG and the live-experience photos (an iPhone in
    a real hand) as PNG
  * exports the app icon, the logo stamp and the 12 city stamps as PNG
  * turns og-image.png into the 1200x630 key art
  * zips everything in docs/press/files/, including the hand-written
    odyz-fact-sheet.txt, into docs/press/odyz-press-kit.zip

The screenshots are only as large as the site's copies (468-540 px wide).
To ship full-resolution ones, drop the master PNGs into SCREENSHOT_OVERRIDES
below and re-run.
"""

import os
import zipfile
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "docs", "assets")
PRESS = os.path.join(ROOT, "docs", "press")
FILES = os.path.join(PRESS, "files")
ZIP = os.path.join(PRESS, "odyz-press-kit.zip")

BG = "#121212"

# Published name -> site asset. Order is the order on the press page.
SCREENSHOTS = [
    ("odyz-01-world-trips.jpg", "screens/hero-feature.webp"),
    ("odyz-02-passport-dark.jpg", "screens/passport-dark-1.webp"),
    ("odyz-03-passport-light.jpg", "screens/passport-light-2.webp"),
    ("odyz-04-compare-with-friends.jpg", "screens/passport-compare.webp"),
    ("odyz-05-travel-timeline.jpg", "screens/timeline.webp"),
    ("odyz-06-world-map.jpg", "screens/worldmap.webp"),
    ("odyz-07-trip-photos.jpg", "screens/shelf-uganda.webp"),
    ("odyz-08-ipad.jpg", "screens/download-ipad.webp"),
]

# Published name -> full-resolution master, used instead of the site asset when set.
SCREENSHOT_OVERRIDES = {}

LIVE = [
    ("odyz-live-eiffel-tower.png", "screens/story-eiffel.webp"),
    ("odyz-live-louvre.png", "screens/story-louvre.webp"),
    ("odyz-live-pier-39.png", "screens/story-pier39.webp"),
]

STAMPS = ["agra", "berlin", "buenosaires", "cairo", "dubai", "istanbul",
          "la", "newyork", "rio", "rome", "sf", "singapore"]


def out(rel):
    p = os.path.join(FILES, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def report(rel, im):
    print(f"  {rel}  {im.width}x{im.height}  {os.path.getsize(out(rel)) // 1024} KB")


def save_jpg(src_path, rel):
    im = Image.open(src_path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        flat = Image.new("RGB", im.size, BG)
        flat.paste(im, mask=im.split()[-1])
        im = flat
    im.convert("RGB").save(out(rel), "JPEG", quality=92, optimize=True, progressive=True)
    report(rel, im)


def save_png(src_path, rel):
    im = Image.open(src_path).convert("RGBA")
    im.save(out(rel), "PNG", optimize=True)
    report(rel, im)


def build_files():
    print("screenshots/")
    for name, asset in SCREENSHOTS:
        save_jpg(SCREENSHOT_OVERRIDES.get(name, os.path.join(ASSETS, asset)), f"screenshots/{name}")

    print("live/")
    for name, asset in LIVE:
        save_png(os.path.join(ASSETS, asset), f"live/{name}")

    print("stamps/")
    for city in STAMPS:
        save_png(os.path.join(ASSETS, f"stamps/{city}.webp"), f"stamps/odyz-stamp-{city}.png")

    print("icon/ and logo/")
    save_png(os.path.join(ASSETS, "app-icon.png"), "icon/odyz-icon.png")
    save_png(os.path.join(ASSETS, "logo-stamp.png"), "logo/odyz-logo-stamp.png")

    print("key art")
    save_jpg(os.path.join(ASSETS, "og-image.png"), "odyz-key-art-1200x630.jpg")


def build_zip():
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, names in sorted(os.walk(FILES)):
            for n in sorted(names):
                if n.startswith("."):
                    continue
                path = os.path.join(folder, n)
                z.write(path, os.path.join("odyz-press-kit", os.path.relpath(path, FILES)))
    print(f"odyz-press-kit.zip  {os.path.getsize(ZIP) / 1e6:.1f} MB")


if __name__ == "__main__":
    build_files()
    build_zip()
