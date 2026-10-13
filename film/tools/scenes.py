"""The 14 scenes of 'مخبز الطاقة'. Each scene draws one frame for time t (seconds from scene start).

Timing object T gives the start/end of every voice cue, so visuals are locked to the real ElevenLabs audio.
"""
import functools
import math
import random

import cairo
from PIL import Image

from lib import (ALPHA_C, BEIGE, BETA_C, C_ATOM, CREAM, GOLD, GOLD_LT, H, H_ATOM, HBOND, INK, O_ATOM, OM_GREEN,
                 OM_RED, ROSE, ROYAL, W, WOOD, WOOD_DK, add_shadow, cairo_layer, camera, card, chef_frame, ease,
                 ease_out, glass, molecular_frame, paste, ramp, rgb, round_rect, shade, text_block, text_img,
                 vignette, window, wood_sign)
import chem
from chem import (FRUCTOSE_ROWS, GALACTOSE_ROWS, GLUCOSE_ROWS, ERYTHROSE_ROWS, GLYCERALDEHYDE_ROWS, RIBOSE_ROWS,
                  atom_ball, fischer, fructose_in_sucrose, glyco_link, group, haworth, token)


# ----------------------------------------------------------------------------- small helpers
def T_(s, size=44, color=CREAM, kind="naskh", shadow=True):
    return text_img(s, size, color, kind, shadow=shadow)


