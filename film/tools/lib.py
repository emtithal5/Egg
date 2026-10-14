"""Shared rendering helpers: palette, fonts, Arabic/Latin text, cairo<->PIL, plates, panels, easing."""
import math
import functools
import pathlib
import random

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
W, H, FPS = 1920, 1080, 25
FONTS = ROOT / "assets/fonts"
PLATES = ROOT / "assets/plates"

# ---- palette (from the approved mood board) ----
WOOD = (107, 62, 38)
WOOD_DK = (64, 36, 22)
GOLD = (217, 164, 65)
GOLD_LT = (240, 205, 120)
CREAM = (251, 243, 228)
BEIGE = (233, 214, 182)
ROSE = (217, 140, 154)
ROYAL = (31, 79, 163)
OM_RED = (200, 16, 46)
OM_GREEN = (0, 132, 61)
NIGHT = (24, 14, 30)
INK = (52, 34, 24)
# atom colours (CPK-style as requested: C dark grey, O red, H white)
C_ATOM = (70, 70, 74)
O_ATOM = (226, 60, 60)
H_ATOM = (250, 250, 250)
ALPHA_C = (240, 120, 160)   # alpha-glucose units (pink, as in the mood board)
BETA_C = (90, 160, 235)     # beta-glucose units (blue)
HBOND = (120, 230, 255)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ramp(t, a, b):
    """0 before a, 1 after b, eased in between."""
    if b <= a:
        return 1.0 if t >= a else 0.0
    return ease((t - a) / (b - a))


def window(t, a, b, fade=0.5):
    """Fade in at a, fade out at b."""
    return min(ramp(t, a, a + fade), 1 - ramp(t, b - fade, b))


# ---------------------------------------------------------------- fonts / text
@functools.lru_cache(None)
def font(kind, size):
    files = {
        "naskh": ("NotoNaskhArabic[wght].ttf", "SemiBold"),
        "naskh_b": ("NotoNaskhArabic[wght].ttf", "Bold"),
        "naskh_r": ("NotoNaskhArabic[wght].ttf", "Regular"),
        "kufi": ("ReemKufi[wght].ttf", "Bold"),
        "kufi_m": ("ReemKufi[wght].ttf", "Medium"),
        "amiri": ("Amiri-Bold.ttf", None),
        "amiri_r": ("Amiri-Regular.ttf", None),
    }
    if kind.startswith("inter"):
        name = {"inter": "Inter-SemiBold.otf", "inter_b": "Inter-Bold.otf", "inter_r": "Inter-Regular.otf"}[kind]
        return ImageFont.truetype(f"/usr/share/fonts/opentype/inter/{name}", size, layout_engine=ImageFont.Layout.RAQM)
    fn, var = files[kind]
    f = ImageFont.truetype(str(FONTS / fn), size, layout_engine=ImageFont.Layout.RAQM)
    if var:
        f.set_variation_by_name(var)
    return f


def _is_latin_run(s):
    return any(c in s for c in "αβ→₀₁₂₃₄₅₆₇₈₉ₙ") or (s.strip() and all(ord(c) < 0x590 or c in "αβ→₀₁₂₃₄₅₆₇₈₉ₙ" for c in s))


