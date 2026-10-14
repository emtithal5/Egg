"""Short version (≈6 min): 7 parts, vector environments only (no upscaled raster plates)."""
import functools
import math
import random

import cairo
from PIL import Image, ImageFilter

import env
from env import chef_arch, chef_medal
from lib import (ALPHA_C, BEIGE, BETA_C, C_ATOM, CREAM, GOLD, GOLD_LT, H, H_ATOM, HBOND, INK, O_ATOM, W, WOOD,
                 cairo_layer, card, ease, ease_out, glass, paste, ramp, rgb, shade, text_block, text_img, window,
                 wood_sign)
from scenes import (COLS, ROWS, GLY, T_, _amylopectin, _atp_icon, _ball, _cell_chains, _cellulose_haworth,
                    _condense_draw, _disacch, _dna_icon, _fibre, _fischer_glc_big, _glycogen_draw, _h_arrow,
                    _haworth_big, _helix, _microfibril, _organ, _plane_note, _plant_cell, _table_token, _two_lines,
                    _wall, _water, arrow, at, glow_spot, heading, label_chip, layer)
import chem


# ----------------------------------------------------------------------------- crisp molecular stage
@functools.lru_cache(None)
def _mol_bg2x():
    """Molecular-world background rendered at 2x so the slow drift only ever downsamples."""
    def draw(ctx):
        ctx.scale(2, 2)
        g = cairo.RadialGradient(W * 0.5, H * 0.45, 80, W * 0.5, H * 0.5, W * 0.75)
        g.add_color_stop_rgb(0, 0.20, 0.10, 0.22)
        g.add_color_stop_rgb(0.6, 0.10, 0.05, 0.13)
        g.add_color_stop_rgb(1, 0.04, 0.02, 0.06)
        ctx.set_source(g)
        ctx.paint()
        rnd = random.Random(3)
        for _ in range(150):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.5, 8)
            col = rnd.choice([GOLD_LT, (217, 140, 154), (160, 140, 230), (255, 255, 255)])
            gg = cairo.RadialGradient(x, y, 0, x, y, r * 2.2)
            gg.add_color_stop_rgba(0, col[0] / 255, col[1] / 255, col[2] / 255, rnd.uniform(0.15, 0.4))
            gg.add_color_stop_rgba(1, col[0] / 255, col[1] / 255, col[2] / 255, 0)
            ctx.set_source(gg)
            ctx.arc(x, y, r * 2.2, 0, 2 * math.pi)
            ctx.fill()
    return cairo_layer(2 * W, 2 * H, draw).convert("RGB")


def mol(t):
    bg = _mol_bg2x()
    z = 1.05 + 0.03 * (0.5 + 0.5 * math.sin(t * 0.12))   # >= 1.05 leaves room for the drift
    dx, dy = 30 * math.sin(t * 0.1), 18 * math.cos(t * 0.08)
    cw, ch = 2 * W / z, 2 * H / z
    box = (W - cw / 2 + dx, H - ch / 2 + dy, W + cw / 2 + dx, H + ch / 2 + dy)
    return bg.resize((W, H), Image.BILINEAR, box=box).convert("RGBA")


def envf(fn, *a, **k):
    return env.draw(fn, *a, **k)


def xblend(a, b, k):
    return b if k >= 1 else (a if k <= 0 else Image.blend(a, b, k))


def plaque(canvas, t, D, text):
    paste(canvas, wood_sign(text, 38, 28), W - 30, 26, window(t, 0.3, D - 0.2, 0.5), "tr")


def medal(canvas, t, T, cids):
    a = 0.0
    for c in cids:
        a = max(a, window(t, T.start(c) - 0.4, T.end(c) + 0.4, 0.4))
    if a > 0:
        paste(canvas, chef_medal(), 40, 40, a, "tl")


