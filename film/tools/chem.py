"""Scientifically exact carbohydrate drawings (cairo, dark 'molecular world' style).

Conventions (checked against the Grade-11 textbook figures 2-3, 2-4, 2-5, 2-6, 2-7, 2-8):
* Haworth projection of D-pyranoses: ring O back-right, C1 right, C2/C3 front, C4 left, C5 back-left; front edge bold.
* D-glucose substituents: C1 alpha OH down / beta OH up; C2 OH down; C3 OH up; C4 OH down; C5 CH2OH (C6) up.
* D-galactose differs only at C4 (OH up).
* flipped=True rotates a unit 180 deg about the in-plane left-right axis (used for every 2nd unit of cellulose and for
  the glucose of lactose) -> drawing y is mirrored and up/down substituents swap, ring O moves to the bottom.
* beta-D-fructofuranose in sucrose is drawn rotated 180 deg about the front-back axis (as in textbooks):
  C2 on the left with the glycosidic O down and C1H2OH up; C3 OH down; C4 OH up; C5 C6H2OH down.
Atom colours: C dark grey spheres (ring), O red, H white. On the dark stage C letters in group labels are light grey
so they stay readable.
"""
import math
import random

import cairo

from lib import (ALPHA_C, BETA_C, C_ATOM, CREAM, GOLD, GOLD_LT, H_ATOM, HBOND, O_ATOM, rgb)

BOND = (238, 228, 210)
C_TXT = (190, 190, 196)
NUM = GOLD_LT
FONT = "Inter"


def _font(ctx, size, bold=True):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(size)


ATOM_COL = {"O": O_ATOM, "H": H_ATOM, "C": C_TXT}


def group(ctx, x, y, label, size, vdir, anchor_char=0, alpha=1.0, color_override=None):
    """Draw a chemical group label like 'OH', 'HO', 'CH2OH', 'H'. The char at anchor_char is centred on x.
    vdir=+1: label sits below (x,y); -1: above; 0: vertically centred on y. Digits become subscripts."""
    _font(ctx, size)
    toks = []
    for ch in label:
        if ch.isdigit():
            toks.append((ch, True))
        else:
            toks.append((ch, False))
    widths = []
    for ch, sub in toks:
        _font(ctx, size * (0.62 if sub else 1.0))
        widths.append(ctx.text_extents(ch).x_advance)
    xs, acc = [], 0
    for w in widths:
        xs.append(acc)
        acc += w
    ax = xs[anchor_char] + widths[anchor_char] / 2
    cap = size * 0.72
    if vdir > 0:
        base = y + cap + size * 0.22
    elif vdir < 0:
        base = y - size * 0.22
    else:
        base = y + cap / 2
    for (ch, sub), x0, w in zip(toks, xs, widths):
        _font(ctx, size * (0.62 if sub else 1.0))
        col = color_override or ATOM_COL.get(ch, C_TXT)
        rgb(ctx, col, alpha)
        ctx.move_to(x - ax + x0, base + (size * 0.22 if sub else 0))
        ctx.show_text(ch)
    left = x - ax
    return (left, base - cap, left + acc, base)


def atom_ball(ctx, x, y, r, col, letter=None, alpha=1.0):
    g = cairo.RadialGradient(x - r * 0.35, y - r * 0.35, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, min(1, col[0] / 255 + 0.35), min(1, col[1] / 255 + 0.35), min(1, col[2] / 255 + 0.35), alpha)
    g.add_color_stop_rgba(1, col[0] / 255 * 0.7, col[1] / 255 * 0.7, col[2] / 255 * 0.7, alpha)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()
    rgb(ctx, (255, 255, 255), 0.55 * alpha)
    ctx.set_line_width(1.4)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.stroke()
    if letter:
        _font(ctx, r * 1.15)
        e = ctx.text_extents(letter)
        rgb(ctx, (255, 255, 255) if col != H_ATOM else (40, 40, 40), alpha)
        ctx.move_to(x - e.x_advance / 2, y + e.height / 2)
        ctx.show_text(letter)