@functools.lru_cache(maxsize=8192)
def text_img(text, size, color=CREAM, kind="naskh", stroke=0, stroke_color=(0, 0, 0), shadow=False, latin_kind="inter"):
    """Render one line. Segments wrapped in {…} are rendered LTR with the Latin font (for chemistry notation)."""
    runs = []
    buf, latin = "", False
    for ch in text:
        if ch == "{" and not latin:
            if buf:
                runs.append((buf, False))
            buf, latin = "", True
        elif ch == "}" and latin:
            runs.append((buf, True))
            buf, latin = "", False
        else:
            buf += ch
    if buf:
        runs.append((buf, latin))
    pieces = []
    for s, is_lat in runs:
        f = font(latin_kind if is_lat else kind, int(size * (0.86 if is_lat else 1.0)))
        direction = "ltr" if is_lat else "rtl"
        bbox = f.getbbox(s, direction=direction, stroke_width=stroke)
        asc, desc = f.getmetrics()
        w = max(1, bbox[2] - min(0, bbox[0]) + 2 * stroke + 4)
        h = int(size * 1.9)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # baseline-align every run at the same y
        base = int(size * 1.25)
        d.text((stroke + 2 - min(0, bbox[0]), base), s, font=f, fill=color + (255,) if len(color) == 3 else color,
               anchor="ls", direction=direction, stroke_width=stroke, stroke_fill=stroke_color)
        pieces.append(im)
    # logical order is RTL: first run on the right
    total = sum(p.width for p in pieces)
    h = int(size * 1.9)
    out = Image.new("RGBA", (total, h), (0, 0, 0, 0))
    x = total
    for p in pieces:
        x -= p.width
        out.alpha_composite(p, (x, 0))
    bb = out.getbbox() or (0, 0, 1, 1)
    out = out.crop((0, max(0, bb[1] - 4), out.width, min(h, bb[3] + 6)))
    if shadow:
        sh = Image.new("RGBA", (out.width + 24, out.height + 24), (0, 0, 0, 0))
        a = out.split()[3].point(lambda v: int(v * 0.65))
        blk = Image.new("RGBA", out.size, (0, 0, 0, 255))
        blk.putalpha(a)
        sh.alpha_composite(blk, (14, 15))
        sh = sh.filter(ImageFilter.GaussianBlur(5))
        sh.alpha_composite(out, (12, 12))
        out = sh
    return out


@functools.lru_cache(maxsize=4096)
def wrap_words(text, size, max_w, kind="naskh"):
    words = text.split()
    lines, cur = [], ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if cur and text_img(trial, size, kind=kind).width > max_w:
            lines.append(cur)
            cur = w_
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


