"""
Generates a synthetic "scanned" drilling report image for the OCR demo.
Renders report text onto an image with a monospace font and light scan-like
noise, so the extraction pipeline demo can show a genuine image -> OCR ->
structured-JSON flow instead of only reading clean .txt input.

Run: python3 generate_scan_sample.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_reports")
FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"

SOURCE_TEXT = """OIL INDIA LIMITED
DAILY DRILLING REPORT

Well Name: LAK-003
Field: Lakwa
Spud Date: 09-11-2019
Rig: OIL Rig-22

FORMATION TOPS
Alluvium - 0m
Girujan Clay - 145m
Tipam Sandstone - 795m
Barail Group - 1605m

CASING PROGRAM
20 in casing set at 148m
13.375 in casing set at 790m
9.625 in casing set at 1590m

MUD PROGRAM
Current mud weight 1.35 SG water-based polymer mud, drilling ahead in
Barail Group at 1870m.

NPT EVENTS
Total mud loss encountered on entering vugular zone in Barail Group at
1865m; circulation lost within 40 minutes.
Differential sticking encountered in Barail Group at 1920m; freed after
9 hrs of jarring and spotting pill.
Abnormal torque spike observed while drilling Barail Group, attributed to
tight hole and ledging; reamed and continued.
"""


def generate(out_name="LAK-003_DDR_scanned.png", noise_sigma=4, seed=7):
    font_size = 20
    font = ImageFont.truetype(FONT_PATH, font_size) if os.path.exists(FONT_PATH) else ImageFont.load_default()

    lines = SOURCE_TEXT.split("\n")
    line_height = int(font_size * 1.45)
    width = 1000
    height = line_height * len(lines) + 60

    img = Image.new("L", (width, height), color=248)
    draw = ImageDraw.Draw(img)
    y = 30
    for line in lines:
        draw.text((30, y), line, fill=15, font=font)
        y += line_height

    rng = np.random.default_rng(seed)
    arr = np.array(img).astype(np.int16)
    noise = rng.normal(0, noise_sigma, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype("uint8")
    out_img = Image.fromarray(arr)

    out_path = os.path.join(SAMPLE_DIR, out_name)
    out_img.save(out_path)
    print(f"Saved {out_path} ({out_img.size[0]}x{out_img.size[1]})")
    return out_path


if __name__ == "__main__":
    generate()