@functools.lru_cache(None)
def label_chip(s, size=36, fg=CREAM, bg=(40, 22, 30), border=GOLD):
    t = text_img(s, size, fg, "naskh")
    w, h = t.width + 56, t.height + 30
    out = glass(w, h, h // 2 - 2, bg, 0.82, border).copy()
    out.alpha_composite(t, ((w - t.width) // 2, (h - t.height) // 2))
    return out


def layer(draw, w=W, h=H):
    return cairo_layer(w, h, draw)


def cue_p(t, T, cid, a=0.0, b=1.0):
    """Eased progress between fractions a..b of cue cid."""
    s, e = T.start(cid), T.end(cid)
    d = e - s
    return ramp(t, s + a * d, s + b * d)


def at(T, cid, f):
    return T.start(cid) + f * (T.end(cid) - T.start(cid))


def chef_in(canvas, t, T, cids, name="chef_spoon", x=1580, y=560, w=430, h=520, side="right"):
    """Show the chef frame while any of cids is spoken (plus a small margin)."""
    a = 0.0
    for c in cids:
        a = max(a, window(t, T.start(c) - 0.6, T.end(c) + 0.8, 0.6))
    if a <= 0:
        return
    dx = (1 - a) * (140 if side == "right" else -140)
    bob = 4 * math.sin(t * 1.3)
    paste(canvas, chef_frame(name, w, h), x + dx, y + bob, a)


def title_plaque(canvas, t, D, text):
    a = window(t, 0.4, D - 0.3, 0.6)
    paste(canvas, wood_sign(text, 38, 28), W - 30, 26, a, "tr")


def heading(canvas, s, a, y=150, size=58, color=GOLD_LT):
    paste(canvas, T_(s, size, color, "kufi"), W / 2, y, a)


def arrow(ctx, a, b, col=GOLD_LT, w=5, head=18, alpha=1.0, curve=0.0):
    rgb(ctx, col, alpha)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    nx, ny = -(b[1] - a[1]), b[0] - a[0]
    cx, cy = mx + nx * curve, my + ny * curve
    ctx.move_to(*a)
    ctx.curve_to(cx, cy, cx, cy, *b)
    ctx.stroke()
    ang = math.atan2(b[1] - cy, b[0] - cx)
    ctx.move_to(*b)
    ctx.line_to(b[0] - head * math.cos(ang - 0.45), b[1] - head * math.sin(ang - 0.45))
    ctx.line_to(b[0] - head * math.cos(ang + 0.45), b[1] - head * math.sin(ang + 0.45))
    ctx.close_path()
    ctx.fill()


def flash(canvas, a, color=(255, 236, 190)):
    if a > 0:
        shade(canvas, min(0.95, a), color)


def glow_spot(canvas, x, y, r, col, a):
    if a <= 0:
        return
    def d(ctx):
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0, col[0] / 255, col[1] / 255, col[2] / 255, 0.8 * a)
        g.add_color_stop_rgba(1, col[0] / 255, col[1] / 255, col[2] / 255, 0)
        ctx.set_source(g)
        ctx.paint()
    paste(canvas, _glow_cache(int(r), col), x, y, a)


@functools.lru_cache(None)
def _glow_cache(r, col):
    def d(ctx):
        g = cairo.RadialGradient(r, r, 0, r, r, r)
        g.add_color_stop_rgba(0, col[0] / 255, col[1] / 255, col[2] / 255, 0.85)
        g.add_color_stop_rgba(1, col[0] / 255, col[1] / 255, col[2] / 255, 0)
        ctx.set_source(g)
        ctx.paint()
    return cairo_layer(2 * r, 2 * r, d)


def xfade(t, t0, d=0.8):
    return ramp(t, t0, t0 + d)


# ----------------------------------------------------------------------------- scene 1
def s01(t, T):
    D = T.D
    # drone over the fort -> gate -> gate opens -> souq tracking -> bakery sign -> chef
    k1 = T.start("s01_01") + 6.5        # cut to gate
    k2 = T.start("s01_01") + 9.5        # gate opens (door sfx)
    k3 = T.start("s01_01") + 11.5       # souq tracking
    k4 = T.start("s01_02") - 1.4        # bakery sign
    k5 = T.start("s01_02") + 1.4        # chef close-up
    if t < k1 + 0.8:
        im = camera("fort_wide", t / (k1 + 0.8), 1.0, 1.32, 0.5, 0.45, 0.47, 0.62)
        if t > k1:
            im = Image.blend(im, camera("castle", 0, 1.05, 1.4, 0.5, 0.6, 0.5, 0.66), xfade(t, k1))
    elif t < k3 + 0.8:
        p = (t - k1) / (k3 + 0.8 - k1)
        im = camera("castle", p, 1.05, 1.55, 0.5, 0.6, 0.5, 0.68)
        if t > k3:
            im = Image.blend(im, camera("env_souq", 0, 1.15, 1.15, 0.25, 0.55, 0.75, 0.55), xfade(t, k3))
    elif t < k4 + 0.8:
        p = (t - k3) / (k4 + 0.8 - k3)
        im = camera("env_souq", p, 1.15, 1.22, 0.25, 0.55, 0.75, 0.55)
        if t > k4:
            im = Image.blend(im, camera("b_tools", 0, 1.0, 1.1, 0.5, 0.5, 0.5, 0.45), xfade(t, k4))
    elif t < k5 + 0.8:
        p = (t - k4) / (k5 + 0.8 - k4)
        im = camera("b_tools", p, 1.0, 1.1, 0.5, 0.5, 0.5, 0.45)
        if t > k5:
            im = Image.blend(im, camera("chef_hero", 0, 1.0, 1.2, 0.5, 0.45, 0.56, 0.35), xfade(t, k5))
    else:
        p = (t - k5) / max(1, D - k5)
        im = camera("chef_hero", p, 1.0, 1.2, 0.5, 0.45, 0.56, 0.35)
    im.alpha_composite(vignette())
    # golden light pouring from the opening gate
    ga = window(t, k2 - 0.2, k3 + 0.6, 0.9)
    if ga > 0:
        glow_spot(im, W / 2, H * 0.62, 520 + 300 * ramp(t, k2, k3), (255, 214, 140), ga)
    # hanging bakery sign
    sa = window(t, k4 + 0.3, k5 + 1.0, 0.5)
    if sa > 0:
        drop = (1 - ease_out((t - k4 - 0.3) / 0.9)) * -220
        swing = 2.5 * math.sin((t - k4) * 3.0) * math.exp(-(t - k4) * 0.7)
        sign = wood_sign("مخبز الطاقة", 92, 60)
        paste(im, sign.rotate(swing, Image.BICUBIC, expand=True), W / 2, 300 + drop, sa)
    # main title badge
    ta = ramp(t, T.end("s01_02") - 3.5, T.end("s01_02") - 2.0)
    if ta > 0:
        shade(im, 0.25 * ta)
        paste(im, glass(1060, 470, 34, (24, 12, 10), 0.72), 560, 560, ta)
        paste(im, wood_sign("مخبز الطاقة", 96, 64), 560, 440, ta, scale=0.9 + 0.1 * ta)
        paste(im, T_("أسرار الكربوهيدرات", 62, GOLD_LT, "kufi"), 560, 590, ta)
        paste(im, T_("من السكر البسيط إلى التخزين والبناء", 44, CREAM, "kufi_m"), 560, 670, ta)
        paste(im, T_("الوحدة الثانية: الجزيئات الحيوية  •  الدرس ٢-٢", 32, BEIGE, "naskh"), 560, 745, ta)
    return im


# ----------------------------------------------------------------------------- scene 2
FOODS = ["تمر", "خبز", "أرز", "بطاطس", "سكر"]


def s02(t, T):
    D = T.D
    k_mol = T.start("s02_02") - 0.4
    if t < k_mol + 0.8:
        im = camera("b_ingred", t / (k_mol + 0.8), 1.0, 1.15, 0.5, 0.55, 0.4, 0.6)
        im.alpha_composite(vignette())
        chef_in(im, t, T, ["s02_01"], "chef_spoon", 1560, 560)
        for i, f in enumerate(FOODS):
            a = window(t, at(T, "s02_01", 0.12 + i * 0.1), k_mol + 0.6, 0.4)
            paste(im, label_chip(f, 44), 260 + i * 0.0, 230 + i * 120, a, "cl")
        ca = window(t, at(T, "s02_01", 0.72), k_mol + 0.6, 0.4)
        paste(im, wood_sign("الكربوهيدرات", 64, 44), 760, 520, ca, scale=0.85 + 0.15 * ca)
        if t > k_mol:
            mf = molecular_frame(t)
            im = Image.blend(im, mf, xfade(t, k_mol))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "ما الكربوهيدرات؟")
    # --- C, H, O
    p2 = "s02_02"
    a_atoms = window(t, T.start(p2), T.start("s02_03") + 0.4, 0.5)
    if a_atoms > 0:
        names = [("C", C_ATOM, "كربون"), ("H", H_ATOM, "هيدروجين"), ("O", O_ATOM, "أكسجين")]
        for i, (sym, col, nm) in enumerate(names):
            ai = a_atoms * ramp(t, at(T, p2, 0.12 + i * 0.12), at(T, p2, 0.2 + i * 0.12))
            x = 1380 - i * 300
            ball = _ball(sym, col, 90)
            paste(im, ball, x, 380, ai, scale=0.6 + 0.4 * ease_out(ai))
            paste(im, T_(nm, 42), x, 510, ai)
        aw = a_atoms * ramp(t, at(T, p2, 0.55), at(T, p2, 0.68))
        paste(im, _water(), 560, 700, aw)
        paste(im, T_("{H : O  =  2 : 1}", 54, GOLD_LT), 1180, 700, aw)
        paste(im, T_("كما في الماء  {H₂O}", 40), 560, 830, aw)
    # --- general formula
    p3 = "s02_03"
    af = window(t, T.start(p3), T.start("s02_04") + 0.3, 0.5)
    if af > 0:
        paste(im, T_("الصيغة العامة الشائعة", 46, CREAM, "kufi_m"), W / 2, 240, af)
        paste(im, T_("{(CH₂O)ₙ   =   Cₙ(H₂O)ₙ}", 96, GOLD_LT), W / 2, 380, af * ramp(t, at(T, p3, 0.05), at(T, p3, 0.15)))
        aw = af * ramp(t, at(T, p3, 0.42), at(T, p3, 0.52))
        paste(im, card(1240, 330), W / 2, 700, aw)
        paste(im, T_("تنبيه: لا تنطبق على جميع الكربوهيدرات", 46, OM_RED, "naskh_b", shadow=False), W / 2, 610, aw)
        ad = af * ramp(t, at(T, p3, 0.68), at(T, p3, 0.78))
        paste(im, T_("الديوكسي ريبوز:  {C₅H₁₀O₄}", 50, INK, "naskh", shadow=False), W / 2, 700, ad)
        paste(im, T_("وليست  {C₅H₁₀O₅}  كما تتوقع الصيغة العامة", 38, WOOD, "naskh", shadow=False), W / 2, 785, ad)
    # --- three doors
    p4 = "s02_04"
    ad = window(t, T.start(p4) - 0.2, D, 0.6)
    if ad > 0:
        heading(im, "ثلاث مجموعات رئيسية", ad, 170)
        names = [("السكريات الأحادية", 1), ("السكريات الثنائية", 2), ("عديدات التسكر", 6)]
        for i, (nm, n) in enumerate(names):
            ai = ad * ramp(t, at(T, p4, 0.3 + i * 0.18), at(T, p4, 0.4 + i * 0.18))
            x = 1440 - i * 480
            paste(im, _door(n), x, 560, ai, scale=0.85 + 0.15 * ai)
            paste(im, T_(nm, 44, GOLD_LT, "kufi_m"), x, 860, ai)
    return im


@functools.lru_cache(None)
def _ball(sym, col, r):
    return layer(lambda c: atom_ball(c, r + 4, r + 4, r, col, sym), 2 * r + 8, 2 * r + 8)


@functools.lru_cache(None)
def _water():
    def d(c):
        chem.line(c, (150, 110), (70, 170), 6)
        chem.line(c, (150, 110), (230, 170), 6)
        atom_ball(c, 150, 110, 52, O_ATOM, "O")
        atom_ball(c, 70, 170, 34, H_ATOM, "H")
        atom_ball(c, 230, 170, 34, H_ATOM, "H")
    return layer(d, 300, 220)


@functools.lru_cache(None)
def _door(n):
    """Omani arched wooden door with n glucose tokens inside."""
    w, h = 340, 480
    def d(c):
        c.move_to(20, h - 10)
        c.line_to(20, 170)
        c.curve_to(20, 40, w / 2 - 40, 10, w / 2, 10)
        c.curve_to(w / 2 + 40, 10, w - 20, 40, w - 20, 170)
        c.line_to(w - 20, h - 10)
        c.close_path()
        g = cairo.LinearGradient(0, 0, w, 0)
        g.add_color_stop_rgb(0, 0.36, 0.2, 0.11)
        g.add_color_stop_rgb(0.5, 0.52, 0.31, 0.17)
        g.add_color_stop_rgb(1, 0.36, 0.2, 0.11)
        c.set_source(g)
        c.fill_preserve()
        rgb(c, GOLD)
        c.set_line_width(7)
        c.stroke()
        # studs
        for yy in range(200, h - 20, 52):
            for xx in (50, w - 50):
                rgb(c, GOLD_LT)
                c.arc(xx, yy, 6, 0, 2 * math.pi)
                c.fill()
        # glowing window with tokens
        round_rect(c, 70, 150, w - 140, 230, 26)
        rgb(c, (20, 10, 24), 0.85)
        c.fill()
        if n == 1:
            token(c, w / 2, 265, 46, ALPHA_C)
        elif n == 2:
            token(c, w / 2 - 50, 265, 38, ALPHA_C)
            chem.line(c, (w / 2 - 12, 265), (w / 2 + 12, 265), 5, GOLD)
            token(c, w / 2 + 50, 265, 38, ROSE)
        else:
            for k in range(5):
                xx = 98 + k * 36
                yy = 265 + 22 * math.sin(k * 1.2)
                if k:
                    chem.line(c, (xx - 36, 265 + 22 * math.sin((k - 1) * 1.2)), (xx, yy), 4, GOLD)
            for k in range(5):
                token(c, 98 + k * 36, 265 + 22 * math.sin(k * 1.2), 17, ALPHA_C, glow=False)
    return add_shadow(layer(d, w, h), 14, 0.5)


# ----------------------------------------------------------------------------- scene 3
def s03(t, T):
    D = T.D
    k_zoom = T.end("s03_01") - 1.6
    k_mol = T.end("s03_01") + 0.2
    if t < k_mol + 0.6:
        z1 = 1.1 + 2.2 * ramp(t, k_zoom, k_mol + 0.4) ** 2
        im = camera("b_ingred", t / (k_mol + 0.6), 1.0, z1, 0.5, 0.55, 0.78, 0.8,
                    blur=6 * ramp(t, k_zoom + 0.6, k_mol + 0.3))
        im.alpha_composite(vignette())
        chef_in(im, t, T, ["s03_01"], "chef_spoon", 1580, 560)
        flash(im, window(t, k_mol - 0.4, k_mol + 0.6, 0.35))
        if t > k_mol:
            im = Image.blend(im, molecular_frame(t), xfade(t, k_mol, 0.6))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "السكريات الأحادية")
    p = "s03_02"
    a = window(t, T.start(p), T.start("s03_03") + 0.2, 0.5)
    if a > 0:
        paste(im, _single_token(), W / 2, 420, a, scale=0.8 + 0.2 * a + 0.03 * math.sin(t * 2))
        props = ["حلوة المذاق", "تذوب بسهولة في الماء", "جزيء سكر مفرد"]
        for i, s in enumerate(props):
            ai = a * ramp(t, at(T, p, 0.12 + i * 0.25), at(T, p, 0.2 + i * 0.25))
            paste(im, label_chip(s, 44), 1460 - i * 520, 760, ai)
    p = "s03_03"
    a = window(t, T.start(p) - 0.2, T.start("s03_04") + 0.2, 0.5)
    if a > 0:
        heading(im, "التصنيف حسب عدد ذرات الكربون", a, 150)
        items = [("ثلاثي الكربون", "جليسرالدهيد", GLYCERALDEHYDE_ROWS, "3C", 0.10),
                 ("رباعي الكربون", "إريثروز", ERYTHROSE_ROWS, "4C", 0.30),
                 ("خماسي الكربون", "ريبوز", RIBOSE_ROWS, "5C", 0.48),
                 ("سداسي الكربون", "جلوكوز", GLUCOSE_ROWS, "6C", 0.66)]
        for i, (cls, nm, rows, badge, f) in enumerate(items):
            ai = a * ramp(t, at(T, p, f), at(T, p, f + 0.07))
            x = 1600 - i * 430
            paste(im, label_chip(cls, 36, GOLD_LT), x, 260, ai)
            paste(im, _fischer_small(tuple(rows)), x, 300, ai, "tc")
            paste(im, T_(nm, 40), x, 300 + 90 + (len(rows) + 2) * 93, ai)
        af = a * ramp(t, at(T, p, 0.86), at(T, p, 0.93))
        paste(im, label_chip("الفركتوز والجالاكتوز: سداسية الكربون أيضًا", 34), 460, 920, af)
    p = "s03_04"
    a = window(t, T.start(p) - 0.2, D, 0.5)
    if a > 0:
        a1 = a * (1 - ramp(t, at(T, p, 0.6), at(T, p, 0.66)))
        paste(im, T_("{C₆H₁₂O₆}", 120, GOLD_LT), W / 2, 260, a1)
        rows = [(6, C_ATOM, "C", "٦ ذرات كربون", 0.18), (12, H_ATOM, "H", "١٢ ذرة هيدروجين", 0.28), (6, O_ATOM, "O", "٦ ذرات أكسجين", 0.4)]
        for j, (n, col, sym, nm, f) in enumerate(rows):
            aj = a1 * ramp(t, at(T, p, f), at(T, p, f + 0.06))
            y = 440 + j * 150
            paste(im, T_(nm, 40), 1560, y, aj, "cr")
            for k in range(n):
                ak = aj * ramp(t, at(T, p, f) + k * 0.06, at(T, p, f) + k * 0.06 + 0.3)
                paste(im, _ball(sym, col, 30 if sym != "H" else 24), 1100 - k * 66, y, ak)
        a2 = a * ramp(t, at(T, p, 0.62), at(T, p, 0.7))
        if a2 > 0:
            heading(im, "الصيغة نفسها {C₆H₁₂O₆} ... وترتيب مختلف للذرات", a2, 160, 50)
            trio = [("جلوكوز", GLUCOSE_ROWS, "CHO", (), 1460), ("فركتوز", FRUCTOSE_ROWS, "CH2OH", (1,), 960),
                    ("جالاكتوز", GALACTOSE_ROWS, "CHO", (3,), 460)]
            for k, (nm, rows, top, hl, x) in enumerate(trio):
                ak = a2 * ramp(t, at(T, p, 0.66 + k * 0.06), at(T, p, 0.72 + k * 0.06))
                paste(im, T_(nm, 46, GOLD_LT, "kufi_m"), x, 260, ak)
                paste(im, _fischer_big(tuple(rows), top, hl), x, 310, ak, "tc")
    return im