# ----------------------------------------------------------------------------- part 1
def p1(t, T):
    D = T.D
    s1, s2 = T.start("s01_01"), T.start("s01_02")
    k_souq, k_bak, k_chef = s1 + 5.0, s1 + 10.0, s2 - 0.3
    if t < k_souq + 0.7:
        g = ramp(t, k_souq - 2.4, k_souq - 0.6)
        im = envf(env.fort, t, 1.0 + 0.4 * ease(t / (k_souq + 0.7)), g, g)
        if t > k_souq:
            im = xblend(im, envf(env.souq, t, 0.0), ramp(t, k_souq, k_souq + 0.7))
    elif t < k_bak + 0.7:
        im = envf(env.souq, t, 0.75 * ease((t - k_souq) / (k_bak + 0.7 - k_souq)))
        if t > k_bak:
            im = xblend(im, envf(env.bakery, t, 1.0), ramp(t, k_bak, k_bak + 0.7))
    else:
        im = envf(env.bakery, t, 1.0 + 0.1 * ease((t - k_bak) / (D - k_bak)), 960, 520)
    # hanging bakery sign
    sa = window(t, k_bak + 0.2, k_chef + 0.5, 0.5)
    if sa > 0:
        drop = (1 - ease_out((t - k_bak - 0.2) / 0.9)) * -220
        sw = 2.5 * math.sin((t - k_bak) * 3.0) * math.exp(-(t - k_bak) * 0.7)
        paste(im, wood_sign("مخبز الطاقة", 92, 60).rotate(sw, Image.BICUBIC, expand=True), W / 2, 330 + drop, sa)
    # chef (opening shot) + title
    ca = ramp(t, k_chef, k_chef + 0.8)
    if ca > 0:
        shade(im, 0.25 * ca)
        paste(im, chef_arch(), 1420 + 120 * (1 - ca), 560, ca)
    ta = ramp(t, T.end("s01_02") - 0.6, T.end("s01_02") + 0.6)
    if ta > 0:
        paste(im, glass(980, 440, 34, (24, 12, 10), 0.75), 560, 560, ta)
        paste(im, wood_sign("مخبز الطاقة", 88, 60), 560, 440, ta)
        paste(im, T_("أسرار الكربوهيدرات", 60, GOLD_LT, "kufi"), 560, 585, ta)
        paste(im, T_("من السكر البسيط إلى التخزين والبناء", 42, CREAM, "kufi_m"), 560, 660, ta)
        paste(im, T_("الأحياء – الصف الحادي عشر  •  الدرس ٢-٢", 32, BEIGE, "naskh"), 560, 730, ta)
    return im


