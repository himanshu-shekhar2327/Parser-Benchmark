"""
Seeded degraded-invoice dataset generator (all data is FAKE).

Why seeded: every parser must see byte-identical images, so differences in
results come from the parsers, not from random noise. Re-running this script
reproduces the same files.

Outputs (data/dataset/, committed to git because it is fake data):
  images/<invoice>_<template>_L<level>_s<seed>.{png|jpg}
  ground_truth/<invoice>.json      (true fields and line items)
  manifest.csv                     (file -> template, level, degradation params)

Design choices:
  - Two table templates: 'grid' (full borders) and 'plain' (only a header rule),
    because table detectors behave very differently on bordered vs borderless.
  - Money >= 1000 is printed with a thousands comma ("1,450.00"), like real invoices.
  - Level 0 is a lossless PNG; levels 1-3 are saved directly as JPEG at the stated
    quality, like phone photos (this also keeps the dataset small).
"""

import csv
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path("data/dataset")
IMG_DIR, GT_DIR = OUT / "images", OUT / "ground_truth"
MASTER_SEED = 2026
N_INVOICES = 4
SEEDS_PER_LEVEL = 2

# level: (rotation_deg, noise_sigma, blur_radius, jpeg_quality or None)
LEVELS = {0: (0, 0, 0, None), 1: (1.0, 10, 0.6, 80),
          2: (3.0, 25, 1.1, 50), 3: (6.0, 45, 1.8, 25)}

SUPPLIERS = ["Example Supplies (Pty) Ltd", "Sample Traders (Pty) Ltd",
             "Demo Stationers (Pty) Ltd"]
ITEMS = ["USB cable", "Desk lamp", "Printer paper A4", "Toner cartridge",
         "Office chair", "Stapler", "Whiteboard markers", "Laptop stand",
         "HDMI cable", "Filing cabinet"]
# Invoice-number styles with letters and zeros, to expose O/0 and I/1 OCR confusions.
INV_FORMATS = ["INV-{:04d}", "IN{:06d}", "POS-{:05d}"]


def fmt(x: float) -> str:
    return f"{x:,.2f}"


def font(size: int):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_invoice(rng: random.Random, n: int) -> dict:
    """Builds one fake invoice whose arithmetic is internally consistent."""
    lines = []
    for desc in rng.sample(ITEMS, rng.randint(3, 6)):
        qty = rng.randint(1, 12)
        unit = round(rng.uniform(25, 2500), 2)
        lines.append({"description": desc, "quantity": qty, "unit_price": unit,
                      "line_amount": round(qty * unit, 2)})
    subtotal = round(sum(l["line_amount"] for l in lines), 2)
    vat = round(subtotal * 0.15, 2)
    return {
        "invoice_id": f"inv{n:02d}",
        "supplier_name": rng.choice(SUPPLIERS),
        "supplier_tax_no": "4" + "".join(rng.choice("0123456789") for _ in range(9)),
        "invoice_number": rng.choice(INV_FORMATS).format(rng.randint(100, 9999)),
        "invoice_date": f"{rng.randint(1, 28):02d}/10/2026",
        "lines": lines,
        "subtotal": subtotal,
        "vat": vat,
        "total": round(subtotal + vat, 2),
    }


def render(inv: dict, template: str) -> Image.Image:
    """Draws a clean grayscale invoice. Numbers are right-aligned in columns."""
    img = Image.new("L", (1100, 950), 255)
    d = ImageDraw.Draw(img)
    big, f = font(36), font(26)

    d.text((50, 40), "TAX INVOICE", font=big, fill=0)
    y = 100
    for t in (inv["supplier_name"], f"VAT No: {inv['supplier_tax_no']}",
              f"Invoice No: {inv['invoice_number']}", f"Date: {inv['invoice_date']}"):
        d.text((50, y), t, font=f, fill=0)
        y += 38

    cols = [50, 520, 640, 820, 1000]          # column boundaries (x)
    row_h = 50
    rows = [["Description", "Qty", "Unit Price", "Amount"]] + [
        [l["description"], str(l["quantity"]), fmt(l["unit_price"]), fmt(l["line_amount"])]
        for l in inv["lines"]]
    top = y + 20
    for r, row in enumerate(rows):
        ty = top + r * row_h + 9
        for c, text in enumerate(row):
            if c == 0:
                d.text((cols[0] + 10, ty), text, font=f, fill=0)
            else:                              # right-align numeric columns
                w = d.textlength(text, font=f)
                d.text((cols[c + 1] - 10 - w, ty), text, font=f, fill=0)

    bottom = top + row_h * len(rows)
    if template == "grid":                     # full borders
        for r in range(len(rows) + 1):
            d.line([(cols[0], top + r * row_h), (cols[-1], top + r * row_h)], fill=0, width=2)
        for x in cols:
            d.line([(x, top), (x, bottom)], fill=0, width=2)
    else:                                      # 'plain': only a rule under the header
        d.line([(cols[0], top + row_h), (cols[-1], top + row_h)], fill=0, width=2)

    ty = bottom + 25
    for label, value in (("Subtotal", inv["subtotal"]), ("VAT 15%", inv["vat"]),
                         ("Total", inv["total"])):
        d.text((640, ty), label, font=f, fill=0)
        w = d.textlength(fmt(value), font=f)
        d.text((cols[-1] - 10 - w, ty), fmt(value), font=f, fill=0)
        ty += 42
    return img


def degrade(img: Image.Image, level: int, seed: int) -> Image.Image:
    """Tilt, blur, then add sensor-like noise. Fully determined by `seed`."""
    rot, sigma, blur, _ = LEVELS[level]
    if level == 0:
        return img
    rs = np.random.RandomState(seed)
    img = img.rotate(rot * rs.choice([-1, 1]), expand=True, fillcolor=255,
                     resample=Image.BICUBIC)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    arr = np.asarray(img, dtype=np.float32) + rs.normal(0, sigma, (img.height, img.width))
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    GT_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(MASTER_SEED)
    manifest = []

    for n in range(1, N_INVOICES + 1):
        inv = make_invoice(rng, n)
        (GT_DIR / f"{inv['invoice_id']}.json").write_text(
            json.dumps(inv, indent=2), encoding="utf-8")
        for template in ("grid", "plain"):
            clean = render(inv, template)
            for level, (rot, sigma, blur, q) in LEVELS.items():
                for s in ([0] if level == 0 else range(1, SEEDS_PER_LEVEL + 1)):
                    seed = MASTER_SEED + 1000 * n + 100 * level + 10 * s + (template == "plain")
                    out = degrade(clean, level, seed)
                    ext = "png" if q is None else "jpg"
                    name = f"{inv['invoice_id']}_{template}_L{level}_s{s}.{ext}"
                    if q is None:
                        out.save(IMG_DIR / name)
                    else:
                        out.save(IMG_DIR / name, "JPEG", quality=q)
                    manifest.append({"file": name, "invoice_id": inv["invoice_id"],
                                     "template": template, "level": level, "seed": seed,
                                     "rotation": rot, "noise": sigma, "blur": blur,
                                     "jpeg_quality": q or ""})

    with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(manifest[0].keys()))
        w.writeheader()
        w.writerows(manifest)
    print(f"Wrote {len(manifest)} images to {IMG_DIR}")


if __name__ == "__main__":
    main()