@functools.lru_cache(None)
def _single_token():
    return layer(lambda c: token(c, 150, 150, 90, ALPHA_C), 300, 300)


@functools.lru_cache(None)
def _fischer_small(rows):
    s = 150
    h = int((len(rows) + 2) * s * 0.62 + 80)
    return layer(lambda c: fischer(c, 200, 40, list(rows), s), 400, h)


@functools.lru_cache(None)
def _fischer_big(rows, top, hl):
    s = 140
    h = int((len(rows) + 2) * s * 0.62 + 90)
    return layer(lambda c: fischer(c, 200, 45, list(rows), s, top=top, highlight_rows=hl), 400, h)


# ----------------------------------------------------------------------------- scene 4
def s04(t, T):
    D = T.D
    im = molecular_frame(t)
    title_plaque(im, t, D, "من الخطي إلى الحلقي")
    p1, p2, p3 = "s04_01", "s04_02", "s04_03"
    # Fischer projection (stays during the folding explanation)
    af = window(t, 0.3, T.start(p2) + 0.65 * (T.end(p2) - T.start(p2)), 0.6)
    fx = 760 if t < T.start(p2) else 760 - 260 * ramp(t, T.start(p2), at(T, p2, 0.2))
    if af > 0:
        hl = []
        if t > at(T, p1, 0.42):
            hl.append(0)
        paste(im, _fischer_glc_big(tuple(hl)), fx, 140, af, "tc")
        aa = af * window(t, at(T, p1, 0.42), T.start(p2), 0.4)
        paste(im, label_chip("C1: مجموعة الألدهيد {CHO}", 38, GOLD_LT), fx + 520, 210, aa)
        ao = af * window(t, at(T, p1, 0.68), T.start(p2), 0.4)
        if ao > 0:
            pulse = 0.5 + 0.5 * math.sin(t * 5)
            for k in range(1, 5):
                glow_spot(im, fx + 125 if k != 2 else fx - 125, 140 + 45 + k * 112, 70, HBOND, ao * (0.5 + 0.4 * pulse))
            paste(im, label_chip("مجموعات الهيدروكسيل {OH}", 38, (180, 235, 255)), fx + 520, 520, ao)
        ac = af * window(t, at(T, p1, 0.2), T.start(p2), 0.4)
        paste(im, label_chip("سلسلة من ٦ ذرات كربون مرقّمة من الأعلى", 34), fx - 330, 300, ac, "cr")
        # folding cue: highlight C1 and the O on C5, curved arrow
        ak = af * ramp(t, at(T, p2, 0.25), at(T, p2, 0.4))
        if ak > 0:
            glow_spot(im, fx, 185, 90, GOLD, ak)
            glow_spot(im, fx + 125, 140 + 45 + 4 * 112, 90, O_ATOM, ak)
            arr = layer(lambda c: arrow(c, (fx + 200, 140 + 45 + 4 * 112), (fx + 90, 200), GOLD_LT, 6, 22, 1, curve=-0.45))
            paste(im, arr, W / 2, H / 2, ak * ramp(t, at(T, p2, 0.32), at(T, p2, 0.45)))
            paste(im, label_chip("ترتبط C1 بذرة الأكسجين المتصلة بـ C5", 36, GOLD_LT), fx + 560, 700, ak)
    # ring
    ar = ramp(t, at(T, p2, 0.62), at(T, p2, 0.8))
    if ar > 0:
        x = 1340 if t < T.start(p3) else 1340 - 380 * ramp(t, T.start(p3), at(T, p3, 0.1))
        paste(im, _haworth_big("a", True), x, 470, ar, scale=0.75 + 0.25 * ar)
        a3 = ramp(t, at(T, p3, 0.05), at(T, p3, 0.15))
        if a3 > 0:
            s = 190
            cx, cy = x, 470
            # glowing ring carbons 1..5 in sequence, ring O, C6
            for k, key in enumerate(["C1", "C2", "C3", "C4", "C5"]):
                ak = a3 * window(t, at(T, p3, 0.08 + k * 0.05), at(T, p3, 0.95), 0.25)
                px, py = chem.PYR[key]
                glow_spot(im, cx + px * s, cy + py * s, 60, GOLD, ak * 0.8)
            ao = a3 * ramp(t, at(T, p3, 0.38), at(T, p3, 0.45))
            px, py = chem.PYR["O5"]
            glow_spot(im, cx + px * s, cy + py * s, 80, O_ATOM, ao)
            a6 = a3 * ramp(t, at(T, p3, 0.52), at(T, p3, 0.6))
            px, py = chem.PYR["C5"]
            glow_spot(im, cx + px * s, cy + py * s - 0.6 * s - 30, 90, HBOND, a6)
            paste(im, label_chip("٥ ذرات كربون داخل الحلقة", 38, GOLD_LT), 1500, 330, ramp(t, at(T, p3, 0.1), at(T, p3, 0.2)))
            paste(im, label_chip("ذرة أكسجين واحدة في الحلقة", 38, (255, 170, 170)), 1500, 460, ao)
            paste(im, label_chip("ذرة الكربون ٦ خارج الحلقة", 38, (180, 235, 255)), 1500, 590, a6)
            paste(im, label_chip("في الخلايا الحية: الشكل الحلقي هو الغالب", 36), 1500, 760,
                  ramp(t, at(T, p3, 0.72), at(T, p3, 0.8)))
    return im


@functools.lru_cache(None)
def _fischer_glc_big(hl):
    s = 180
    return layer(lambda c: fischer(c, 260, 45, GLUCOSE_ROWS, s, highlight_rows=hl, hl_col=GOLD), 520, 800)


@functools.lru_cache(None)
def _haworth_big(anomer, show_H, sugar="glc", s=190, glow=None, hl=()):
    w, h = int(s * 3.4), int(s * 2.9)
    return layer(lambda c: haworth(c, w / 2, h / 2, s, sugar, anomer, show_H=show_H, glow=glow, highlight=hl), w, h)


# ----------------------------------------------------------------------------- scene 5
def s05(t, T):
    D = T.D
    im = molecular_frame(t)
    title_plaque(im, t, D, "ألفا وبيتا جلوكوز")
    p1, p2, p3 = "s05_01", "s05_02", "s05_03"
    a = window(t, 0.2, at(T, p3, 0.55), 0.6)
    hl = ("C1_down",) if True else ()
    zoom = 1.0 + 0.18 * window(t, T.start(p2), T.end(p2) + 0.3, 1.0)
    if a > 0:
        xa, xb = 1340, 580
        if t < T.end(p1) + 0.6:
            xa, xb = 1080 - 0, 420
        else:
            k = ramp(t, T.end(p1) + 0.4, T.end(p1) + 1.4)
            xa, xb = 1080 + (1380 - 1080) * k, 420 + (560 - 420) * k
        pulse = 0.6 + 0.4 * math.sin(t * 4)
        for x, anom, nm, col in ((xa, "a", "ألفا جلوكوز  {α}", ALPHA_C), (xb, "b", "بيتا جلوكوز  {β}", BETA_C)):
            mol = _haworth_big(anom, True, "glc", 170, col, ("C1_down",) if anom == "a" else ("C1_up",))
            paste(im, mol, x, 480, a, scale=zoom)
            paste(im, T_(nm, 50, GOLD_LT, "kufi_m"), x, 180, a)
        # chef stands in front of the two models while she speaks
        chef_in(im, t, T, [p1], "chef_spoon", 1660, 640, 380, 460)
        a2 = ramp(t, at(T, p2, 0.05), at(T, p2, 0.15)) * a
        if a2 > 0:
            paste(im, _plane_note(), W / 2, 480, a2)
            paste(im, label_chip("{OH}  على C1 أسفل مستوى الحلقة", 38, (255, 190, 210)), 1380, 820, a2 * ramp(t, at(T, p2, 0.15), at(T, p2, 0.25)))
            paste(im, label_chip("{OH}  على C1 أعلى مستوى الحلقة", 38, (180, 220, 255)), 560, 820, a2 * ramp(t, at(T, p2, 0.6), at(T, p2, 0.7)))
    a3 = ramp(t, at(T, p3, 0.0), at(T, p3, 0.1))
    if a3 > 0:
        paste(im, card(1400, 150, band=True), W / 2, 905 if t < at(T, p3, 0.55) else 300, a3 * (1 if t < at(T, p3, 0.55) else 0))
        if t < at(T, p3, 0.55):
            paste(im, T_("متشكِّلات (أيزومرات): الصيغة نفسها {C₆H₁₂O₆} – واتجاه مختلف لمجموعة {OH} عند C1", 36, INK, "naskh", False), W / 2, 912, a3)
        a4 = ramp(t, at(T, p3, 0.55), at(T, p3, 0.68))
        if a4 > 0:
            heading(im, "فرق صغير ... نتائج كبيرة", a4, 180)
            paste(im, _haworth_mini("a"), 1400, 420, a4)
            paste(im, _haworth_mini("b"), 520, 420, a4)
            paste(im, _preview_chain("a"), 1400, 700, a4 * ramp(t, at(T, p3, 0.68), at(T, p3, 0.78)))
            paste(im, _preview_chain("b"), 520, 700, a4 * ramp(t, at(T, p3, 0.68), at(T, p3, 0.78)))
            paste(im, T_("النشا والجلايكوجين", 44, (255, 190, 210), "kufi_m"), 1400, 830, a4 * ramp(t, at(T, p3, 0.72), at(T, p3, 0.82)))
            paste(im, T_("السليلوز", 44, (180, 220, 255), "kufi_m"), 520, 830, a4 * ramp(t, at(T, p3, 0.82), at(T, p3, 0.92)))
    return im