# ----------------------------------------------------------------------------- part 2
def p2(t, T):
    D = T.D
    im = mol(t)
    plaque(im, t, D, "السكريات الأحادية")
    c1, c2, c3, c4, c5 = "v02_01", "v02_02", "s05_01", "v02_03", "v02_04"
    # (1) C H O + general formula + three groups
    a = window(t, 0.2, T.start(c2) + 0.2, 0.5)
    if a > 0:
        for i, (sym, col, nm) in enumerate((("C", C_ATOM, "كربون"), ("H", H_ATOM, "هيدروجين"), ("O", O_ATOM, "أكسجين"))):
            ai = a * ramp(t, at(T, c1, 0.04 + i * 0.07), at(T, c1, 0.1 + i * 0.07))
            x = 1360 - i * 280
            paste(im, _ball(sym, col, 80), x, 300, ai)
            paste(im, T_(nm, 40), x, 420, ai)
        af = a * ramp(t, at(T, c1, 0.3), at(T, c1, 0.4))
        paste(im, T_("{(CH₂O)ₙ}", 120, GOLD_LT), W / 2, 590, af)
        paste(im, T_("الصيغة العامة الشائعة", 38, CREAM, "kufi_m"), W / 2, 690, af)
        for i, nm in enumerate(("السكريات الأحادية", "السكريات الثنائية", "عديدات التسكر")):
            ai = a * ramp(t, at(T, c1, 0.68 + i * 0.09), at(T, c1, 0.75 + i * 0.09))
            paste(im, label_chip(nm, 42, GOLD_LT), 1440 - i * 480, 830, ai)
    # (2) glucose: linear -> ring
    a = window(t, T.start(c2) - 0.2, T.start(c3) + 0.2, 0.5)
    if a > 0:
        fx = 1360   # RTL: linear form on the right, ring on the left
        paste(im, T_("{C₆H₁₂O₆}", 76, GOLD_LT), fx, 150, a * ramp(t, at(T, c2, 0.0), at(T, c2, 0.1)))
        paste(im, _fischer_glc_big(()), fx, 200, a * ramp(t, at(T, c2, 0.02), at(T, c2, 0.12)), "tc")
        k = ramp(t, at(T, c2, 0.3), at(T, c2, 0.5))
        if k > 0:
            glow_spot(im, fx, 245, 90, GOLD, a * k)
            glow_spot(im, fx + 125, 200 + 45 + 4 * 112, 90, O_ATOM, a * k)
            arr = layer(lambda c: arrow(c, (fx + 200, 200 + 45 + 4 * 112), (fx + 90, 260), GOLD_LT, 6, 22, 1, curve=-0.45))
            paste(im, arr, W / 2, H / 2, a * k)
            paste(im, _h_arrow(1060, 900), 940, 520, a * k)
        ar = a * ramp(t, at(T, c2, 0.5), at(T, c2, 0.62))
        if ar > 0:
            cx, cy, s = 520, 500, 190
            paste(im, _haworth_big("a", True), cx, cy, ar)
            ak = a * ramp(t, at(T, c2, 0.66), at(T, c2, 0.76))
            for key in ("C1", "C2", "C3", "C4", "C5"):
                px, py = chem.PYR[key]
                glow_spot(im, cx + px * s, cy + py * s, 55, GOLD, ak * 0.8)
            px, py = chem.PYR["O5"]
            glow_spot(im, cx + px * s, cy + py * s, 75, O_ATOM, ak)
            a6 = a * ramp(t, at(T, c2, 0.84), at(T, c2, 0.92))
            px, py = chem.PYR["C5"]
            glow_spot(im, cx + px * s, cy + py * s - 0.6 * s - 30, 90, HBOND, a6)
            paste(im, label_chip("حلقة: ٥ ذرات كربون + ذرة أكسجين", 36, GOLD_LT), cx, 800, ak)
            paste(im, label_chip("C6 خارج الحلقة", 36, (180, 235, 255)), cx, 880, a6)
    # (3) alpha vs beta
    a = window(t, T.start(c3) - 0.2, T.start(c5) + 0.2, 0.5)
    if a > 0:
        for x, anom, nm, col in ((1380, "a", "ألفا جلوكوز  {α}", ALPHA_C), (560, "b", "بيتا جلوكوز  {β}", BETA_C)):
            mol_ = _haworth_big(anom, True, "glc", 170, col, ("C1_down",) if anom == "a" else ("C1_up",))
            paste(im, mol_, x, 480, a)
            paste(im, T_(nm, 50, GOLD_LT, "kufi_m"), x, 160, a)
        paste(im, _plane_note(), W / 2, 480, a * ramp(t, T.start(c4) - 0.2, at(T, c4, 0.1)))
        paste(im, label_chip("{OH}  على C1 أسفل مستوى الحلقة", 38, (255, 190, 210)), 1380, 820,
              a * ramp(t, at(T, c4, 0.05), at(T, c4, 0.18)))
        paste(im, label_chip("{OH}  على C1 أعلى مستوى الحلقة", 38, (180, 220, 255)), 560, 820,
              a * ramp(t, at(T, c4, 0.6), at(T, c4, 0.72)))
        medal(im, t, T, [c3])
    # (4) functions
    a = window(t, T.start(c5) - 0.2, D, 0.5)
    if a > 0:
        heading(im, "وظيفتان رئيسيتان", a, 160)
        a1 = a * ramp(t, at(T, c5, 0.02), at(T, c5, 0.12))
        paste(im, label_chip("مصدر للطاقة", 46, GOLD_LT), 1380, 300, a1)
        paste(im, _table_token(ALPHA_C), 1380, 450, a1, scale=0.75)
        paste(im, label_chip("التنفس الخلوي: عدة خطوات", 34), 1380, 590, a1)
        paste(im, _atp_icon(), 1380, 720, a1)
        paste(im, T_("الطاقة المنطلقة تبني {ATP}", 34, GOLD_LT), 1380, 840, a1)
        a2 = a * ramp(t, at(T, c5, 0.35), at(T, c5, 0.45))
        paste(im, label_chip("وحدات بنائية", 46, GOLD_LT), 540, 330, a2)
        paste(im, label_chip("الريبوز {←} {RNA}  •  {ATP}", 38), 540, 470, a * ramp(t, at(T, c5, 0.5), at(T, c5, 0.6)))
        paste(im, label_chip("الديوكسي ريبوز {←} {DNA}", 38), 540, 590, a * ramp(t, at(T, c5, 0.78), at(T, c5, 0.88)))
        paste(im, _dna_icon(), 540, 760, a * ramp(t, at(T, c5, 0.78), at(T, c5, 0.88)))
    return im


