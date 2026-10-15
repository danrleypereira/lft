# Brief: draws the 4-PoP diamond instance (ES, MG, RJ, SP) used as the hand-traced
# example in the report, highlighting the minimum-cost path ES -> MG -> SP.
# Uses Pillow only (matplotlib is not required for this figure).
# Regenerate: python3 pca_routing/assignment/figures/make_diamond.py

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "diamond.png"
SCALE = 3  # supersample, then downscale for smooth edges
W, H = 640 * SCALE, 420 * SCALE
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

NODES = {"ES": (320, 60), "MG": (150, 210), "RJ": (490, 210), "SP": (320, 360)}
EDGES = [("ES", "MG", 10), ("ES", "RJ", 30), ("MG", "SP", 10), ("RJ", "SP", 10)]
BEST = {("ES", "MG"), ("MG", "SP")}
RADIUS = 34


def main() -> None:
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    label_font = ImageFont.truetype(FONT_B, 22 * SCALE)
    weight_font = ImageFont.truetype(FONT, 18 * SCALE)

    def p(name):
        x, y = NODES[name]
        return x * SCALE, y * SCALE

    for a, b, w in EDGES:
        on_best = (a, b) in BEST or (b, a) in BEST
        d.line([p(a), p(b)], fill=(200, 60, 40) if on_best else (120, 120, 120),
               width=(6 if on_best else 3) * SCALE // 2)
        (xa, ya), (xb, yb) = p(a), p(b)
        mx, my = (xa + xb) // 2, (ya + yb) // 2
        # nudge the weight label off the line, toward the outside of the diamond
        ox = -62 * SCALE if mx < 320 * SCALE else 62 * SCALE
        text = f"{w} ms"
        tw = d.textlength(text, font=weight_font)
        d.rectangle([mx + ox - tw / 2 - 6, my - 16 * SCALE, mx + ox + tw / 2 + 6, my + 16 * SCALE],
                    fill="white")
        d.text((mx + ox, my), text, font=weight_font, fill=(30, 30, 30), anchor="mm")

    for name in NODES:
        x, y = p(name)
        r = RADIUS * SCALE
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 242, 252), outline=(40, 70, 130),
                  width=3 * SCALE)
        d.text((x, y), name, font=label_font, fill=(20, 40, 90), anchor="mm")

    img = img.resize((W // SCALE, H // SCALE), Image.LANCZOS)
    img.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