@functools.lru_cache(None)
def _plane_note():
    def d(c):
        c.set_dash([14, 10])
        rgb(c, GOLD_LT, 0.7)
        c.set_line_width(2.5)
        for x0 in (1340 - 300, 560 - 300):
            c.move_to(x0, 480)
            c.line_to(x0 + 600, 480)
        c.stroke()
        c.set_dash([])
    return layer(d)


@functools.lru_cache(None)
def _haworth_mini(anomer):
    s = 95
    col = ALPHA_C if anomer == "a" else BETA_C
    return layer(lambda c: haworth(c, 180, 150, s, "glc", anomer, show_H=False, glow=col,
                                   highlight=("C1_down",) if anomer == "a" else ("C1_up",)), 360, 300)


@functools.lru_cache(None)
def _preview_chain(kind):
    def d(c):
        col = ALPHA_C if kind == "a" else BETA_C
        n = 7
        for k in range(n):
            x = 50 + k * 70
            y = 60 + (14 * math.sin(k * 1.1) if kind == "a" else 0)
            if k:
                chem.line(c, (x - 70, 60 + (14 * math.sin((k - 1) * 1.1) if kind == "a" else 0)), (x, y), 4, GOLD)
        for k in range(n):
            x = 50 + k * 70
            y = 60 + (14 * math.sin(k * 1.1) if kind == "a" else 0)
            token(c, x, y, 26, col, o_up=(kind == "a" or k % 2 == 0), glow=False)
    return layer(d, 520, 120)


# ----------------------------------------------------------------------------- scene 6
def s06(t, T):
    D = T.D
    im = molecular_frame(t)
    title_plaque(im, t, D, "وظائف السكريات الأحادية")
    p1, p2 = "s06_01", "s06_02"
    a1 = window(t, T.start(p1) - 0.2, T.end(p1) + 0.8, 0.6)
    if a1 > 0:
        paste(im, _cell_outline(), W / 2, 560, a1 * 0.9)
        heading(im, "١) مصدر للطاقة", a1, 170)
        steps = [("جلوكوز", 1500, 0.25), ("التنفس الخلوي:\nسلسلة من التفاعلات", 1050, 0.45), ("طاقة", 640, 0.68), ("{ATP}", 300, 0.8)]
        for i, (s, x, f) in enumerate(steps):
            ai = a1 * ramp(t, at(T, p1, f), at(T, p1, f + 0.06))
            if i == 0:
                paste(im, _single_token(), x, 520, ai, scale=0.75)
            elif i == 1:
                paste(im, _reaction_chain(t), x, 520, ai)
            elif i == 2:
                glow_spot(im, x, 520, 110, GOLD, ai * (0.7 + 0.3 * math.sin(t * 6)))
                paste(im, T_("⚡", 80, GOLD_LT, "inter"), x, 520, 0)
            else:
                paste(im, _atp_icon(), x, 520, ai)
            lab = s.split("\n")
            for j, l in enumerate(lab):
                paste(im, T_(l, 40), x, 690 + j * 52, ai)
            if i:
                aa = ai
                arr = _h_arrow(steps[i - 1][1] - 150, x + 150)
                paste(im, arr, (steps[i - 1][1] + x) / 2, 520, aa)
        paste(im, label_chip("الطاقة المنطلقة تُستخدم في بناء {ATP}", 36, GOLD_LT), W / 2, 880,
              a1 * ramp(t, at(T, p1, 0.85), at(T, p1, 0.95)))
    a2 = window(t, T.start(p2) - 0.2, D, 0.6)
    if a2 > 0:
        heading(im, "٢) وحدات بنائية", a2, 170)
        rows = [("الجلوكوز", "النشا  •  الجلايكوجين  •  السليلوز", 0.1, ALPHA_C),
                ("الريبوز", "{RNA}  •  {ATP}", 0.45, GOLD),
                ("الديوكسي ريبوز", "{DNA}", 0.75, BETA_C)]
        for j, (src, dst, f, col) in enumerate(rows):
            aj = a2 * ramp(t, at(T, p2, f), at(T, p2, f + 0.08))
            y = 340 + j * 210
            paste(im, label_chip(src, 44, GOLD_LT), 1500, y, aj)
            paste(im, _h_arrow(1300, 1080), 1190, y, aj)
            paste(im, label_chip(dst, 44), 700, y, aj)
            if j == 2:
                paste(im, _dna_icon(), 220, y, aj)
    return im


@functools.lru_cache(None)
def _cell_outline():
    def d(c):
        c.save()
        c.translate(W / 2, 560)
        c.scale(1.0, 0.52)
        c.arc(0, 0, 900, 0, 2 * math.pi)
        c.restore()
        rgb(c, (120, 200, 160), 0.08)
        c.fill_preserve()
        rgb(c, (140, 220, 180), 0.45)
        c.set_line_width(4)
        c.stroke()
    return layer(d, W, 1120)


def _reaction_chain(t):
    return _reaction_chain_c(int(t * 8) % 8)


@functools.lru_cache(None)
def _reaction_chain_c(k):
    def d(c):
        for i in range(5):
            x = 40 + i * 70
            a = 1.0 if i <= k % 6 else 0.35
            atom_ball(c, x, 60, 18, GOLD if i % 2 else ROSE, None, a)
            if i:
                chem.line(c, (x - 52, 60), (x - 18, 60), 3, CREAM, 0.6)
    return layer(d, 360, 120)


@functools.lru_cache(None)
def _h_arrow(x0, x1):
    w = abs(x0 - x1) + 40
    return layer(lambda c: arrow(c, (w - 20, 30), (20, 30), GOLD_LT, 5, 18), w, 60)