def line(ctx, a, b, w=3.0, col=BOND, alpha=1.0, dash=None):
    rgb(ctx, col, alpha)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    if dash:
        ctx.set_dash(dash)
    ctx.move_to(*a)
    ctx.line_to(*b)
    ctx.stroke()
    ctx.set_dash([])


# --------------------------------------------------------------------------- Haworth pyranose
PYR = {"O5": (0.58, -0.50), "C1": (1.0, 0.0), "C2": (0.56, 0.50), "C3": (-0.56, 0.50), "C4": (-1.0, 0.0), "C5": (-0.58, -0.50)}
# substituent bond length (x s) pointing into the ring face is shorter so labels stay clear of the back bonds
INWARD = 0.36
OUTWARD = 0.60
PYR_ORDER = ["O5", "C1", "C2", "C3", "C4", "C5"]


def pyranose_subs(sugar="glc", anomer="a"):
    """(up, down) substituent labels for an unflipped D-pyranose."""
    s = {
        "C1": ("H", "OH") if anomer == "a" else ("OH", "H"),
        "C2": ("H", "OH"),
        "C3": ("OH", "H"),
        "C4": ("H", "OH") if sugar == "glc" else ("OH", "H"),
        "C5": ("CH2OH", "H"),
    }
    return s


def haworth(ctx, cx, cy, s, sugar="glc", anomer="a", flipped=False, show_H=True, omit=(), numbers=True,
            highlight=(), hl_col=HBOND, alpha=1.0, label_size=None, ring_balls=True, glow=None):
    """Draw a pyranose. Returns dict with absolute coords of ring atoms and substituent ends ('C1_up', 'C4_down'...).
    omit: iterable of 'C1_down' style keys whose substituent is not drawn (used for glycosidic links).
    highlight: keys like 'C1_down' to draw a glowing halo behind that group."""
    fy = -1 if flipped else 1
    P = {k: (cx + v[0] * s, cy + v[1] * s * fy) for k, v in PYR.items()}
    subs = pyranose_subs(sugar, anomer)
    L = 0.60 * s
    ls = label_size or s * 0.26
    out = dict(P)
    def blen(c, side):
        y = PYR[c][1]
        inward = (side == "up" and y > 0.1) or (side == "down" and y < -0.1)
        return (INWARD if inward else OUTWARD) * s
    for c, (up, down) in subs.items():
        for side, lab in (("up", up), ("down", down)):
            d = -1 if side == "up" else 1
            d *= fy
            out[f"{c}_{side}"] = (P[c][0], P[c][1] + d * blen(c, side))
    if glow:
        g = cairo.RadialGradient(cx, cy, s * 0.2, cx, cy, s * 1.6)
        g.add_color_stop_rgba(0, glow[0] / 255, glow[1] / 255, glow[2] / 255, 0.35 * alpha)
        g.add_color_stop_rgba(1, glow[0] / 255, glow[1] / 255, glow[2] / 255, 0)
        ctx.set_source(g)
        ctx.arc(cx, cy, s * 1.6, 0, 2 * math.pi)
        ctx.fill()
    for key in highlight:
        hx, hy = out[key]
        c = key.split("_")[0]
        side = key.split("_")[1]
        dd = (-1 if side == "up" else 1) * fy
        hy = hy + dd * ls * 0.55
        g = cairo.RadialGradient(hx, hy, 2, hx, hy, ls * 1.6)
        g.add_color_stop_rgba(0, hl_col[0] / 255, hl_col[1] / 255, hl_col[2] / 255, 0.85 * alpha)
        g.add_color_stop_rgba(1, hl_col[0] / 255, hl_col[1] / 255, hl_col[2] / 255, 0)
        ctx.set_source(g)
        ctx.arc(hx, hy, ls * 1.6, 0, 2 * math.pi)
        ctx.fill()
    # ring bonds (front edge thicker)
    for i in range(6):
        a, b = PYR_ORDER[i], PYR_ORDER[(i + 1) % 6]
        front = (PYR[a][1] * fy + PYR[b][1] * fy) / 2 > 0.1
        line(ctx, P[a], P[b], s * (0.085 if front else 0.035), BOND, alpha)
    # substituent bonds + labels
    for c, (up, down) in subs.items():
        for side, lab in (("up", up), ("down", down)):
            key = f"{c}_{side}"
            if key in omit:
                continue
            if lab == "H" and not show_H:
                continue
            if key == "C5_down":
                # sits directly over C3's inward OH in a Haworth drawing; omitted as in the textbook's simple form
                continue
            d = (-1 if side == "up" else 1) * fy
            end = out[key]
            short = lab == "H"
            stop = (end[0], P[c][1] + d * blen(c, side) * (0.82 if short else 1.0))
            line(ctx, P[c], stop, s * 0.03, BOND, alpha)
            left_side = P[c][0] < cx - 0.1 * s
            if lab == "OH":
                txt, anc = ("HO", 1) if left_side and c in ("C4",) else ("OH", 0)
            elif lab == "CH2OH":
                txt, anc = ("HOH2C", 4) if False else ("CH2OH", 0)
                if c == "C5":
                    # C6 is its own carbon: number it
                    if numbers:
                        _font(ctx, ls * 0.62)
                        rgb(ctx, NUM, alpha)
                        ctx.move_to(stop[0] - ls * 1.05, stop[1] + d * ls * 0.25 + (ls * 0.55 if d > 0 else -ls * 0.1))
                        ctx.show_text("6")
            else:
                txt, anc = lab, 0
            group(ctx, stop[0], stop[1], txt, ls * (0.85 if short else 1.0), d, anc, alpha)
    # ring atoms
    for k in PYR_ORDER:
        x, y = P[k]
        if k == "O5":
            atom_ball(ctx, x, y, s * 0.15, O_ATOM, "O", alpha)
        elif ring_balls:
            atom_ball(ctx, x, y, s * 0.085, C_ATOM, None, alpha)
    if numbers:
        _font(ctx, ls * 0.66)
        rgb(ctx, NUM, alpha)
        # numbers sit just outside the ring, clear of the vertical substituent bonds
        offs = {"C1": (0.17, -0.13), "C2": (0.17, 0.17), "C3": (-0.17, 0.17), "C4": (-0.17, -0.13), "C5": (-0.17, -0.13)}
        for k, (ox, oy) in offs.items():
            x, y = P[k]
            e = ctx.text_extents(k[1])
            ctx.move_to(x + ox * s - e.x_advance / 2, y + oy * s * fy + e.height / 2)
            ctx.show_text(k[1])
    return out


