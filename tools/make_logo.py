"""Generate the HERMETIKS brand kit from one geometry definition (SVG + PNG + ICO).

Mark: an "H" built from two curved bars and a crossbar, followed by a large sound-wave arc.
Wordmark: HERMETIKS in BBH Bartle, SOUNDBOARD in Rethink Sans.
"""
import math
import os

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "brand")
RES = os.path.join(ROOT, "hermetiks", "resources")
INSTALLER = os.path.join(ROOT, "installer")
FONTS = os.path.join(RES, "fonts")
BARTLE = os.path.join(FONTS, "BBHBartle-Regular.ttf")
RETHINK = os.path.join(FONTS, "RethinkSans-Bold.ttf")

# ---- mark geometry (arc centre at origin, opens to the left) -------------------------
BANDS = [  # (inner radius, outer radius, half height)
    (26, 38, 17),    # H left bar
    (50, 62, 17),    # H right bar
    (68, 82, 46),    # sound-wave arc
]
CROSSBAR = (37, 51, 3.6)  # x0, x1, half height


def band_path(r_in, r_out, h):
    xo, xi = math.sqrt(r_out ** 2 - h ** 2), math.sqrt(r_in ** 2 - h ** 2)
    return (f"M{xo:.2f},{-h:.2f} A{r_out},{r_out} 0 0 1 {xo:.2f},{h:.2f} "
            f"L{xi:.2f},{h:.2f} A{r_in},{r_in} 0 0 0 {xi:.2f},{-h:.2f} Z")


def band_poly(r_in, r_out, h, n=64):
    ao, ai = math.asin(h / r_out), math.asin(h / r_in)
    pts = [(r_out * math.cos(-ao + 2 * ao * i / n), r_out * math.sin(-ao + 2 * ao * i / n)) for i in range(n + 1)]
    pts += [(r_in * math.cos(ai - 2 * ai * i / n), r_in * math.sin(ai - 2 * ai * i / n)) for i in range(n + 1)]
    return pts


def mark_shapes():
    """List of (svg_path, polygon) in mark units."""
    shapes = [(band_path(*b), band_poly(*b)) for b in BANDS]
    x0, x1, h = CROSSBAR
    rect = [(x0, -h), (x1, -h), (x1, h), (x0, h)]
    shapes.append((f"M{x0},{-h} H{x1} V{h} H{x0} Z", rect))
    return shapes


def mark_bounds():
    xs = [p[0] for _, poly in mark_shapes() for p in poly]
    ys = [p[1] for _, poly in mark_shapes() for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def mark_svg(fill, pad=0):
    x0, y0, x1, y1 = mark_bounds()
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    paths = "".join(f'<path d="{d}"/>' for d, _ in mark_shapes())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0 - pad:.2f} {y0 - pad:.2f} {w:.2f} {h:.2f}">'
            f'<g fill="{fill}">{paths}</g></svg>')


def render_mark(height, color=(255, 255, 255, 255), scale=4):
    x0, y0, x1, y1 = mark_bounds()
    k = height * scale / (y1 - y0)
    W, H = int((x1 - x0) * k) + 1, int((y1 - y0) * k) + 1
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for _, poly in mark_shapes():
        d.polygon([((x - x0) * k, (y - y0) * k) for x, y in poly], fill=color)
    return im.resize((max(1, W // scale), max(1, H // scale)), Image.LANCZOS)


# ---- text ---------------------------------------------------------------------------
def text_svg_path(font_path, text, size, tracking, x, baseline):
    """Vector outlines of `text`; returns (path_d, width)."""
    f = TTFont(font_path)
    gs, cmap, upm = f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm
    s = size / upm
    d, cx = "", x
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(gs, lambda v: f"{v:.2f}")
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, cx, baseline)))
        d += pen.getCommands()
        cx += gs[name].width * s + tracking
    return d, cx - x - tracking


def text_width(font_path, text, size, tracking):
    f = ImageFont.truetype(font_path, 1000)
    return sum(f.getlength(c) for c in text) * size / 1000 + tracking * (len(text) - 1)