@functools.lru_cache(None)
def _atp_icon():
    def d(c):
        atom_ball(c, 70, 90, 50, ROYAL, None)
        for k in range(3):
            chem.line(c, (110 + k * 50, 90), (140 + k * 50, 90), 4)
            atom_ball(c, 150 + k * 50, 90, 22, GOLD, "P")
    out = layer(d, 300, 180)
    t = text_img("ATP", 34, CREAM, "inter")
    out.alpha_composite(t, (70 - t.width // 2, 90 - t.height // 2))
    return out


@functools.lru_cache(None)
def _dna_icon():
    def d(c):
        for k in range(60):
            y = 10 + k * 3
            x1 = 70 + 40 * math.sin(k * 0.2)
            x2 = 70 - 40 * math.sin(k * 0.2)
            if k % 6 == 0:
                chem.line(c, (x1, y), (x2, y), 2, CREAM, 0.6)
            rgb(c, BETA_C)
            c.arc(x1, y, 3.4, 0, 2 * math.pi)
            c.fill()
            rgb(c, ROSE)
            c.arc(x2, y, 3.4, 0, 2 * math.pi)
            c.fill()
    return layer(d, 140, 200)


# ----------------------------------------------------------------------------- scene 7
def s07(t, T):
    D = T.D
    p1, p2, p3, p4 = "s07_01", "s07_02", "s07_03", "s07_04"
    k_mol = T.end(p1) + 0.2
    if t < k_mol + 0.8:
        im = camera("b_session", t / (k_mol + 0.8), 1.0, 1.15, 0.5, 0.6, 0.5, 0.65)
        im.alpha_composite(vignette())
        chef_in(im, t, T, [p1], "chef_spoon", 1580, 560)
        j = ramp(t, at(T, p1, 0.45), at(T, p1, 0.8))
        a = window(t, at(T, p1, 0.1), k_mol + 0.5, 0.4)
        paste(im, _table_token(ALPHA_C), 640 - 120 * (1 - j), 640, a)
        paste(im, _table_token(ROSE), 900 + 120 * (1 - j), 640, a)
        if j >= 1:
            glow_spot(im, 770, 640, 120, GOLD, a * window(t, at(T, p1, 0.8), at(T, p1, 1.0), 0.15))
            paste(im, label_chip("سكر ثنائي", 44, GOLD_LT), 770, 790, a)
        if t > k_mol:
            im = Image.blend(im, molecular_frame(t), xfade(t, k_mol))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "السكريات الثنائية")
    specs = [
        (p2, "المالتوز (سكر الشعير)", "ألفا جلوكوز + ألفا جلوكوز", "{α(1→4)}  بين C1 و C4", "الحبوب النابتة (الشعير)", "maltose"),
        (p3, "السكروز (سكر المائدة)", "ألفا جلوكوز + بيتا فركتوز", "{α(1→2)β}  بين C1 و C2", "قصب السكر والشمندر  •  يُنقل في النباتات", "sucrose"),
        (p4, "اللاكتوز (سكر الحليب)", "بيتا جالاكتوز + جلوكوز", "{β(1→4)}  بين C1 و C4", "الحليب", "lactose"),
    ]
    for cid, name, units, bond, src, key in specs:
        end = T.end(cid) + (0.7 if cid != p4 else D)
        a = window(t, T.start(cid) - 0.3, end, 0.5)
        if a <= 0:
            continue
        heading(im, name, a, 160, 60)
        paste(im, label_chip(units, 38), W / 2, 250, a * ramp(t, at(T, cid, 0.05), at(T, cid, 0.15)))
        prog = ramp(t, at(T, cid, 0.2), at(T, cid, 0.42))
        paste(im, _disacch(key, round(prog * 24) / 24), W / 2, 540, a)
        paste(im, label_chip(bond, 38, GOLD_LT), W / 2, 850, a * ramp(t, at(T, cid, 0.42), at(T, cid, 0.5)))
        paste(im, label_chip("المصدر: " + src, 34, CREAM, (20, 50, 30), OM_GREEN), W / 2, 922, a * ramp(t, at(T, cid, 0.72), at(T, cid, 0.8)))
    return im


@functools.lru_cache(None)
def _table_token(col):
    return layer(lambda c: token(c, 110, 110, 70, col), 220, 220)


@functools.lru_cache(None)
def _disacch(key, prog):
    s = 150
    w, h = 1300, 560
    def d(c):
        cy = 270
        if key == "maltose":
            L = haworth(c, 400, cy, s, "glc", "a", show_H=False, omit={"C1_down"}, highlight=("C1",) if False else ())
            R = haworth(c, 900, cy, s, "glc", "a", show_H=False, omit={"C4_down"})
            glyco_link(c, L["C1"], R["C4"], s, True, progress=prog)
        elif key == "sucrose":
            G = haworth(c, 420, cy, s, "glc", "a", show_H=False, omit={"C1_down"})
            F = fructose_in_sucrose(c, 900, cy, s)
            glyco_link(c, G["C1"], F["C2"], s, True, progress=prog)
        else:
            Ga = haworth(c, 400, cy + 20, s, "gal", "b", show_H=False, omit={"C1_up"})
            Gl = haworth(c, 900, cy + 20, s, "glc", "b", flipped=True, show_H=False, omit={"C4_up"})
            glyco_link(c, Ga["C1"], Gl["C4"], s, False, progress=prog)
        names = {"maltose": ("جلوكوز", "جلوكوز"), "sucrose": ("جلوكوز", "فركتوز"), "lactose": ("جالاكتوز", "جلوكوز")}
    out = layer(d, w, h)
    n1, n2 = {"maltose": ("ألفا جلوكوز", "ألفا جلوكوز"), "sucrose": ("ألفا جلوكوز", "بيتا فركتوز"), "lactose": ("بيتا جالاكتوز", "جلوكوز")}[key]
    for nm, x in ((n1, 400), (n2, 900)):
        ti = text_img(nm, 34, GOLD_LT, "naskh")
        out.alpha_composite(ti, (int(x - ti.width / 2), h - ti.height - 4))
    return out


def _ar_greek(s):
    # Greek letter rendered with the Latin font
    return s.replace("α-", "{α-}").replace("β-", "{β-}")


# ----------------------------------------------------------------------------- scene 8: condensation / hydrolysis
def s08(t, T):
    D = T.D
    im = molecular_frame(t)
    title_plaque(im, t, D, "التكثيف والتحلل المائي")
    p1, p2, p3 = "s08_01", "s08_02", "s08_03"
    # state machine (all in seconds)
    approach = ramp(t, 0.4, at(T, p1, 0.3))                  # molecules move in
    leave = ramp(t, at(T, p1, 0.55), at(T, p1, 0.9))           # OH + H leave and form water
    bond = ramp(t, T.start(p2) + 0.2, at(T, p2, 0.35))         # bond drawn
    back = ramp(t, at(T, p3, 0.12), at(T, p3, 0.45))           # water returns
    breakp = ramp(t, at(T, p3, 0.4), at(T, p3, 0.62))          # bond breaks, molecules separate
    sep = breakp
    gap = 520 - 330 * approach + 330 * sep
    frame = layer(lambda c: _condense_draw(c, t, gap, leave, bond * (1 - breakp), back, breakp))
    paste(im, frame, W / 2, H / 2)
    # labels
    paste(im, label_chip("مجموعتا هيدروكسيل {OH}", 38, (180, 235, 255)), W / 2, 210,
          window(t, at(T, p1, 0.15), at(T, p1, 0.6), 0.4))
    paste(im, label_chip("خروج جزيء ماء  {H₂O}", 40, (180, 235, 255)), W / 2, 210, window(t, at(T, p1, 0.6), T.end(p2), 0.4))
    paste(im, wood_sign("التكثيف  {−H₂O}", 50, 40), W / 2, 905, window(t, T.start(p2), T.start(p3) + 0.5, 0.5))
    paste(im, label_chip("رابطة جلايكوسيدية: {C–O–C}", 40, GOLD_LT), W / 2, 300, window(t, at(T, p2, 0.35), T.start(p3) + 0.3, 0.4))
    paste(im, wood_sign("التحلل المائي  {+H₂O}", 50, 40), W / 2, 905, window(t, T.start(p3) + 0.3, D, 0.5))
    paste(im, label_chip("يُضاف الماء {←} تنكسر الرابطة", 40, (180, 235, 255)), W / 2, 210, window(t, at(T, p3, 0.1), at(T, p3, 0.7), 0.4))
    paste(im, label_chip("هذا ما يحدث عند الهضم", 40, GOLD_LT), W / 2, 210, window(t, at(T, p3, 0.72), D, 0.4))
    return im


def _condense_draw(c, t, gap, leave, bond, back, breakp):
    s = 150
    cy = 470
    lx, rx = W / 2 - gap / 2 - s, W / 2 + gap / 2 + s
    joined = bond > 0.02
    L = haworth(c, lx, cy, s, "glc", "a", show_H=False, omit={"C1_down"})
    R = haworth(c, rx, cy, s, "glc", "a", show_H=False, omit={"C4_down"})
    Lend = (L["C1"][0], L["C1"][1] + 0.6 * s)       # where L's C1-OH sits
    Rend = (R["C4"][0], R["C4"][1] + 0.6 * s)       # where R's C4-OH sits
    mid = ((Lend[0] + Rend[0]) / 2, Lend[1] + 0.12 * s)
    # water location
    wpos = (W / 2, cy + 2.05 * s)
    wl = max(0.0, leave - back)                      # 1 = water is away
    if bond > 0.02:
        glyco_link(c, L["C1"], R["C4"], s, True, progress=bond)
    else:
        # R's C4-OH oxygen stays with R; its H leaves
        chem.line(c, R["C4"], (Rend[0], Rend[1] - 0.05 * s), s * 0.03)
        if breakp < 0.5 or breakp >= 1:
            pass
        group(c, Rend[0], Rend[1] - 0.02 * s, "HO" if wl < 0.5 else "O", s * 0.26, 1, 1 if wl < 0.5 else 0)
        # L's C1-OH
        if wl < 0.5:
            chem.line(c, L["C1"], (Lend[0], Lend[1] - 0.05 * s), s * 0.03)
            group(c, Lend[0], Lend[1] - 0.02 * s, "OH", s * 0.26, 1, 0)
    # the leaving/returning atoms: OH (from L) + H (from R) -> H2O
    if 0.02 < wl < 0.999 or (leave > 0 and wl >= 0.999):
        k = ease(wl)
        oh = (Lend[0] + (wpos[0] - 40 - Lend[0]) * k, Lend[1] + 30 + (wpos[1] - Lend[1] - 30) * k)
        hh = (Rend[0] - 30 + (wpos[0] + 40 - Rend[0] + 30) * k, Rend[1] + 30 + (wpos[1] - Rend[1] - 30) * k)
        if wl < 0.98:
            g = cairo.RadialGradient(oh[0], oh[1], 1, oh[0], oh[1], 60)
            g.add_color_stop_rgba(0, HBOND[0] / 255, HBOND[1] / 255, HBOND[2] / 255, 0.7)
            g.add_color_stop_rgba(1, HBOND[0] / 255, HBOND[1] / 255, HBOND[2] / 255, 0)
            c.set_source(g)
            c.arc(oh[0], oh[1], 60, 0, 2 * math.pi)
            c.fill()
            group(c, oh[0], oh[1], "OH", s * 0.26, 0, 0)
            group(c, hh[0], hh[1], "H", s * 0.26, 0, 0)
        if wl > 0.6:
            a = min(1, (wl - 0.6) / 0.3)
            chem.line(c, (wpos[0], wpos[1]), (wpos[0] - 46, wpos[1] + 34), 5, CREAM, a)
            chem.line(c, (wpos[0], wpos[1]), (wpos[0] + 46, wpos[1] + 34), 5, CREAM, a)
            atom_ball(c, wpos[0], wpos[1], 34, O_ATOM, "O", a)
            atom_ball(c, wpos[0] - 50, wpos[1] + 38, 22, H_ATOM, "H", a)
            atom_ball(c, wpos[0] + 50, wpos[1] + 38, 22, H_ATOM, "H", a)


# ----------------------------------------------------------------------------- scene 9
def s09(t, T):
    D = T.D
    p1, p2 = "s09_01", "s09_02"
    k_mol = T.end(p1) + 0.2
    if t < k_mol + 0.8:
        im = camera("b_tools", t / (k_mol + 0.8), 1.0, 1.3, 0.5, 0.5, 0.45, 0.55)
        im.alpha_composite(vignette())
        chef_in(im, t, T, [p1], "chef_spoon", 1580, 560)
        if t > k_mol:
            im = Image.blend(im, molecular_frame(t), xfade(t, k_mol))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "عديدات التسكر")
    a = window(t, T.start(p2) - 0.2, D, 0.6)
    if a > 0:
        heading(im, "بوليمرات: آلاف الوحدات السكرية المرتبطة", a * (1 - ramp(t, at(T, p2, 0.62), at(T, p2, 0.68))), 170, 52)
        asm = ramp(t, at(T, p2, 0.02), at(T, p2, 0.55))
        split = ramp(t, at(T, p2, 0.62), at(T, p2, 0.72))
        paste(im, layer(lambda c: _assemble(c, t, asm, 1 - split)), W / 2, H / 2, a)
        paste(im, label_chip("ليست حلوة المذاق", 38), 1500, 780, a * window(t, at(T, p2, 0.4), at(T, p2, 0.65), 0.3))
        if split > 0:
            heading(im, "جميعها بوليمرات من الجلوكوز", split * a, 170, 52)
            for k, (nm, key, col) in enumerate([("النشا", "starch", (255, 190, 210)), ("الجلايكوجين", "glycogen", (255, 190, 210)),
                                                ("السليلوز", "cellulose", (180, 220, 255))]):
                ak = a * ramp(t, at(T, p2, 0.68 + k * 0.08), at(T, p2, 0.76 + k * 0.08))
                x = 1460 - k * 500
                paste(im, _poly_icon(key), x, 520, ak, scale=0.8 + 0.2 * ak)
                paste(im, T_(nm, 50, col, "kufi_m"), x, 780, ak)
    return im