@functools.lru_cache(maxsize=4096)
def text_block(text, size, max_w, color=CREAM, kind="naskh", align="center", line_gap=0.35, shadow=False, stroke=0):
    lines = wrap_words(text, size, max_w, kind)
    ims = [text_img(l, size, color, kind, shadow=shadow, stroke=stroke) for l in lines]
    lh = int(size * (1 + line_gap)) + (24 if shadow else 0)
    wmax = max(i.width for i in ims)
    out = Image.new("RGBA", (wmax, lh * (len(ims) - 1) + ims[-1].height), (0, 0, 0, 0))
    for k, im in enumerate(ims):
        x = {"center": (wmax - im.width) // 2, "right": wmax - im.width, "left": 0}[align]
        out.alpha_composite(im, (x, k * lh))
    return out


# ---------------------------------------------------------------- cairo bridge
def cairo_layer(w, h, draw, scale=1.0):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))
    ctx = cairo.Context(surf)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    if scale != 1.0:
        ctx.scale(scale, scale)
    draw(ctx)
    surf.flush()
    buf = np.ndarray((int(h), int(w), 4), np.uint8, surf.get_data()).copy()
    b, g, r, a = buf[..., 0].astype(np.float32), buf[..., 1].astype(np.float32), buf[..., 2].astype(np.float32), buf[..., 3]
    af = np.maximum(a.astype(np.float32), 1) / 255.0
    rgba = np.dstack([np.clip(r / af, 0, 255), np.clip(g / af, 0, 255), np.clip(b / af, 0, 255), a]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def rgb(ctx, c, a=1.0):
    ctx.set_source_rgba(c[0] / 255, c[1] / 255, c[2] / 255, a)


def round_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def omani_band(ctx, x, y, w, h):
    """Geometric band inspired by Omani textile borders (red / green / gold diamonds)."""
    rgb(ctx, WOOD_DK)
    ctx.rectangle(x, y, w, h)
    ctx.fill()
    step = h * 1.6
    n = int(w / step) + 1
    for i in range(n):
        cx = x + i * step + step / 2
        cy = y + h / 2
        for k, (col, s) in enumerate([(OM_RED, 0.46), (GOLD, 0.30), (OM_GREEN, 0.14)]):
            rgb(ctx, col)
            ctx.move_to(cx, cy - h * s * 2 * 0.5)
            ctx.line_to(cx + h * s, cy)
            ctx.line_to(cx, cy + h * s * 2 * 0.5)
            ctx.line_to(cx - h * s, cy)
            ctx.close_path()
            ctx.fill()
    rgb(ctx, GOLD)
    ctx.set_line_width(2)
    ctx.move_to(x, y + 1)
    ctx.line_to(x + w, y + 1)
    ctx.move_to(x, y + h - 1)
    ctx.line_to(x + w, y + h - 1)
    ctx.stroke()


# ---------------------------------------------------------------- plates (backgrounds)
@functools.lru_cache(None)
def plate(name, over=1.18):
    im = Image.open(PLATES / f"{name}.png").convert("RGB")
    # cover 16:9 at `over` x the frame size so the camera can move
    tw, th = int(W * over), int(H * over)
    s = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((l, t, l + tw, t + th))
    im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
    return im


def camera(name, p, z0=1.0, z1=1.12, fx0=0.5, fy0=0.5, fx1=0.5, fy1=0.5, over=1.18, blur=0.0, grade=True):
    """Ken Burns move over a plate. p in [0,1]. zoom relative to the frame; f* = focus point (0..1)."""
    src = plate(name, over)
    p = ease(p)
    z = z0 + (z1 - z0) * p
    fx = fx0 + (fx1 - fx0) * p
    fy = fy0 + (fy1 - fy0) * p
    cw, ch = src.width / (z * over) * 1.0, src.height / (z * over)
    cw, ch = min(cw, src.width), min(ch, src.height)
    cx = min(max(fx * src.width, cw / 2), src.width - cw / 2)
    cy = min(max(fy * src.height, ch / 2), src.height - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    im = src.resize((W, H), Image.BILINEAR, box=box)
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im.convert("RGBA")


@functools.lru_cache(None)
def vignette(strength=0.55):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a = np.clip((d - 0.55) / 0.9, 0, 1) ** 1.6 * 255 * strength
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 0], v[..., 1], v[..., 2] = 20, 10, 6
    v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


@functools.lru_cache(None)
def molecular_bg(seed=3):
    """Dark 'molecular world' stage: plum-to-night gradient with soft bokeh particles."""
    def draw(ctx):
        g = cairo.RadialGradient(W * 0.5, H * 0.45, 80, W * 0.5, H * 0.5, W * 0.75)
        g.add_color_stop_rgb(0, 0.20, 0.10, 0.22)
        g.add_color_stop_rgb(0.6, 0.10, 0.05, 0.13)
        g.add_color_stop_rgb(1, 0.04, 0.02, 0.06)
        ctx.set_source(g)
        ctx.paint()
        rnd = random.Random(seed)
        for _ in range(140):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.5, 9)
            col = rnd.choice([GOLD_LT, ROSE, (160, 140, 230), (255, 255, 255)])
            gg = cairo.RadialGradient(x, y, 0, x, y, r * 2.2)
            gg.add_color_stop_rgba(0, col[0] / 255, col[1] / 255, col[2] / 255, rnd.uniform(0.15, 0.45))
            gg.add_color_stop_rgba(1, col[0] / 255, col[1] / 255, col[2] / 255, 0)
            ctx.set_source(gg)
            ctx.arc(x, y, r * 2.2, 0, 2 * math.pi)
            ctx.fill()
    return cairo_layer(W, H, draw)


def molecular_frame(t, drift=True):
    bg = molecular_bg()
    if not drift:
        return bg.copy()
    # slow parallax drift so the stage never looks frozen
    z = 1.04 + 0.02 * math.sin(t * 0.15)
    dx = 18 * math.sin(t * 0.11)
    dy = 10 * math.cos(t * 0.09)
    cw, ch = W / z, H / z
    box = (W / 2 - cw / 2 + dx, H / 2 - ch / 2 + dy, W / 2 + cw / 2 + dx, H / 2 + ch / 2 + dy)
    return bg.resize((W, H), Image.BILINEAR, box=box)