# ----------------------------------------------------------------------------- part 3
def p3(t, T):
    D = T.D
    im = mol(t)
    plaque(im, t, D, "السكريات الثنائية")
    c1, c2, c3, c4, c5 = "s07_01", "s08_01", "s08_02", "v03_02", "v03_03"
    a = window(t, 0.2, T.start(c2) + 0.2, 0.5)
    if a > 0:
        j = ramp(t, at(T, c1, 0.3), at(T, c1, 0.75))
        paste(im, _table_token(ALPHA_C), 760 - 140 * (1 - j), 520, a)
        paste(im, _table_token((217, 140, 154)), 1160 + 140 * (1 - j), 520, a)
        if j > 0.98:
            glow_spot(im, 960, 520, 140, GOLD, a * window(t, at(T, c1, 0.75), T.start(c2), 0.2))
            chem_link = layer(lambda c: chem.line(c, (870, 520), (1050, 520), 8, GOLD), W, H)
            paste(im, chem_link, W / 2, H / 2, a)
            paste(im, label_chip("سكر ثنائي = وحدتان سكريتان مرتبطتان", 42, GOLD_LT), W / 2, 760, a)
        medal(im, t, T, [c1])
    # condensation / hydrolysis
    a = window(t, T.start(c2) - 0.3, T.start(c5) + 0.2, 0.5)
    if a > 0:
        approach = ramp(t, T.start(c2), at(T, c2, 0.3))
        leave = ramp(t, at(T, c2, 0.55), at(T, c2, 0.9))
        bond = ramp(t, T.start(c3) + 0.2, at(T, c3, 0.4))
        back = ramp(t, T.start(c4) - 0.6, at(T, c4, 0.45))
        brk = ramp(t, at(T, c4, 0.35), at(T, c4, 0.8))
        gap = 520 - 330 * approach + 330 * brk
        frame = layer(lambda c: _condense_draw(c, t, gap, leave, bond * (1 - brk), back, brk))
        paste(im, frame, W / 2, H / 2, a)
        paste(im, label_chip("مجموعتا هيدروكسيل {OH}", 38, (180, 235, 255)), W / 2, 200, a * window(t, at(T, c2, 0.1), at(T, c2, 0.6), 0.4))
        paste(im, label_chip("خروج جزيء ماء  {H₂O}", 40, (180, 235, 255)), W / 2, 200, a * window(t, at(T, c2, 0.6), at(T, c3, 0.3), 0.4))
        paste(im, label_chip("رابطة جلايكوسيدية {C–O–C}", 40, GOLD_LT), W / 2, 200, a * window(t, at(T, c3, 0.35), T.start(c4) - 0.4, 0.4))
        paste(im, wood_sign("التكثيف  {−H₂O}", 50, 40), W / 2, 905, a * window(t, T.start(c3), T.start(c4) - 0.2, 0.5))
        paste(im, wood_sign("التحلل المائي  {+H₂O}", 50, 40), W / 2, 905, a * window(t, T.start(c4) - 0.3, T.start(c5) + 0.2, 0.5))
        paste(im, label_chip("هذا ما يحدث عند الهضم", 40, GOLD_LT), W / 2, 200, a * window(t, at(T, c4, 0.5), T.start(c5) + 0.2, 0.4))
    # three disaccharides in sequence
    specs = [("المالتوز", "{α(1→4)}", "maltose", 0.0, 0.33), ("السكروز", "{α(1→2)β}", "sucrose", 0.33, 0.68),
             ("اللاكتوز (سكر الحليب)", "{β(1→4)}", "lactose", 0.68, 1.0)]
    for name, bond_s, key, f0, f1 in specs:
        a = window(t, at(T, c5, f0) - 0.3, (at(T, c5, f1) + 0.3) if f1 < 1 else D, 0.4)
        if a <= 0:
            continue
        heading(im, name, a, 160, 62)
        prog = ramp(t, at(T, c5, f0 + 0.03), at(T, c5, f0 + 0.15))
        paste(im, _disacch(key, round(prog * 24) / 24), W / 2, 540, a)
        paste(im, label_chip("رابطة " + bond_s, 44, GOLD_LT), W / 2, 860, a * ramp(t, at(T, c5, f0 + 0.12), at(T, c5, f0 + 0.18)))
    return im