# --------------------------------------------------------------------------- fructofuranose (as in sucrose)
FUR_FLIP = {"O5": (0.0, -0.52), "C2": (-0.88, -0.10), "C3": (-0.54, 0.48), "C4": (0.54, 0.48), "C5": (0.88, -0.10)}


def fructose_in_sucrose(ctx, cx, cy, s, alpha=1.0, numbers=True, omit_c2_down=True, ls=None, highlight=()):
    P = {k: (cx + v[0] * s, cy + v[1] * s) for k, v in FUR_FLIP.items()}
    ls = ls or s * 0.26
    L = 0.60 * s
    order = ["O5", "C2", "C3", "C4", "C5"]
    subs = {"C2": ("CH2OH", "O*"), "C3": ("H", "OH"), "C4": ("OH", "H"), "C5": ("H", "CH2OH")}
    out = dict(P)
    def blen(c, side):
        return (INWARD if (side == "up" and FUR_FLIP[c][1] > 0.1) else OUTWARD) * s
    for c, (up, down) in subs.items():
        out[f"{c}_up"] = (P[c][0], P[c][1] - blen(c, "up"))
        out[f"{c}_down"] = (P[c][0], P[c][1] + blen(c, "down"))
    for key in highlight:
        hx, hy = out[key]
        g = cairo.RadialGradient(hx, hy, 2, hx, hy, ls * 1.6)
        g.add_color_stop_rgba(0, HBOND[0] / 255, HBOND[1] / 255, HBOND[2] / 255, 0.85 * alpha)
        g.add_color_stop_rgba(1, HBOND[0] / 255, HBOND[1] / 255, HBOND[2] / 255, 0)
        ctx.set_source(g)
        ctx.arc(hx, hy, ls * 1.6, 0, 2 * math.pi)
        ctx.fill()
    for i in range(5):
        a, b = order[i], order[(i + 1) % 5]
        front = (FUR_FLIP[a][1] + FUR_FLIP[b][1]) / 2 > 0.1
        line(ctx, P[a], P[b], s * (0.085 if front else 0.035), BOND, alpha)
    for c, (up, down) in subs.items():
        for side, lab in (("up", up), ("down", down)):
            if lab == "O*" and omit_c2_down:
                continue
            d = -1 if side == "up" else 1
            short = lab == "H"
            stop = (P[c][0], P[c][1] + d * blen(c, side) * (0.82 if short else 1.0))
            line(ctx, P[c], stop, s * 0.03, BOND, alpha)
            if lab == "CH2OH":
                num = "1" if c == "C2" else "6"
                txt = "HOH2C" if c == "C2" else "CH2OH"
                anc = 4 if c == "C2" else 0
                g = group(ctx, stop[0], stop[1], txt, ls, d, anc, alpha)
                if numbers:
                    _font(ctx, ls * 0.62)
                    rgb(ctx, NUM, alpha)
                    if c == "C2":
                        ctx.move_to(g[2] + 4, g[1] + ls * 0.3)
                    else:
                        ctx.move_to(g[0] - ls * 0.55, g[3])
                    ctx.show_text(num)
            elif lab == "OH" and c == "C4":
                group(ctx, stop[0], stop[1], "HO", ls, d, 1, alpha)
            else:
                group(ctx, stop[0], stop[1], lab, ls * (0.85 if short else 1.0), d, 0, alpha)
    for k in order:
        x, y = P[k]
        if k == "O5":
            atom_ball(ctx, x, y, s * 0.15, O_ATOM, "O", alpha)
        else:
            atom_ball(ctx, x, y, s * 0.085, C_ATOM, None, alpha)
    if numbers:
        _font(ctx, ls * 0.66)
        rgb(ctx, NUM, alpha)
        offs = {"C2": (-0.17, 0.14), "C3": (-0.17, 0.17), "C4": (-0.15, 0.20), "C5": (0.17, 0.14)}
        for k, (ox, oy) in offs.items():
            x, y = P[k]
            e = ctx.text_extents(k[1])
            ctx.move_to(x + ox * s - e.x_advance / 2, y + oy * s + e.height / 2)
            ctx.show_text(k[1])
    return out