# ---------------------------------------------------------------- compositing helpers
def with_alpha(im, a):
    if a >= 0.999:
        return im
    if a <= 0.001:
        return None
    im = im.copy()
    al = im.getchannel("A").point(lambda v: int(v * a))
    im.putalpha(al)
    return im


def paste(canvas, im, x, y, a=1.0, anchor="c", scale=1.0):
    """Alpha-composite im onto canvas. anchor: c (centre), tl, tr, bc, ..."""
    if im is None or a <= 0.001:
        return
    if abs(scale - 1.0) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    im = with_alpha(im, a)
    if im is None:
        return
    w, h = im.size
    ox = {"c": w / 2, "tl": 0, "tr": w, "bc": w / 2, "tc": w / 2, "cl": 0, "cr": w, "bl": 0, "br": w}[anchor]
    oy = {"c": h / 2, "tl": 0, "tr": 0, "bc": h, "tc": 0, "cl": h / 2, "cr": h / 2, "bl": h, "br": h}[anchor]
    x0, y0 = int(round(x - ox)), int(round(y - oy))
    # clip to canvas
    cl, ct = max(0, -x0), max(0, -y0)
    cr, cb = min(w, canvas.width - x0), min(h, canvas.height - y0)
    if cr <= cl or cb <= ct:
        return
    if (cl, ct, cr, cb) != (0, 0, w, h):
        im = im.crop((cl, ct, cr, cb))
    canvas.alpha_composite(im, (x0 + cl, y0 + ct))


def shade(canvas, a, color=(15, 8, 5)):
    if a <= 0:
        return canvas
    ov = Image.new("RGBA", canvas.size, color + (int(255 * a),))
    canvas.alpha_composite(ov)
    return canvas


# ---------------------------------------------------------------- UI pieces
@functools.lru_cache(None)
def wood_sign(text, size=64, pad=48, kind="kufi"):
    """Wooden bakery-style sign with gold lettering (Canva-style title board, rendered here)."""
    t = text_img(text, size, GOLD_LT, kind)
    w, h = t.width + pad * 2, t.height + pad
    def draw(ctx):
        round_rect(ctx, 6, 6, w - 12, h - 12, 22)
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0, 0.52, 0.31, 0.18)
        g.add_color_stop_rgb(1, 0.33, 0.19, 0.11)
        ctx.set_source(g)
        ctx.fill_preserve()
        rgb(ctx, GOLD)
        ctx.set_line_width(4)
        ctx.stroke()
        round_rect(ctx, 16, 16, w - 32, h - 32, 16)
        rgb(ctx, GOLD, 0.45)
        ctx.set_line_width(1.5)
        ctx.stroke()
        # wood grain
        rnd = random.Random(len(text))
        for _ in range(9):
            yy = rnd.uniform(20, h - 20)
            rgb(ctx, (40, 20, 10), 0.18)
            ctx.set_line_width(1.2)
            ctx.move_to(24, yy)
            ctx.curve_to(w * 0.3, yy + rnd.uniform(-6, 6), w * 0.7, yy + rnd.uniform(-6, 6), w - 24, yy)
            ctx.stroke()
    board = cairo_layer(w, h, draw)
    board.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    return add_shadow(board, 10, 0.5)


def add_shadow(im, r=12, a=0.45, off=(0, 8)):
    pad = r * 3
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    blk = Image.new("RGBA", im.size, (0, 0, 0, 255))
    blk.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    out.alpha_composite(blk, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(r))
    out.alpha_composite(im, (pad, pad))
    return out


@functools.lru_cache(None)
def card(w, h, fill=CREAM, alpha=0.93, border=GOLD, radius=26, band=True):
    def draw(ctx):
        round_rect(ctx, 4, 4, w - 8, h - 8, radius)
        rgb(ctx, fill, alpha)
        ctx.fill_preserve()
        rgb(ctx, border)
        ctx.set_line_width(4)
        ctx.stroke()
        if band:
            ctx.save()
            round_rect(ctx, 4, 4, w - 8, h - 8, radius)
            ctx.clip()
            omani_band(ctx, 0, 4, w, 22)
            ctx.restore()
    return add_shadow(cairo_layer(w, h, draw), 14, 0.45)