def draw_text(im, font_path, text, size, tracking, cx, baseline, fill):
    f = ImageFont.truetype(font_path, int(size))
    w = text_width(font_path, text, size, tracking)
    x = cx - w / 2
    d = ImageDraw.Draw(im)
    for ch in text:
        d.text((x, baseline), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + tracking


# ---- lockup -------------------------------------------------------------------------
def lockup(color_hex, height_px=None):
    """Stacked lockup: mark, HERMETIKS (Bartle), SOUNDBOARD (Rethink Sans). Returns (svg, png)."""
    mx0, my0, mx1, my1 = mark_bounds()
    mh = 150.0
    k = mh / (my1 - my0)
    mw = (mx1 - mx0) * k
    title_size, sub_size = 74, 27
    title_w = text_width(BARTLE, "HERMETIKS", title_size, 2)
    sub_track = 13
    sub_w = text_width(RETHINK, "SOUNDBOARD", sub_size, sub_track)
    W = max(title_w, mw) + 40
    cx = W / 2
    y_mark = 20
    y_title = y_mark + mh + 34 + title_size * 0.72
    y_sub = y_title + 34 + sub_size * 0.72
    H = y_sub + 20

    # SVG (all outlines, no font dependency)
    shapes = "".join(f'<path d="{d}" transform="translate({cx - mw / 2 - (mx0 * k):.2f},{y_mark - my0 * k:.2f}) scale({k:.4f})"/>'
                     for d, _ in mark_shapes())
    td, _ = text_svg_path(BARTLE, "HERMETIKS", title_size, 2, cx - title_w / 2, y_title)
    sd, _ = text_svg_path(RETHINK, "SOUNDBOARD", sub_size, sub_track, cx - sub_w / 2, y_sub)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}">'
           f'<g fill="{color_hex}">{shapes}<path d="{td}"/><path d="{sd}" opacity="0.72"/></g></svg>')

    # PNG at 4x
    S = 4
    rgb = tuple(int(color_hex[i:i + 2], 16) for i in (1, 3, 5))
    im = Image.new("RGBA", (int(W * S), int(H * S)), (0, 0, 0, 0))
    mk = render_mark(int(mh * S), rgb + (255,), scale=2)
    im.alpha_composite(mk, (int((cx - mk.width / S / 2) * S), int(y_mark * S)))
    draw_text(im, BARTLE, "HERMETIKS", title_size * S, 2 * S, cx * S, y_title * S, rgb + (255,))
    draw_text(im, RETHINK, "SOUNDBOARD", sub_size * S, sub_track * S, cx * S, y_sub * S,
              tuple(int(c * 0.72 + (0 if sum(rgb) > 380 else 255) * 0.28) for c in rgb) + (255,))
    return svg, im


def icon_tile(size, radius=0.2):
    scale = 4
    S = size * scale
    tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(S * radius), fill=(10, 10, 10, 255))
    mk = render_mark(int(S * 0.56), (255, 255, 255, 255), scale=1)
    tile.alpha_composite(mk, ((S - mk.width) // 2, (S - mk.height) // 2))
    return tile.resize((size, size), Image.LANCZOS)


def wizard_images():
    """Bitmaps for the installer wizard (black, brand mark + wordmark)."""
    _, lk = lockup("#ffffff")
    big = Image.new("RGB", (328, 628), (10, 10, 10))
    lk2 = lk.resize((296, int(lk.height * 296 / lk.width)), Image.LANCZOS)
    big.paste(lk2, ((328 - lk2.width) // 2, (628 - lk2.height) // 2 - 40), lk2)
    big.save(os.path.join(INSTALLER, "wizard-large.bmp"))
    small = icon_tile(110, radius=0.0).convert("RGB")
    small.save(os.path.join(INSTALLER, "wizard-small.bmp"))


def main():
    for d in (OUT, RES, INSTALLER):
        os.makedirs(d, exist_ok=True)
    write = lambda n, t: open(os.path.join(OUT, n), "w", encoding="utf-8").write(t)
    write("mark-white.svg", mark_svg("#ffffff", 2))
    write("mark-black.svg", mark_svg("#0a0a0a", 2))
    render_mark(1024, (255, 255, 255, 255)).save(os.path.join(OUT, "mark-white.png"))
    render_mark(1024, (10, 10, 10, 255)).save(os.path.join(OUT, "mark-black.png"))
    for name, col in (("white", "#ffffff"), ("black", "#0a0a0a")):
        svg, png = lockup(col)
        write(f"lockup-{name}.svg", svg)
        png.save(os.path.join(OUT, f"lockup-{name}.png"))
    icon_tile(512).save(os.path.join(OUT, "icon-512.png"))
    ico_sizes = [(s, s) for s in (256, 128, 64, 48, 32, 24, 16)]
    icon_tile(256).save(os.path.join(OUT, "icon.ico"), sizes=ico_sizes)
    # runtime resources shipped inside the app
    icon_tile(256).save(os.path.join(RES, "icon.ico"), sizes=ico_sizes)
    icon_tile(256).save(os.path.join(RES, "icon-256.png"))
    _, white = lockup("#ffffff")
    white.resize((white.width // 2, white.height // 2), Image.LANCZOS).save(os.path.join(RES, "lockup-white.png"))
    wizard_images()
    print("brand kit written:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