def _assemble(c, t, p, a):
    if a <= 0.01:
        return
    n = 22
    rnd = random.Random(5)
    for i in range(n):
        tx, ty = 220 + i * 70, 540 + 40 * math.sin(i * 0.6 + t * 1.5)
        sx, sy = rnd.uniform(0, W), rnd.choice([rnd.uniform(-200, 150), rnd.uniform(950, 1300)])
        k = ease(min(1, max(0, p * 1.6 - i / n * 0.6)))
        x, y = sx + (tx - sx) * k, sy + (ty - sy) * k
        if i and k > 0.97:
            px, py = 220 + (i - 1) * 70, 540 + 40 * math.sin((i - 1) * 0.6 + t * 1.5)
            chem.line(c, (px, py), (x, y), 4, GOLD, a)
        token(c, x, y, 24, ALPHA_C, alpha=a, glow=False)


@functools.lru_cache(None)
def _poly_icon(key):
    def d(c):
        if key == "starch":
            for k in range(8):
                x, y = 40 + k * 40, 150 + 40 * math.sin(k * 1.0)
                if k:
                    chem.line(c, (40 + (k - 1) * 40, 150 + 40 * math.sin((k - 1) * 1.0)), (x, y), 3, GOLD)
            for k in range(8):
                token(c, 40 + k * 40, 150 + 40 * math.sin(k * 1.0), 17, ALPHA_C, glow=False)
        elif key == "glycogen":
            nodes, ends = chem.glycogen_tree(3, 2, 190, 150, 0.6)
            for x, y, par, kind in nodes:
                if par >= 0:
                    chem.line(c, nodes[par][:2], (x, y), 2.5, GOLD if kind == "a16" else CREAM, 0.9)
            for x, y, par, kind in nodes[1:]:
                token(c, x, y, 9, ALPHA_C, glow=False)
        else:
            for r in range(3):
                for k in range(8):
                    x, y = 40 + k * 42, 90 + r * 60
                    if k:
                        chem.line(c, (x - 42, y), (x, y), 3, GOLD)
                for k in range(8):
                    token(c, 40 + k * 42, 90 + r * 60, 16, BETA_C, o_up=(k % 2 == 0), glow=False)
                if r:
                    for k in range(8):
                        chem.line(c, (40 + k * 42, 90 + (r - 1) * 60 + 18), (40 + k * 42, 90 + r * 60 - 18), 2, HBOND, 0.9, [5, 5])
    return layer(d, 380, 300)


# ----------------------------------------------------------------------------- scene 10: starch
def s10(t, T):
    D = T.D
    p1, p2, p3 = "s10_01", "s10_02", "s10_03"
    k_cell = at(T, p1, 0.32)
    if t < k_cell + 0.8:
        im = camera("b_ingred", t / (k_cell + 0.8), 1.0, 1.35, 0.5, 0.5, 0.3, 0.45)
        im.alpha_composite(vignette())
        paste(im, label_chip("حبوب القمح  •  درنات البطاطس", 42, GOLD_LT), W / 2, 880, window(t, 0.5, k_cell + 0.4, 0.4))
        if t > k_cell:
            im = Image.blend(im, molecular_frame(t), xfade(t, k_cell))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "النشا")
    a = window(t, k_cell, T.start(p2) + 0.3, 0.6)
    if a > 0:
        paste(im, _plant_cell(), 1260, 540, a, scale=0.9 + 0.1 * a)
        paste(im, label_chip("حبيبات النشا داخل البلاستيدات", 36, GOLD_LT), 1260, 900, a * ramp(t, at(T, p1, 0.75), at(T, p1, 0.85)))
        paste(im, card(620, 420), 420, 520, a * ramp(t, at(T, p1, 0.4), at(T, p1, 0.5)))
        lines = [("الجلوكوز: يذوب في الماء", OM_RED, 0.42), ("يؤثر في حركة الماء (الأسموزية)", WOOD, 0.5),
                 ("النشا: جزيء كبير غير ذائب", OM_GREEN, 0.62), ("مخزن مُدمج للجلوكوز", WOOD, 0.7)]
        for j, (s, col, f) in enumerate(lines):
            paste(im, T_(s, 36, col, "naskh_b", False), 420, 400 + j * 80, a * ramp(t, at(T, p1, f), at(T, p1, f + 0.06)))
    a2 = window(t, T.start(p2) - 0.2, D, 0.6)
    if a2 > 0:
        k3 = ramp(t, T.start(p3) - 0.3, at(T, p3, 0.1))
        y_am = 420 - 150 * k3
        heading(im, "النشا = أميلوز + أميلوبكتين", a2 * (1 - k3), 170, 54)
        paste(im, layer(lambda c: _helix(c, t, 1 - 0.45 * k3), W, 420), W / 2, y_am, a2)
        paste(im, T_("الأميلوز", 50, (255, 190, 210), "kufi_m"), 1700, y_am - 120, a2)
        chips = [("وحدات ألفا جلوكوز", 0.2), ("روابط {α(1→4)}", 0.4), ("غير متفرع", 0.55), ("يلتف حلزونًا مُدمَجًا", 0.75)]
        for j, (s, f) in enumerate(chips):
            aj = a2 * ramp(t, at(T, p2, f), at(T, p2, f + 0.08)) * (1 - k3)
            paste(im, label_chip(s, 36), 1560 - j * 400, 760, aj)
        if k3 > 0:
            paste(im, _amylopectin(), W / 2, 640, a2 * k3)
            paste(im, T_("الأميلوبكتين", 50, (255, 190, 210), "kufi_m"), 1700, 470, a2 * k3)
            chips = [("روابط {α(1→4)} في السلاسل", 0.3), ("روابط {α(1→6)} عند التفرعات", 0.55), ("سلسلة متفرعة", 0.8)]
            for j, (s, f) in enumerate(chips):
                aj = a2 * ramp(t, at(T, p3, f), at(T, p3, f + 0.08))
                paste(im, label_chip(s, 36, GOLD_LT if j == 1 else CREAM), 1500 - j * 520, 925, aj)
    return im


@functools.lru_cache(None)
def _plant_cell():
    def d(c):
        round_rect(c, 20, 20, 760, 600, 70)
        rgb(c, (90, 170, 90), 0.25)
        c.fill_preserve()
        rgb(c, (120, 210, 120))
        c.set_line_width(14)
        c.stroke()
        round_rect(c, 44, 44, 712, 552, 52)
        rgb(c, (170, 230, 160), 0.6)
        c.set_line_width(3)
        c.stroke()
        rnd = random.Random(2)
        for k in range(6):
            x, y = rnd.uniform(170, 630), rnd.uniform(150, 480)
            c.save()
            c.translate(x, y)
            c.scale(1.0, 0.65)
            c.arc(0, 0, 80, 0, 2 * math.pi)
            c.restore()
            rgb(c, (110, 180, 90), 0.85)
            c.fill()
            for g in range(3):
                gx, gy = x + rnd.uniform(-38, 38), y + rnd.uniform(-20, 20)
                c.save()
                c.translate(gx, gy)
                c.scale(1.0, 0.75)
                c.arc(0, 0, 18, 0, 2 * math.pi)
                c.restore()
                rgb(c, (250, 240, 215))
                c.fill()
    return layer(d, 800, 640)


def _helix(c, t, sc):
    n = 24
    pts = chem.helix_points(n, W / 2 - (n - 1) * 34 * sc, 210, 68 * sc, 70 * sc, t * 1.2, 6.0)
    order = sorted(range(n), key=lambda i: pts[i][2])
    for i in range(1, n):
        a, b = pts[i - 1], pts[i]
        dep = (a[2] + b[2]) / 2
        chem.line(c, a[:2], b[:2], 4 * sc, GOLD, 0.45 + 0.4 * (dep + 1) / 2)
    for i in order:
        x, y, dep = pts[i]
        token(c, x, y, (22 + 8 * dep) * sc, ALPHA_C, alpha=0.55 + 0.45 * (dep + 1) / 2, glow=dep > 0.3)


@functools.lru_cache(None)
def _amylopectin():
    def d(c):
        dx = 62
        main = [(150 + k * dx, 420) for k in range(24)]
        br1 = [(150 + (5 + k) * dx + 30, 300) for k in range(10)]
        br2 = [(150 + (13 + k) * dx + 30, 180) for k in range(9)]
        br3 = [(150 + (16 + k) * dx + 30, 300) for k in range(8)]
        for chain_ in (main, br1, br2, br3):
            for i in range(1, len(chain_)):
                chem.line(c, chain_[i - 1], chain_[i], 4, CREAM, 0.85)
        branch = [(main[5], br1[0]), (br1[7], br2[0]), (main[16], br3[0])]
        for a, b in branch:
            chem.line(c, (a[0], a[1] - 22), (b[0] - 6, b[1] + 22), 6, GOLD)
            g = cairo.RadialGradient(a[0], a[1], 2, a[0], a[1], 50)
            g.add_color_stop_rgba(0, 1, 0.8, 0.3, 0.7)
            g.add_color_stop_rgba(1, 1, 0.8, 0.3, 0)
            c.set_source(g)
            c.arc(a[0], a[1], 50, 0, 2 * math.pi)
            c.fill()
        for chain_ in (main, br1, br2, br3):
            for x, y in chain_:
                token(c, x, y, 22, ALPHA_C, glow=False)
        c.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        c.set_font_size(26)
        for a, b in branch:
            rgb(c, GOLD_LT)
            c.move_to(a[0] - 120, (a[1] + b[1]) / 2 + 6)
            c.show_text("α(1→6)")
        rgb(c, CREAM)
        c.move_to(main[10][0] - 20, 480)
        c.show_text("α(1→4)")
    return layer(d, 1800, 540)


# ----------------------------------------------------------------------------- scene 11: glycogen
GLY = chem.glycogen_tree(seed=11, depth=3, cx=W / 2, cy=560, scale=0.78)