@functools.lru_cache(None)
def glass(w, h, radius=28, tint=(30, 16, 34), alpha=0.72, border=GOLD):
    def draw(ctx):
        round_rect(ctx, 3, 3, w - 6, h - 6, radius)
        rgb(ctx, tint, alpha)
        ctx.fill_preserve()
        rgb(ctx, border, 0.85)
        ctx.set_line_width(2.5)
        ctx.stroke()
    return cairo_layer(w, h, draw)


@functools.lru_cache(None)
def chef_frame(name, w=520, h=600, label="الشيف رقية"):
    """Approved illustrated Chef Ruqayya (from the mood board) in a carved gold frame with a name tag."""
    src = Image.open(PLATES / f"{name}.png").convert("RGB")
    s = max(w / src.width, h / src.height)
    src = src.resize((int(src.width * s) + 1, int(src.height * s) + 1), Image.LANCZOS)
    l = (src.width - w) // 2
    src = src.crop((l, 0, l + w, h)).filter(ImageFilter.UnsharpMask(2, 60, 2)).convert("RGBA")
    mask = cairo_layer(w, h, lambda c: (round_rect(c, 0, 0, w, h, 34), c.set_source_rgb(1, 1, 1), c.fill()))
    src.putalpha(mask.getchannel("A"))
    out = Image.new("RGBA", (w + 24, h + 70), (0, 0, 0, 0))
    def frame(ctx):
        round_rect(ctx, 4, 4, w + 16, h + 16, 38)
        rgb(ctx, GOLD)
        ctx.set_line_width(7)
        ctx.stroke()
        round_rect(ctx, 13, 13, w - 2, h - 2, 32)
        rgb(ctx, WOOD_DK)
        ctx.set_line_width(2)
        ctx.stroke()
    out.alpha_composite(src, (12, 12))
    out.alpha_composite(cairo_layer(w + 24, h + 24, frame), (0, 0))
    tag = wood_sign(label, 34, 26)
    out.alpha_composite(tag, ((out.width - tag.width) // 2, out.height - tag.height + 8))
    return add_shadow(out, 16, 0.5)


def scene_title(text):
    """Small title plaque, top-right (RTL reading start)."""
    return wood_sign(text, 40, 30)


# ---------------------------------------------------------------- subtitles
SPEAKER = {"chef": ("الشيف رقية", GOLD_LT), "narr": ("الراوية", (190, 210, 255))}


@functools.lru_cache(None)
def subtitle_img(text, who):
    size = 40
    body = text_block(text, size, 1120, CREAM, "naskh", line_gap=0.28)
    name, col = SPEAKER[who]
    tag = text_img(name, 24, col, "naskh_b")
    w = max(body.width, tag.width) + 70
    h = body.height + tag.height + 40
    bg = glass(w, h, 22, (14, 8, 10), 0.66, GOLD)
    out = bg.copy()
    out.alpha_composite(tag, (w - tag.width - 30, 12))
    out.alpha_composite(body, ((w - body.width) // 2, tag.height + 22))
    return out


def strip_harakat(s):
    return "".join(ch for ch in s if not ("ً" <= ch <= "ْ" or ch == "ٰ"))


def split_subs(text, max_chars=95):
    """Split a cue into subtitle chunks at sentence / clause boundaries."""
    import re
    clean = strip_harakat(re.sub(r"\[[^\]]*\]", "", text)).strip()
    parts = re.split(r"(?<=[\.\!\؟\?؛:…])\s+", clean)
    chunks = []
    for p in parts:
        while len(p) > max_chars:
            cut = p.rfind("،", 0, max_chars)
            cut = cut if cut > 30 else p.rfind(" ", 0, max_chars)
            chunks.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            chunks.append(p)
    return chunks
