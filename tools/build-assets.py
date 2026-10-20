#!/usr/bin/env python3
"""
Builds the site's assets/ folder from the master files in
"Odyz Assets/Website".

    python3 tools/build-assets.py /path/to/"Odyz Assets"/Website

What it does:
  * re-encodes the app screenshots as WebP (they arrive as 2-3 MB PNGs)
  * shows the 3D-map screenshots through the screen of handphone.png
  * copies the stamps, avatars, logo and favicon into place
  * generates the App Store QR code
  * crops the flag strip out of the passport screenshot
  * renders a 1200x630 og-image.png for social previews

Re-run it any time you update a source file.
"""

import os
import sys
import numpy as np
import segno
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# The published site lives in ../docs.
SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/Odyz Assets--Website"
OUT = os.path.join(SITE, "assets")

ACCENT = "#bb73ff"
BG = "#121212"


APP_STORE_QR_URL = "https://apps.apple.com/app/odyz/id6736624376"


def src(rel):
    return os.path.join(SRC, rel)


def out(rel):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def save_webp(im, rel, quality=86, max_w=None):
    im = im.convert("RGB")
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(out(rel), "WEBP", quality=quality, method=6)
    print(f"  {rel}  {im.width}x{im.height}  {os.path.getsize(out(rel))//1024} KB")


def hand_composite(screenshot_path, rel_out):
    """Show a screenshot through the screen of the phone the hand is holding.

    handphone.png has a transparent screen, so the screenshot goes underneath
    it: find the see-through area connected to the middle of the screen, cover
    it (plus a 2px overlap so no seam shows at the bezel's soft edge), then lay
    the hand, bezel and Dynamic Island back on top.
    """
    hand = Image.open(src("Content/handphone.png")).convert("RGBA")
    a = np.array(hand)[..., 3]
    m = Image.fromarray(np.where(a < 250, 0, 255).astype(np.uint8)).copy()   # copy: floodfill needs its own pixels
    seed = (hand.width * 33 // 100, hand.height * 40 // 100)   # middle of the screen
    ImageDraw.floodfill(m, seed, 128)
    hole = np.array(m) == 128
    ys, xs = np.where(hole)
    x0, y0, x1, y1 = xs.min() - 2, ys.min() - 2, xs.max() + 3, ys.max() + 3
    mask = Image.fromarray((hole * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))

    shot = Image.open(screenshot_path).convert("RGBA").resize((x1 - x0, y1 - y0), Image.LANCZOS)
    layer = Image.new("RGBA", hand.size, (0, 0, 0, 0))
    layer.paste(shot, (x0, y0))
    canvas = Image.new("RGBA", hand.size, (0, 0, 0, 0))
    canvas.paste(layer, (0, 0), mask)
    canvas.alpha_composite(hand)

    canvas = canvas.resize((744, 1008), Image.LANCZOS)          # 0.8x is plenty at display size
    canvas.save(out(rel_out), "WEBP", quality=88, method=6)     # WebP keeps the alpha channel
    print(f"  {rel_out}  {canvas.width}x{canvas.height}  {os.path.getsize(out(rel_out))//1024} KB")


def main():
    print("Screens ->")
    screens = {
        # feature cards
        "screens/passport-light-2.webp": "Content/Pass/IMG_1063.PNG",
        "screens/passport-dark-1.webp": "Content/Pass/IMG_1064.PNG",
        "screens/timeline.webp": "Content/Screenshot 2026-10-19 at 6.39.40 PM.png",
        "screens/worldmap.webp": "Content/IMG_0524.PNG",
    }
    for rel, source in screens.items():
        save_webp(Image.open(src(source)), rel, quality=86, max_w=468)

    print("3D map, shown in the hand ->")
    hand_composite(src("Content/IMG_1044.PNG"), "screens/story-eiffel.webp")  # relive in 3D
    hand_composite(src("Content/IMG_1043.PNG"), "screens/story-louvre.webp")  # right where it happened
    hand_composite(src("Content/IMG_1047.PNG"), "screens/story-pier39.webp")  # global adventures

    print("Stamps ->")
    for name in ["agra", "berlin", "buenosaires", "cairo", "dubai", "istanbul",
                 "la", "newyork", "rio", "rome", "sf", "singapore"]:
        im = Image.open(src(f"Stamps/{name}.png")).convert("RGBA")
        im.save(out(f"stamps/{name}.webp"), "WEBP", quality=90, method=6)
    print(f"  12 stamps")

    print("Brand + people ->")
    logo = Image.open(src("OdyzCentered.png")).convert("RGBA")
    logo.resize((450, 450), Image.LANCZOS).save(out("logo-stamp.png"), optimize=True)
    Image.open(src("favicon.png")).save(out("favicon.png"), optimize=True)
    # Flatten it to black-on-white so it scans reliably wherever it lands.
    # Generated here rather than copied from QRCode.png, which pointed at the
    # retired appstore.com/odyz short link. No country in the URL, so the App
    # Store opens Odyz in the scanner's own storefront.
    segno.make(APP_STORE_QR_URL, error="m").save(out("qr-appstore.png"), scale=12, border=3, dark="#000", light="#fff")
    for i in (1, 2, 3):
        Image.open(src(f"Testimonials/Avatar{i}.png")).save(out(f"avatars/avatar-{i}.png"), optimize=True)
    print("  logo, favicon, QR, 3 avatars")

    print("Flag strip ->")
    # Lift the row of country flags out of the passport screen and key out the
    # purple background behind it, so the flags sit on the dark card cleanly.
    from scipy import ndimage
    strip = Image.open(src("Content/IMG_0490.PNG")).convert("RGB").crop((8, 534, 460, 580))
    lum = np.array(strip).astype(float).mean(axis=2)
    mask = ndimage.binary_fill_holes(
        ndimage.binary_closing(lum > 82, np.ones((3, 3)), iterations=2))
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 150])
    rgba = np.dstack([np.array(strip), (keep * 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(out("flag-strip.png"), "PNG", optimize=True)
    print("  flag-strip.png")

    print("Social image ->")
    og = Image.new("RGB", (1200, 630), BG)
    glow = Image.new("RGB", (1200, 630), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([180, -420, 1020, 420], fill=(38, 25, 54))
    og = Image.blend(og, glow, 0.9)
    stamp = Image.open(src("OdyzCentered.png")).convert("RGBA")
    stamp.thumbnail((250, 250), Image.LANCZOS)
    og.paste(stamp, ((1200 - stamp.width) // 2, 70), stamp)
    d = ImageDraw.Draw(og)

    def font(size, bold=True):
        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def centered(text, y, size, fill):
        f = font(size)
        w = d.textbbox((0, 0), text, font=f)[2]
        d.text(((1200 - w) // 2, y), text, font=f, fill=fill)

    centered("Odyz", 350, 78, ACCENT)
    centered("THE ULTIMATE TRAVEL EXPERIENCE", 460, 40, "#ffffff")
    centered("Automatic trip tracking, built from your photos", 525, 25, "#9a9a9a")
    og.save(out("og-image.png"), optimize=True)
    print("  og-image.png 1200x630")


if __name__ == "__main__":
    main()