def s11(t, T):
    D = T.D
    im = molecular_frame(t)
    title_plaque(im, t, D, "الجلايكوجين")
    p1, p2, p3 = "s11_01", "s11_02", "s11_03"
    a1 = window(t, 0.2, T.start(p2) + 0.4, 0.5)
    if a1 > 0:
        heading(im, "مخزن الجلوكوز في الحيوانات", a1, 170)
        paste(im, _organ("liver"), 1300, 560, a1 * ramp(t, 0.6, 1.4))
        paste(im, _organ("muscle"), 620, 560, a1 * ramp(t, 1.2, 2.0))
        paste(im, T_("الكبد", 48, GOLD_LT, "kufi_m"), 1300, 820, a1 * ramp(t, 0.6, 1.4))
        paste(im, T_("العضلات", 48, GOLD_LT, "kufi_m"), 620, 820, a1 * ramp(t, 1.2, 2.0))
    a2 = window(t, T.start(p2) - 0.2, D, 0.6)
    if a2 > 0:
        grow = ramp(t, T.start(p2), at(T, p2, 0.6))
        rel = ramp(t, at(T, p3, 0.25), at(T, p3, 0.85))
        paste(im, layer(lambda c: _glycogen_draw(c, grow, rel, t)), W / 2, H / 2, a2)
        chips = [("وحدات ألفا جلوكوز", 0.1), ("روابط {α(1→4)}", 0.25), ("تفرعات {α(1→6)}", 0.4),
                 ("تفرعات أكثر وسلاسل أقصر من الأميلوبكتين", 0.6)]
        for j, (s, f) in enumerate(chips):
            aj = a2 * window(t, at(T, p2, f), T.start(p3) + 0.3, 0.4)
            paste(im, label_chip(s, 34, GOLD_LT if "1→6" in s else CREAM), 300, 300 + j * 110, aj, "cl")
        paste(im, label_chip("حبيبات في خلايا الكبد والعضلات", 36), W / 2, 925, a2 * window(t, at(T, p2, 0.8), T.start(p3) + 0.3, 0.4))
        a3 = ramp(t, T.start(p3), at(T, p3, 0.1))
        paste(im, label_chip("نهايات كثيرة {←} تحرير سريع للجلوكوز", 40, GOLD_LT), W / 2, 925, a3)
        paste(im, label_chip("الإنزيمات تعمل على نهايات عديدة في وقت واحد", 34), 300, 300, a3, "cl")
    return im


def _glycogen_draw(c, grow, rel, t):
    nodes, ends = GLY
    n = len(nodes)
    shown = int(1 + grow * (n - 1))
    for i in range(1, shown):
        x, y, par, kind = nodes[i]
        if par >= 0:
            chem.line(c, nodes[par][:2], (x, y), 5 if kind == "a16" else 3, GOLD if kind == "a16" else CREAM, 0.9)
    ends_set = set(ends)
    for i in range(1, shown):
        x, y, par, kind = nodes[i]
        if i in ends_set and rel > 0:
            continue
        token(c, x, y, 13, ALPHA_C, glow=False)
        if kind == "a16":
            g = cairo.RadialGradient(x, y, 1, x, y, 26)
            g.add_color_stop_rgba(0, 1, 0.8, 0.3, 0.6)
            g.add_color_stop_rgba(1, 1, 0.8, 0.3, 0)
            c.set_source(g)
            c.arc(x, y, 26, 0, 2 * math.pi)
            c.fill()
    atom_ball(c, nodes[0][0], nodes[0][1], 16, GOLD, None)
    if rel > 0:
        cx, cy = nodes[0][:2]
        for e in ends:
            x, y = nodes[e][:2]
            vx, vy = x - cx, y - cy
            nn = math.hypot(vx, vy) or 1
            k = ease(rel)
            px, py = x + vx / nn * 200 * k, y + vy / nn * 200 * k
            token(c, px, py, 14, (255, 230, 150), alpha=1 - 0.4 * k)


@functools.lru_cache(None)
def _organ(kind):
    def d(c):
        if kind == "liver":
            c.move_to(40, 160)
            c.curve_to(40, 40, 330, 20, 380, 90)
            c.curve_to(410, 140, 300, 260, 180, 270)
            c.curve_to(100, 276, 40, 230, 40, 160)
            g = cairo.LinearGradient(0, 0, 0, 300)
            g.add_color_stop_rgb(0, 0.62, 0.22, 0.2)
            g.add_color_stop_rgb(1, 0.38, 0.12, 0.12)
            c.set_source(g)
            c.fill()
        else:
            c.save()
            c.translate(210, 150)
            c.scale(1.0, 0.45)
            c.arc(0, 0, 190, 0, 2 * math.pi)
            c.restore()
            g = cairo.LinearGradient(0, 60, 0, 240)
            g.add_color_stop_rgb(0, 0.8, 0.35, 0.38)
            g.add_color_stop_rgb(1, 0.5, 0.15, 0.2)
            c.set_source(g)
            c.fill()
            for k in range(9):
                rgb(c, (255, 220, 220), 0.35)
                c.set_line_width(2)
                c.move_to(60 + k * 34, 100)
                c.line_to(60 + k * 34, 200)
                c.stroke()
        rnd = random.Random(1 if kind == "liver" else 2)
        for _ in range(16):
            x, y = rnd.uniform(110, 320), rnd.uniform(100, 200)
            g = cairo.RadialGradient(x, y, 1, x, y, 14)
            g.add_color_stop_rgba(0, 1, 0.75, 0.85, 0.95)
            g.add_color_stop_rgba(1, 1, 0.75, 0.85, 0)
            c.set_source(g)
            c.arc(x, y, 14, 0, 2 * math.pi)
            c.fill()
    return add_shadow(layer(d, 420, 300), 12, 0.5)


# ----------------------------------------------------------------------------- scene 12: cellulose
def s12(t, T):
    D = T.D
    p1, p2, p3, p4, p5 = "s12_01", "s12_02", "s12_03", "s12_04", "s12_05"
    k_mol = T.end(p1) + 0.2
    k_back = at(T, p5, 0.86)
    if t < k_mol + 0.8:
        im = camera("b_tools", t / (k_mol + 0.8), 1.05, 1.45, 0.5, 0.6, 0.62, 0.78)
        im.alpha_composite(vignette())
        chef_in(im, t, T, [p1], "chef_hero", 1560, 560, 470, 520)
        if t > k_mol:
            im = Image.blend(im, molecular_frame(t), xfade(t, k_mol))
    elif t > k_back:
        im = camera("b_tools", (t - k_back) / max(1, D - k_back), 1.6, 1.0, 0.62, 0.78, 0.5, 0.6)
        im.alpha_composite(vignette())
        if t < k_back + 0.8:
            im = Image.blend(molecular_frame(t), im, xfade(t, k_back))
        paste(im, label_chip("من الجزيء ... إلى سلة الخوص", 42, GOLD_LT), W / 2, 880, ramp(t, k_back + 0.6, k_back + 1.4))
    else:
        im = molecular_frame(t)
    title_plaque(im, t, D, "السليلوز")
    a2 = window(t, T.start(p2) - 0.2, T.start(p4) + 0.4, 0.5)
    if a2 > 0:
        flipk = ramp(t, at(T, p3, 0.1), at(T, p3, 0.4))
        heading(im, "وحدات بيتا جلوكوز بروابط {β(1→4)}", a2, 170, 52)
        paste(im, _cellulose_haworth(round(flipk * 20) / 20), W / 2, 520, a2)
        paste(im, label_chip("أكثر الجزيئات العضوية وفرة على الأرض", 36), W / 2, 260, a2 * window(t, at(T, p2, 0.05), at(T, p2, 0.6), 0.4))
        paste(im, label_chip("كل وحدة تنقلب {180°} بالنسبة إلى جارتها", 38, (180, 220, 255)), W / 2, 860,
              a2 * ramp(t, at(T, p3, 0.12), at(T, p3, 0.22)))
        paste(im, label_chip("سلسلة مستقيمة غير متفرعة  •  مجموعات {OH} على الجانبين", 36, GOLD_LT), W / 2, 922,
              a2 * ramp(t, at(T, p3, 0.6), at(T, p3, 0.7)))
    a4 = window(t, T.start(p4) - 0.2, T.start(p5) + 0.4, 0.5)
    if a4 > 0:
        hb = ramp(t, at(T, p4, 0.12), at(T, p4, 0.4))
        heading(im, "سلاسل متوازية وروابط هيدروجينية", a4, 170, 52)
        paste(im, layer(lambda c: _cell_chains(c, hb, t)), W / 2, H / 2, a4)
        paste(im, label_chip("رابطة جلايكوسيدية {β(1→4)}: داخل السلسلة", 36, GOLD_LT), 560, 900, a4 * ramp(t, at(T, p4, 0.45), at(T, p4, 0.55)))
        paste(im, label_chip("روابط هيدروجينية: بين السلاسل", 36, (180, 235, 255)), 1400, 900, a4 * ramp(t, at(T, p4, 0.7), at(T, p4, 0.8)))
    a5 = window(t, T.start(p5) - 0.2, k_back + 0.6, 0.5)
    if a5 > 0:
        st = [ramp(t, at(T, p5, f), at(T, p5, f + 0.08)) for f in (0.02, 0.3, 0.55)]
        heading(im, "من الجزيء إلى الجدار الخلوي", a5, 170, 52)
        paste(im, _microfibril(), 1450, 520, a5 * st[0])
        paste(im, label_chip("ليف دقيق: ٦٠–٧٠ جزيء سليلوز", 34, (180, 220, 255)), 1450, 760, a5 * st[0])
        paste(im, _h_arrow(1240, 1100), 1170, 520, a5 * st[1])
        paste(im, _fibre(), 950, 520, a5 * st[1])
        paste(im, label_chip("ألياف أكبر", 34), 950, 760, a5 * st[1])
        paste(im, _h_arrow(760, 640), 700, 520, a5 * st[2])
        paste(im, _wall(), 400, 520, a5 * st[2])
        paste(im, label_chip("طبقات في الجدار الخلوي", 34), 400, 760, a5 * st[2])
        paste(im, label_chip("قوة شد عالية {←} تحمي الخلية من الانفجار عند امتلائها بالماء", 36, GOLD_LT), W / 2, 900,
              a5 * ramp(t, at(T, p5, 0.7), at(T, p5, 0.78)))
    return im