# ----------------------------------------------------------------------------- part 4
def p4(t, T):
    D = T.D
    c1, c2, c3, c4 = "v04_01", "v04_02", "v04_03", "v04_04"
    k = T.start(c2) - 0.2
    if t < k + 0.7:
        im = envf(env.wheat_potato, t)
        paste(im, label_chip("القمح والبطاطس: مخازن نباتية للنشا", 42, GOLD_LT), W / 2, 150, ramp(t, 0.6, 1.4))
        medal(im, t, T, [c1])
        if t > k:
            im = xblend(im, mol(t), ramp(t, k, k + 0.7))
    else:
        im = mol(t)
    plaque(im, t, D, "النشا")
    a = window(t, k, T.start(c3) + 0.2, 0.5)
    if a > 0:
        paste(im, _plant_cell(), 1250, 520, a)
        for i, s in enumerate(("بوليمر كبير غير ذائب", "لا يؤثر في حركة الماء", "حبيبات في البذور والدرنات")):
            paste(im, label_chip(s, 40, GOLD_LT if i == 0 else CREAM), 460, 360 + i * 130,
                  a * ramp(t, at(T, c2, 0.05 + i * 0.3), at(T, c2, 0.15 + i * 0.3)))
    a = window(t, T.start(c3) - 0.2, D, 0.5)
    if a > 0:
        k3 = ramp(t, T.start(c4) - 0.3, at(T, c4, 0.12))
        heading(im, "النشا = أميلوز + أميلوبكتين", a * (1 - k3), 160, 54)
        y_am = 440 - 170 * k3
        paste(im, layer(lambda c: _helix(c, t, 1 - 0.45 * k3), W, 420), W / 2, y_am, a)
        paste(im, T_("الأميلوز", 50, (255, 190, 210), "kufi_m"), 1700, y_am - 130, a)
        for j, (s, f) in enumerate((("ألفا جلوكوز", 0.25), ("روابط {α(1→4)}", 0.45), ("غير متفرع – حلزون مدمج", 0.7))):
            paste(im, label_chip(s, 38), 1480 - j * 470, 780, a * (1 - k3) * ramp(t, at(T, c3, f), at(T, c3, f + 0.1)))
        if k3 > 0:
            paste(im, _amylopectin(), W / 2, 640, a * k3)
            paste(im, T_("الأميلوبكتين", 50, (255, 190, 210), "kufi_m"), 1700, 470, a * k3)
            paste(im, label_chip("روابط {α(1→4)} في السلاسل", 38), 1400, 925, a * ramp(t, at(T, c4, 0.25), at(T, c4, 0.35)))
            paste(im, label_chip("تفرعات {α(1→6)}", 38, GOLD_LT), 700, 925, a * ramp(t, at(T, c4, 0.55), at(T, c4, 0.65)))
    return im


# ----------------------------------------------------------------------------- part 5
def p5(t, T):
    D = T.D
    im = mol(t)
    plaque(im, t, D, "الجلايكوجين")
    c1, c2 = "s11_01", "s11_03"
    grow = ramp(t, T.start(c1), at(T, c1, 0.85))
    rel = ramp(t, at(T, c2, 0.3), at(T, c2, 0.85))
    paste(im, layer(lambda c: _glycogen_draw(c, grow, rel, t)), W / 2, H / 2, ramp(t, 0.2, 0.9))
    paste(im, label_chip("مخزن الجلوكوز في الحيوانات", 40, GOLD_LT), 330, 260, window(t, at(T, c1, 0.05), D, 0.4), "cl")
    paste(im, label_chip("تفرعات {α(1→6)} أكثر من الأميلوبكتين", 38), 330, 370, window(t, at(T, c1, 0.5), D, 0.4), "cl")
    ao = ramp(t, T.start(c2) - 0.2, at(T, c2, 0.1))
    paste(im, _organ("liver"), 1650, 330, ao, scale=0.6)
    paste(im, _organ("muscle"), 1650, 560, ao, scale=0.6)
    paste(im, T_("الكبد", 38, GOLD_LT, "kufi_m"), 1650, 440, ao)
    paste(im, T_("العضلات", 38, GOLD_LT, "kufi_m"), 1650, 660, ao)
    paste(im, label_chip("نهايات كثيرة {←} تحرير سريع للجلوكوز", 40, GOLD_LT), W / 2, 920, ramp(t, at(T, c2, 0.4), at(T, c2, 0.5)))
    return im