# --------------------------------------------------------------------------- glycosidic link
def glyco_link(ctx, a, b, s, below=True, col=GOLD, alpha=1.0, progress=1.0, label=None, ls=None):
    """Bridge from ring carbon a to ring carbon b through an O placed below (or above) between them."""
    L = 0.60 * s
    d = 1 if below else -1
    pa = (a[0], a[1] + d * L)
    pb = (b[0], b[1] + d * L)
    o = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 + d * s * 0.12)
    pts = [a, pa, o, pb, b]
    # draw progressively along the polyline
    segs = list(zip(pts[:-1], pts[1:]))
    total = sum(math.dist(p, q) for p, q in segs)
    left = total * max(0.0, min(1.0, progress))
    rgb(ctx, col, alpha)
    ctx.set_line_width(s * 0.05)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*a)
    for p, q in segs:
        dd = math.dist(p, q)
        if left <= 0:
            break
        f = min(1.0, left / dd)
        ctx.line_to(p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
        left -= dd
    ctx.stroke()
    if progress > 0.45:
        atom_ball(ctx, o[0], o[1], s * 0.13, O_ATOM, "O", alpha * min(1, (progress - 0.45) * 4))
    if label and progress >= 1:
        _font(ctx, (ls or s * 0.24))
        e = ctx.text_extents(label)
        rgb(ctx, GOLD_LT, alpha)
        ctx.move_to(o[0] - e.x_advance / 2, o[1] + d * s * 0.42 + (e.height if d > 0 else 0))
        ctx.show_text(label)
    return o


# --------------------------------------------------------------------------- Fischer projection
def fischer(ctx, x, y, rows, s, alpha=1.0, numbers=True, highlight_rows=(), hl_col=HBOND, top="CHO", bottom="CH2OH",
            top_label=None):
    """rows: list of (left, right) for the chiral carbons, top to bottom. Returns carbon coordinates."""
    n = len(rows) + 2
    step = s * 0.62
    ys = [y + i * step for i in range(n)]
    ls = s * 0.24
    coords = []
    # vertical backbone
    line(ctx, (x, ys[0] + ls * 0.6), (x, ys[-1] - ls * 0.6), s * 0.03, BOND, alpha)
    for i, yy in enumerate(ys):
        coords.append((x, yy))
        if i in highlight_rows:
            g = cairo.RadialGradient(x, yy, 2, x, yy, s * 0.5)
            g.add_color_stop_rgba(0, hl_col[0] / 255, hl_col[1] / 255, hl_col[2] / 255, 0.6 * alpha)
            g.add_color_stop_rgba(1, hl_col[0] / 255, hl_col[1] / 255, hl_col[2] / 255, 0)
            ctx.set_source(g)
            ctx.arc(x, yy, s * 0.5, 0, 2 * math.pi)
            ctx.fill()
        if i == 0:
            if top == "CHO":
                # aldehyde drawn explicitly: H-C=O
                atom_ball(ctx, x, yy, s * 0.09, C_ATOM, None, alpha)
                rgb(ctx, BOND, alpha)
                ctx.set_line_width(s * 0.025)
                ctx.move_to(x + s * 0.08, yy - s * 0.035)
                ctx.line_to(x + s * 0.34, yy - s * 0.035)
                ctx.move_to(x + s * 0.08, yy + s * 0.035)
                ctx.line_to(x + s * 0.34, yy + s * 0.035)
                ctx.stroke()
                group(ctx, x + s * 0.44, yy, "O", ls, 0, 0, alpha)
                line(ctx, (x - s * 0.08, yy), (x - s * 0.3, yy), s * 0.025, BOND, alpha)
                group(ctx, x - s * 0.40, yy, "H", ls * 0.9, 0, 0, alpha)
            elif top == "CH2OH":
                group(ctx, x, yy, "CH2OH", ls, 0, 0, alpha)
            continue
        if i == n - 1:
            group(ctx, x, yy, bottom, ls, 0, 0, alpha)
            if numbers:
                _font(ctx, ls * 0.6)
                rgb(ctx, NUM, alpha)
                ctx.move_to(x - ls * 1.1, yy - ls * 0.5)
                ctx.show_text(str(i + 1))
            continue
        left, right = rows[i - 1]
        atom_ball(ctx, x, yy, s * 0.09, C_ATOM, None, alpha)
        if left == "=O":
            rgb(ctx, BOND, alpha)
            ctx.set_line_width(s * 0.025)
            for off in (-0.035, 0.035):
                ctx.move_to(x + s * 0.08, yy + s * off)
                ctx.line_to(x + s * 0.34, yy + s * off)
            ctx.stroke()
            group(ctx, x + s * 0.44, yy, "O", ls, 0, 0, alpha)
        else:
            line(ctx, (x - s * 0.08, yy), (x - s * 0.34, yy), s * 0.025, BOND, alpha)
            line(ctx, (x + s * 0.08, yy), (x + s * 0.34, yy), s * 0.025, BOND, alpha)
            group(ctx, x - s * 0.36 - (ls * 0.55 if left == "HO" else ls * 0.3), yy, left, ls, 0, len(left) - 1, alpha)
            group(ctx, x + s * 0.36 + (ls * 0.3), yy, right, ls, 0, 0, alpha)
        if numbers:
            _font(ctx, ls * 0.6)
            rgb(ctx, NUM, alpha)
            ctx.move_to(x + s * 0.06, yy - s * 0.1)
            ctx.show_text(str(i + 1))
    if numbers:
        _font(ctx, ls * 0.6)
        rgb(ctx, NUM, alpha)
        ctx.move_to(x - s * 0.02, ys[0] - s * 0.14)
        ctx.show_text("1")
    return coords


GLUCOSE_ROWS = [("H", "OH"), ("HO", "H"), ("H", "OH"), ("H", "OH")]
GALACTOSE_ROWS = [("H", "OH"), ("HO", "H"), ("HO", "H"), ("H", "OH")]
FRUCTOSE_ROWS = [("=O", ""), ("HO", "H"), ("H", "OH"), ("H", "OH")]   # C2 ketone, then C3..C5
RIBOSE_ROWS = [("H", "OH"), ("H", "OH"), ("H", "OH")]
ERYTHROSE_ROWS = [("H", "OH"), ("H", "OH")]
GLYCERALDEHYDE_ROWS = [("H", "OH")]


# --------------------------------------------------------------------------- schematic polymer tokens
def token(ctx, x, y, r, col, o_up=True, alpha=1.0, glow=True, rot=0.0):
    """Hexagon standing for one glucose unit; small red dot marks the ring O (top-right or bottom-right) so the
    180-degree flip of alternate beta units in cellulose is visible."""
    if glow:
        g = cairo.RadialGradient(x, y, r * 0.3, x, y, r * 1.9)
        g.add_color_stop_rgba(0, col[0] / 255, col[1] / 255, col[2] / 255, 0.35 * alpha)
        g.add_color_stop_rgba(1, col[0] / 255, col[1] / 255, col[2] / 255, 0)
        ctx.set_source(g)
        ctx.arc(x, y, r * 1.9, 0, 2 * math.pi)
        ctx.fill()
    pts = [(x + r * math.cos(math.radians(60 * k + 30) + rot), y + r * 0.78 * math.sin(math.radians(60 * k + 30) + rot)) for k in range(6)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    g = cairo.LinearGradient(x, y - r, x, y + r)
    g.add_color_stop_rgba(0, min(1, col[0] / 255 + 0.25), min(1, col[1] / 255 + 0.25), min(1, col[2] / 255 + 0.25), alpha)
    g.add_color_stop_rgba(1, col[0] / 255 * 0.65, col[1] / 255 * 0.65, col[2] / 255 * 0.65, alpha)
    ctx.set_source(g)
    ctx.fill_preserve()
    rgb(ctx, (255, 255, 255), 0.75 * alpha)
    ctx.set_line_width(max(1.2, r * 0.09))
    ctx.stroke()
    ox, oy = pts[5] if o_up else pts[0]   # top-right / bottom-right vertex
    atom_ball(ctx, ox, oy, r * 0.22, O_ATOM, None, alpha)


def link_line(ctx, a, b, w, col=BOND, alpha=1.0, dash=None):
    line(ctx, a, b, w, col, alpha, dash)


def helix_points(n, x0, y0, dx, R, phase, turn=6.0):
    pts = []
    for i in range(n):
        th = 2 * math.pi * i / turn + phase
        pts.append((x0 + i * dx, y0 + R * math.sin(th), math.cos(th)))
    return pts


def glycogen_tree(seed=7, depth=4, cx=0.0, cy=0.0, scale=1.0):
    """Generate a branched glucose tree: list of nodes (x, y, parent, kind) with kind 'a14' or 'a16'.
    Chains are short and branch often (glycogen); returns nodes and list of end-node indices."""
    rnd = random.Random(seed)
    nodes = [(cx, cy, -1, "core")]
    ends = []

    def chain(px, py, parent, ang, d, length):
        idx = parent
        x, y = px, py
        for k in range(length):
            x += math.cos(ang) * 38 * scale
            y += math.sin(ang) * 38 * scale
            nodes.append((x, y, idx, "a16" if k == 0 and d > 0 else "a14"))
            idx = len(nodes) - 1
            if d < depth and k in (1, 3) and rnd.random() < 0.8:
                chain(x, y, idx, ang + rnd.choice([-1, 1]) * rnd.uniform(0.55, 0.95), d + 1, rnd.randint(3, 5))
            ang += rnd.uniform(-0.12, 0.12)
        ends.append(idx)

    for k in range(5):
        chain(cx, cy, 0, 2 * math.pi * k / 5 + 0.3, 0, rnd.randint(4, 6))
    return nodes, ends