@functools.lru_cache(None)
def _cellulose_haworth(flipk):
    """Three beta-glucose units: unit 2 is rotated 180 deg (animated by flipk: its vertical scale goes 1 -> -1)."""
    s = 120
    w, h = 1700, 600
    def d(c):
        cy = 300
        xs = [330, 850, 1370]
        A = haworth(c, xs[0], cy, s, "glc", "b", show_H=False, omit={"C1_up"}, glow=BETA_C)
        if flipk < 1:
            c.save()
            c.translate(xs[1], cy)
            c.scale(1, 1 - 2 * flipk if abs(1 - 2 * flipk) > 0.04 else 0.04)
            c.translate(-xs[1], -cy)
            haworth(c, xs[1], cy, s, "glc", "b", show_H=False, glow=BETA_C)
            c.restore()
            haworth(c, xs[2], cy, s, "glc", "b", show_H=False, glow=BETA_C, omit={"C4_down"})
        else:
            B = haworth(c, xs[1], cy, s, "glc", "b", flipped=True, show_H=False, omit={"C4_up", "C1_down"}, glow=BETA_C)
            Cc = haworth(c, xs[2], cy, s, "glc", "b", show_H=False, omit={"C4_down"}, glow=BETA_C)
            glyco_link(c, A["C1"], B["C4"], s, below=False, label="β(1→4)")
            glyco_link(c, B["C1"], Cc["C4"], s, below=True, label="β(1→4)")
    return layer(d, w, h)


def _cell_chains(c, hb, t):
    rows, n = 4, 16
    x0, y0, dx, dy = 360, 330, 80, 120
    for r in range(rows):
        y = y0 + r * dy
        for k in range(1, n):
            chem.line(c, (x0 + (k - 1) * dx + 22, y), (x0 + k * dx - 22, y), 5, GOLD)
    if hb > 0:
        for r in range(1, rows):
            for k in range(n):
                if k / n <= hb:
                    x = x0 + k * dx + (10 if k % 2 else -10)
                    chem.line(c, (x, y0 + (r - 1) * dy + 24), (x, y0 + r * dy - 24), 2.5, HBOND, 0.9, [6, 6])
    for r in range(rows):
        for k in range(n):
            token(c, x0 + k * dx, y0 + r * dy, 26, BETA_C, o_up=(k % 2 == 0), glow=False)


@functools.lru_cache(None)
def _microfibril():
    def d(c):
        c.save()
        round_rect(c, 6, 40, 328, 180, 90)
        c.clip()
        rgb(c, (20, 30, 60), 0.6)
        c.paint()
        for k in range(22):
            y = 48 + k * 8
            rgb(c, BETA_C if k % 2 else (160, 205, 250), 0.95)
            c.set_line_width(4)
            c.move_to(0, y)
            c.line_to(340, y)
            c.stroke()
        c.restore()
        round_rect(c, 6, 40, 328, 180, 90)
        rgb(c, CREAM, 0.8)
        c.set_line_width(2.5)
        c.stroke()
    return layer(d, 340, 260)


@functools.lru_cache(None)
def _fibre():
    def d(c):
        for k in range(7):
            y = 50 + k * 26
            g = cairo.LinearGradient(0, y - 10, 0, y + 10)
            g.add_color_stop_rgb(0, 0.6, 0.8, 1.0)
            g.add_color_stop_rgb(1, 0.2, 0.4, 0.8)
            c.set_source(g)
            round_rect(c, 10, y - 10, 260, 20, 10)
            c.fill()
    return layer(d, 280, 260)


@functools.lru_cache(None)
def _wall():
    def d(c):
        round_rect(c, 10, 10, 300, 240, 30)
        rgb(c, (90, 170, 90), 0.3)
        c.fill()
        c.save()
        round_rect(c, 10, 10, 300, 240, 30)
        c.clip()
        # three layers of microfibrils at different angles (crossed layers of the wall)
        for layer_i, ang in enumerate((0.35, -0.5, 0.9)):
            rgb(c, [(160, 210, 255), (120, 190, 250), (200, 230, 255)][layer_i], 0.8)
            c.set_line_width(4)
            for k in range(-8, 14):
                c.move_to(20 + k * 26, 20)
                c.line_to(20 + k * 26 + 240 * math.tan(ang), 240)
            c.stroke()
        c.restore()
        round_rect(c, 10, 10, 300, 240, 30)
        rgb(c, (120, 210, 120))
        c.set_line_width(8)
        c.stroke()
    return layer(d, 320, 260)


# ----------------------------------------------------------------------------- scene 13: comparison
COLS = [
    ("النشا", "starch", ["ألفا جلوكوز", "{α(1→4)}  و  {α(1→6)}", "أميلوز: غير متفرع\nأميلوبكتين: متفرع", "النباتات\n(البذور والدرنات)", "تخزين الجلوكوز"], (255, 190, 210)),
    ("الجلايكوجين", "glycogen", ["ألفا جلوكوز", "{α(1→4)}  و  {α(1→6)}", "كثير التفرع", "الحيوانات\n(الكبد والعضلات)", "تخزين الجلوكوز"], (255, 190, 210)),
    ("السليلوز", "cellulose", ["بيتا جلوكوز", "{β(1→4)}", "غير متفرع\n(سلاسل مستقيمة)", "جدر الخلايا النباتية", "دعم وقوة (بنائي)"], (180, 220, 255)),
]
ROWS = ["نوع الجلوكوز", "الروابط", "التفرع", "مكان الوجود", "الوظيفة"]


def s13(t, T):
    D = T.D
    p1 = "s13_01"
    im = camera("b_session", 0.5 + 0.5 * t / D, 1.1, 1.2, 0.5, 0.5, 0.5, 0.5, blur=7)
    shade(im, 0.55, (20, 10, 18))
    title_plaque(im, t, D, "المقارنة الشاملة")
    chef_in(im, t, T, [p1], "chef_spoon", 1640, 560, 400, 480)
    # table (large type, held on screen long enough to read)
    x_lab = 1720
    xs = [1330, 900, 470]
    y0, rh = 370, 128
    ta = ramp(t, T.end(p1) - 0.6, T.end(p1) + 0.4)
    if ta > 0:
        paste(im, glass(1780, 860, 30, (30, 16, 26), 0.86), 975, 585, ta)
        for j, r in enumerate(ROWS):
            paste(im, T_(r, 40, GOLD_LT, "naskh_b"), x_lab, y0 + j * rh, ta, "cr")
        for k, (nm, key, cells, col) in enumerate(COLS):
            cid = f"s13_0{k + 2}"
            ak = ramp(t, T.start(cid) - 0.3, T.start(cid) + 0.6)
            if ak <= 0:
                continue
            x = xs[k]
            paste(im, T_(nm, 56, col, "kufi"), x, 245, ak)
            for j, cell in enumerate(cells):
                aj = ak * ramp(t, at(T, cid, 0.08 + j * 0.15), at(T, cid, 0.16 + j * 0.15))
                img = _two_lines(cell) if "\n" in cell else text_img(cell, 38, CREAM, "naskh")
                paste(im, img, x, y0 + j * rh, aj)
    return im


@functools.lru_cache(None)
def _two_lines(cell):
    a, b = cell.split("\n")
    i1 = text_img(a, 38, CREAM, "naskh")
    i2 = text_img(b, 30, BEIGE, "naskh")
    w = max(i1.width, i2.width)
    out = Image.new("RGBA", (w, i1.height + i2.height + 6), (0, 0, 0, 0))
    out.alpha_composite(i1, ((w - i1.width) // 2, 0))
    out.alpha_composite(i2, ((w - i2.width) // 2, i1.height + 6))
    return out


# ----------------------------------------------------------------------------- scene 14
def s14(t, T):
    D = T.D
    p1, p2, p3, p4 = "s14_01", "s14_02", "s14_03", "s14_04"
    im = camera("chef_hero", t / D, 1.3, 1.0, 0.36, 0.38, 0.45, 0.5)
    im.alpha_composite(vignette())
    a2 = window(t, T.start(p2) - 0.3, T.start(p3) + 0.2, 0.5)
    if a2 > 0:
        shade(im, 0.45 * a2)
        glow_spot(im, W / 2, 470, 420, GOLD, a2 * 0.5)
        paste(im, wood_sign("التركيب يحدد الوظيفة", 96, 64), W / 2, 470, a2, scale=0.9 + 0.1 * ease_out(a2))
    a3 = window(t, T.start(p3) - 0.3, T.start(p4) + 0.2, 0.5)
    if a3 > 0:
        shade(im, 0.5 * a3)
        paste(im, card(1180, 470), 760, 480, a3)
        paste(im, T_("سؤال تحدٍّ", 54, OM_RED, "kufi", False), 760, 340, a3)
        paste(im, text_block("لماذا يستطيع الإنسان هضم النشا، بينما لا يستطيع هضم السليلوز بإنزيماته الهاضمة؟", 44, 1000, INK, "naskh_b"),
              760, 500, a3)
        paste(im, T_("فكّرن فيه ... ونلتقي في الحصة القادمة", 34, WOOD, "naskh", False), 760, 640, a3 * ramp(t, at(T, p3, 0.75), at(T, p3, 0.85)))
        chef_in(im, t, T, [p3], "chef_spoon", 1620, 560, 400, 480)
    a4 = ramp(t, T.start(p4) - 0.3, T.start(p4) + 0.6)
    if a4 > 0:
        shade(im, 0.72 * a4, (18, 10, 8))
        paste(im, wood_sign("مخبز الطاقة – مدينة الحياة", 84, 60), W / 2, 390, a4)
        paste(im, T_("إعداد: أ. إمتثال العطابي", 60, GOLD_LT, "amiri"), W / 2, 560, a4 * ramp(t, T.start(p4) + 0.6, T.start(p4) + 1.4))
        paste(im, T_("الأحياء – الصف الحادي عشر – سلطنة عُمان  •  الوحدة الثانية: الجزيئات الحيوية  •  ٢-٢ الكربوهيدرات", 30, CREAM),
              W / 2, 660, a4 * ramp(t, T.start(p4) + 1.2, T.start(p4) + 2.0))
    return im


SCENES = {1: s01, 2: s02, 3: s03, 4: s04, 5: s05, 6: s06, 7: s07, 8: s08, 9: s09, 10: s10, 11: s11, 12: s12, 13: s13, 14: s14}