# ----------------------------------------------------------------------------- part 6
def p6(t, T):
    D = T.D
    c1, c2, c3, c4 = "v06_01", "v06_02", "v06_03", "s12_05"
    k_in = T.end(c1) + 0.3
    k_back = T.end(c4) + 0.1
    if t < k_in + 0.7:
        im = envf(env.basket_weave, t, 1.0 + 1.6 * ease(t / (k_in + 0.7)) ** 2)
        medal(im, t, T, [c1])
        paste(im, label_chip("سلة خوص من سعف النخيل", 42, GOLD_LT), W / 2, 920, window(t, 0.4, k_in, 0.4))
        if t > k_in:
            im = xblend(im, mol(t), ramp(t, k_in, k_in + 0.7))
    elif t > k_back:
        im = envf(env.basket_weave, t, 2.6 - 1.6 * ease((t - k_back) / max(0.1, D - k_back)))
        if t < k_back + 0.7:
            im = xblend(mol(t), im, ramp(t, k_back, k_back + 0.7))
        paste(im, label_chip("من الجزيء ... إلى سلة الخوص", 42, GOLD_LT), W / 2, 920, ramp(t, k_back + 0.5, k_back + 1.2))
    else:
        im = mol(t)
    plaque(im, t, D, "السليلوز")
    a = window(t, T.start(c2) - 0.3, T.start(c3) + 0.2, 0.5)
    if a > 0:
        flipk = ramp(t, at(T, c2, 0.45), at(T, c2, 0.75))
        heading(im, "بيتا جلوكوز بروابط {β(1→4)}", a, 160, 54)
        paste(im, _cellulose_haworth(round(flipk * 20) / 20), W / 2, 520, a)
        paste(im, label_chip("كل وحدة تنقلب {180°} عن جارتها", 38, (180, 220, 255)), W / 2, 830, a * ramp(t, at(T, c2, 0.5), at(T, c2, 0.6)))
        paste(im, label_chip("سلسلة مستقيمة غير متفرعة", 38, GOLD_LT), W / 2, 920, a * ramp(t, at(T, c2, 0.82), at(T, c2, 0.92)))
    a = window(t, T.start(c3) - 0.2, T.start(c4) + 0.2, 0.5)
    if a > 0:
        hb = ramp(t, at(T, c3, 0.05), at(T, c3, 0.4))
        heading(im, "روابط هيدروجينية بين السلاسل", a, 160, 54)
        paste(im, layer(lambda c: _cell_chains(c, hb, t)), W / 2, H / 2, a)
        paste(im, label_chip("جلايكوسيدية {β(1→4)}: داخل السلسلة", 36, GOLD_LT), 560, 900, a * ramp(t, at(T, c3, 0.45), at(T, c3, 0.55)))
        paste(im, label_chip("هيدروجينية: بين السلاسل", 36, (180, 235, 255)), 1400, 900, a * ramp(t, at(T, c3, 0.7), at(T, c3, 0.8)))
    a = window(t, T.start(c4) - 0.2, k_back + 0.6, 0.5)
    if a > 0:
        st = [ramp(t, at(T, c4, f), at(T, c4, f + 0.08)) for f in (0.0, 0.3, 0.55)]
        heading(im, "من الجزيء إلى الجدار الخلوي", a, 160, 54)
        paste(im, _microfibril(), 1450, 500, a * st[0])
        paste(im, label_chip("ليف دقيق: ٦٠–٧٠ سلسلة", 34, (180, 220, 255)), 1450, 740, a * st[0])
        paste(im, _h_arrow(1240, 1100), 1170, 500, a * st[1])
        paste(im, _fibre(), 950, 500, a * st[1])
        paste(im, label_chip("ألياف", 34), 950, 740, a * st[1])
        paste(im, _h_arrow(760, 640), 700, 500, a * st[2])
        paste(im, _wall(), 400, 500, a * st[2])
        paste(im, label_chip("طبقات متقاطعة في الجدار", 34), 400, 740, a * st[2])
        paste(im, label_chip("قوة شد عالية", 40, GOLD_LT), W / 2, 880, a * ramp(t, at(T, c4, 0.75), at(T, c4, 0.85)))
    return im


# ----------------------------------------------------------------------------- part 7
@functools.lru_cache(None)
def _bakery_soft():
    im = env.draw(env.bakery, 2.0, 1.05).convert("RGB").filter(ImageFilter.GaussianBlur(9))
    im = im.convert("RGBA")
    shade(im, 0.55, (20, 10, 18))
    return im


def p7(t, T):
    D = T.D
    c1, c2, c3, c4 = "s13_01", "s14_02", "s14_03", "s14_04"
    im = _bakery_soft().copy()
    plaque(im, t, D, "المقارنة والخاتمة")
    a = window(t, 0.2, T.start(c2) + 0.1, 0.5)
    if a > 0:
        x_lab, xs, y0, rh = 1720, [1330, 900, 470], 370, 128
        paste(im, glass(1780, 860, 30, (30, 16, 26), 0.86), 975, 585, a)
        for j, r in enumerate(ROWS):
            paste(im, T_(r, 40, GOLD_LT, "naskh_b"), x_lab, y0 + j * rh, a, "cr")
        for k, (nm, key, cells, col) in enumerate(COLS):
            ak = a * ramp(t, T.end(c1) + k * 1.2, T.end(c1) + k * 1.2 + 0.6)
            paste(im, T_(nm, 56, col, "kufi"), xs[k], 245, ak)
            for j, cell in enumerate(cells):
                img = _two_lines(cell) if "\n" in cell else text_img(cell, 38, CREAM, "naskh")
                paste(im, img, xs[k], y0 + j * rh, ak)
    a = window(t, T.start(c2) - 0.3, T.start(c3) + 0.1, 0.5)
    if a > 0:
        glow_spot(im, W / 2, 500, 420, GOLD, a * 0.5)
        paste(im, wood_sign("التركيب يحدد الوظيفة", 96, 64), W / 2, 500, a, scale=0.9 + 0.1 * ease_out(a))
    a = window(t, T.start(c3) - 0.3, T.start(c4) + 0.1, 0.5)
    if a > 0:
        paste(im, card(1080, 470), 610, 500, a)
        paste(im, T_("سؤال تحدٍّ", 54, (200, 16, 46), "kufi", False), 610, 360, a)
        paste(im, text_block("لماذا يستطيع الإنسان هضم النشا، بينما لا يستطيع هضم السليلوز بإنزيماته الهاضمة؟", 44, 920, INK, "naskh_b"), 610, 520, a)
        paste(im, chef_arch(), 1520, 560, a)          # closing shot of Chef Ruqayya
    a = ramp(t, T.start(c4) - 0.3, T.start(c4) + 0.5)
    if a > 0:
        shade(im, 0.55 * a, (18, 10, 8))
        paste(im, wood_sign("مخبز الطاقة – مدينة الحياة", 84, 60), W / 2, 400, a)
        paste(im, T_("إعداد: أ. إمتثال العطابي", 60, GOLD_LT, "amiri"), W / 2, 570, a * ramp(t, T.start(c4) + 0.5, T.start(c4) + 1.2))
        paste(im, T_("الأحياء – الصف الحادي عشر – سلطنة عُمان  •  الدرس ٢-٢ الكربوهيدرات", 30, CREAM), W / 2, 670,
              a * ramp(t, T.start(c4) + 1.0, T.start(c4) + 1.8))
    return im


PARTS = {1: p1, 2: p2, 3: p3, 4: p4, 5: p5, 6: p6, 7: p7}
