"""Vector Omani environments for the short version (no raster plates -> no pixelation).

Every scene is drawn per frame with cairo at the output resolution; camera moves are cairo transforms,
so zooming never upsamples pixels.
"""
import functools
import math
import random

import cairo
from PIL import Image, ImageFilter

from lib import GOLD, GOLD_LT, H, OM_GREEN, OM_RED, W, cairo_layer, rgb, round_rect

SAND_LIT = (214, 166, 108)
SAND_SH = (171, 122, 74)
MUD = (201, 154, 99)
MUD_SH = (160, 113, 70)
WOOD_C = (110, 64, 36)
WOOD_D = (70, 40, 22)


def lin(ctx, x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c in stops:
        g.add_color_stop_rgba(o, c[0] / 255, c[1] / 255, c[2] / 255, c[3] if len(c) > 3 else 1)
    ctx.set_source(g)


def rad(ctx, x, y, r0, r1, stops):
    g = cairo.RadialGradient(x, y, r0, x, y, r1)
    for o, c in stops:
        g.add_color_stop_rgba(o, c[0] / 255, c[1] / 255, c[2] / 255, c[3] if len(c) > 3 else 1)
    ctx.set_source(g)


def camera(ctx, zoom, fx, fy):
    """Zoom about focus point (fx, fy) in design space."""
    ctx.translate(fx, fy)
    ctx.scale(zoom, zoom)
    ctx.translate(-fx, -fy)


# ------------------------------------------------------------------ props
def palm(ctx, x, y, h, col, lean=0.0, sway=0.0, fronds=11):
    top = (x + lean * h, y - h)
    rgb(ctx, tuple(int(c * 0.8) for c in col))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    # tapered trunk
    for k in range(14):
        f0, f1 = k / 14, (k + 1) / 14
        p0 = (x + (top[0] - x) * f0 + lean * h * 0.12 * math.sin(f0 * math.pi), y + (top[1] - y) * f0)
        p1 = (x + (top[0] - x) * f1 + lean * h * 0.12 * math.sin(f1 * math.pi), y + (top[1] - y) * f1)
        ctx.set_line_width(h * (0.06 - 0.025 * f0))
        ctx.move_to(*p0)
        ctx.line_to(*p1)
        ctx.stroke()
    rgb(ctx, col)
    for i in range(fronds):
        a = -math.pi / 2 + (i - (fronds - 1) / 2) * (math.pi * 1.35 / fronds) + sway * (1 + 0.3 * math.sin(i))
        L = h * (0.5 + 0.1 * math.cos(i * 1.7))
        droop = L * 0.45
        pts = []
        for k in range(13):
            f = k / 12
            px = top[0] + math.cos(a) * L * f
            py = top[1] + math.sin(a) * L * f * 0.8 + droop * f * f
            pts.append((px, py))
        ctx.set_line_width(h * 0.012)
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        ctx.stroke()
        for k in range(1, 12):
            px, py = pts[k]
            qx, qy = pts[k + 1]
            dx, dy = qx - px, qy - py
            nn = math.hypot(dx, dy) or 1
            nx, ny = -dy / nn, dx / nn
            ll = h * 0.11 * math.sin(k / 12 * math.pi) + h * 0.02
            ctx.set_line_width(h * 0.016)
            for sd in (-1, 1):
                ctx.move_to(px, py)
                ctx.line_to(px + (nx * sd * 0.8 + dx / nn * 0.6) * ll, py + (ny * sd * 0.8 + dy / nn * 0.6) * ll + ll * 0.25)
            ctx.stroke()


def lantern(ctx, x, y, s, glow=1.0, chain=120):
    rgb(ctx, (60, 40, 25))
    ctx.set_line_width(2)
    ctx.move_to(x, y - chain)
    ctx.line_to(x, y - s * 0.9)
    ctx.stroke()
    rad(ctx, x, y + s * 0.2, 0, s * 4, [(0, (255, 190, 90, 0.55 * glow)), (1, (255, 160, 60, 0))])
    ctx.arc(x, y + s * 0.2, s * 4, 0, 2 * math.pi)
    ctx.fill()
    # body
    ctx.move_to(x - s * 0.45, y - s * 0.6)
    ctx.line_to(x + s * 0.45, y - s * 0.6)
    ctx.line_to(x + s * 0.6, y + s * 0.6)
    ctx.line_to(x - s * 0.6, y + s * 0.6)
    ctx.close_path()
    lin(ctx, x - s, 0, x + s, 0, [(0, (255, 200, 110)), (0.5, (255, 235, 170)), (1, (230, 150, 60))])
    ctx.fill()
    rgb(ctx, (120, 70, 30))
    ctx.set_line_width(s * 0.08)
    for k in (-0.2, 0.2):
        ctx.move_to(x + k * s * 1.4, y - s * 0.6)
        ctx.line_to(x + k * s * 1.9, y + s * 0.6)
    ctx.stroke()
    ctx.move_to(x - s * 0.7, y - s * 0.6)
    ctx.line_to(x + s * 0.7, y - s * 0.6)
    ctx.line_to(x, y - s * 1.1)
    ctx.close_path()
    lin(ctx, x - s, 0, x + s, 0, [(0, (150, 85, 35)), (0.5, (200, 125, 55)), (1, (120, 65, 25))])
    ctx.fill()
    ctx.rectangle(x - s * 0.7, y + s * 0.6, s * 1.4, s * 0.18)
    ctx.fill()


def pointed_arch(ctx, x0, x1, y_spring, y_base, peak_k=0.75):
    """Omani pointed arch opening path (x0..x1, springing line y_spring, base y_base)."""
    w = x1 - x0
    xm = (x0 + x1) / 2
    peak = y_spring - w * peak_k
    ctx.move_to(x0, y_base)
    ctx.line_to(x0, y_spring)
    ctx.curve_to(x0, y_spring - w * 0.45, xm - w * 0.15, peak + w * 0.08, xm, peak)
    ctx.curve_to(xm + w * 0.15, peak + w * 0.08, x1, y_spring - w * 0.45, x1, y_spring)
    ctx.line_to(x1, y_base)
    ctx.close_path()


def merlons(ctx, x0, x1, y, size, col):
    n = max(1, int((x1 - x0) / (size * 1.6)))
    step = (x1 - x0) / n
    rgb(ctx, col)
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        ctx.move_to(cx - size * 0.5, y)
        ctx.line_to(cx - size * 0.5, y - size * 0.7)
        ctx.line_to(cx, y - size * 1.25)
        ctx.line_to(cx + size * 0.5, y - size * 0.7)
        ctx.line_to(cx + size * 0.5, y)
        ctx.close_path()
        ctx.fill()


def oman_flag(ctx, x, y, w, wave):
    h = w * 0.5
    def wp(px, py):
        return px, py + math.sin(px / w * 5 + wave) * w * 0.04
    def quad(xa, xb, ya, yb, col):
        rgb(ctx, col)
        ctx.move_to(*wp(xa, ya))
        for k in range(1, 9):
            ctx.line_to(*wp(xa + (xb - xa) * k / 8, ya))
        ctx.line_to(*wp(xb, yb))
        for k in range(7, -1, -1):
            ctx.line_to(*wp(xa + (xb - xa) * k / 8, yb))
        ctx.close_path()
        ctx.fill()
    quad(x, x + w * 0.27, y, y + h, OM_RED)
    quad(x + w * 0.27, x + w, y, y + h / 3, (250, 250, 250))
    quad(x + w * 0.27, x + w, y + h / 3, y + 2 * h / 3, OM_RED)
    quad(x + w * 0.27, x + w, y + 2 * h / 3, y + h, OM_GREEN)
    # simplified national emblem mark (white, top of the red hoist band)
    rgb(ctx, (250, 250, 250))
    ctx.arc(*wp(x + w * 0.135, y + h * 0.17), w * 0.045, 0, 2 * math.pi)
    ctx.fill()
    rgb(ctx, (90, 70, 50))
    ctx.set_line_width(4)
    ctx.move_to(x, y - 10)
    ctx.line_to(x, y + h * 2.2)
    ctx.stroke()


# ------------------------------------------------------------------ 1. fort at dawn
def fort(ctx, t, zoom=1.0, gate_open=0.0, light=0.0):
    rnd = random.Random(4)
    ctx.save()
    # sky (no camera: infinite distance)
    lin(ctx, 0, 0, 0, 760, [(0, (42, 52, 104)), (0.45, (178, 110, 128)), (0.8, (243, 167, 107)), (1, (255, 217, 160))])
    ctx.paint()
    rad(ctx, 1380, 650, 10, 420, [(0, (255, 240, 200, 0.95)), (0.25, (255, 205, 140, 0.55)), (1, (255, 180, 120, 0))])
    ctx.paint()
    for i in range(6):  # thin clouds
        cy = 160 + i * 55
        cx = (220 + i * 330 + t * 6 * (1 + i % 3)) % 2300 - 200
        rgb(ctx, (255, 200, 170), 0.18)
        ctx.save()
        ctx.translate(cx, cy)
        ctx.scale(1, 0.18)
        ctx.arc(0, 0, 260, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
    # layered parallax: far things move less
    def layer(depth):
        ctx.restore()
        ctx.save()
        z = 1 + (zoom - 1) * depth
        camera(ctx, z, 960, 700)
    layer(0.15)
    for col, base, amp, seed in (((160, 106, 124), 600, 150, 1), ((128, 84, 104), 640, 90, 2)):
        r = random.Random(seed)
        rgb(ctx, col)
        ctx.move_to(-200, 900)
        x = -200
        while x < 2200:
            ctx.line_to(x, base - r.uniform(0.2, 1) * amp)
            x += r.uniform(60, 160)
        ctx.line_to(2200, 900)
        ctx.close_path()
        ctx.fill()
    layer(0.35)
    for i in range(16):
        px = -100 + i * 140 + rnd.uniform(-30, 30)
        palm(ctx, px, 700, rnd.uniform(190, 260), (84, 62, 60), rnd.uniform(-0.15, 0.15), 0.03 * math.sin(t + i))
    layer(1.0)
    # ground
    lin(ctx, 0, 780, 0, 1100, [(0, SAND_LIT), (1, SAND_SH)])
    ctx.rectangle(-400, 790, 2800, 600)
    ctx.fill()
    # curtain walls
    for x0, x1 in ((-300, 590), (1330, 2300)):
        lin(ctx, 0, 520, 0, 900, [(0, MUD), (1, MUD_SH)])
        ctx.rectangle(x0, 640, x1 - x0, 260)
        ctx.fill()
        merlons(ctx, x0, x1, 640, 30, MUD)
    # towers (cylinders)
    for cx in (640, 1280):
        lin(ctx, cx - 110, 0, cx + 110, 0, [(0, MUD_SH), (0.35, (226, 178, 120)), (1, (140, 98, 60))])
        ctx.rectangle(cx - 110, 300, 220, 600)
        ctx.fill()
        merlons(ctx, cx - 115, cx + 115, 300, 34, (214, 168, 112))
        rgb(ctx, (90, 58, 38))
        for wy in (420, 560):
            ctx.rectangle(cx - 8, wy, 16, 46)
        ctx.fill()
    # gatehouse
    lin(ctx, 0, 380, 0, 900, [(0, (220, 172, 116)), (1, MUD_SH)])
    ctx.rectangle(740, 400, 440, 500)
    ctx.fill()
    merlons(ctx, 740, 1180, 400, 36, (226, 180, 124))
    # decorative band over gate
    rgb(ctx, (150, 100, 60))
    ctx.rectangle(760, 480, 400, 10)
    ctx.fill()
    # gate recess + doors
    pointed_arch(ctx, 830, 1090, 690, 900, 0.62)
    rgb(ctx, (120, 80, 50))
    ctx.fill()
    pointed_arch(ctx, 855, 1065, 700, 900, 0.62)
    ctx.save()
    ctx.clip()
    rad(ctx, 960, 760, 10, 260, [(0, (255, 236, 180)), (1, (250, 190, 110))])
    ctx.paint()
    g = gate_open
    for side in (-1, 1):
        x_hinge = 855 if side < 0 else 1065
        w = 105 * (1 - 0.85 * g)
        x0 = x_hinge if side < 0 else x_hinge - w
        lin(ctx, x0, 0, x0 + w, 0, [(0, WOOD_D), (0.5, WOOD_C), (1, WOOD_D)])
        ctx.rectangle(x0, 560, w, 340)
        ctx.fill()
        rgb(ctx, (60, 34, 18))
        ctx.set_line_width(2)
        for k in range(1, 5):
            ctx.move_to(x0 + w * k / 5, 560)
            ctx.line_to(x0 + w * k / 5, 900)
        ctx.stroke()
        rgb(ctx, GOLD_LT)
        for yy in range(720, 890, 34):
            for k in range(1, 4):
                ctx.arc(x0 + w * k / 4, yy, 3.2, 0, 2 * math.pi)
                ctx.fill()
    ctx.restore()
    # flag on right tower
    oman_flag(ctx, 1290, 200, 120, t * 3)
    # light spilling out of the gate
    if light > 0:
        rad(ctx, 960, 820, 20, 700, [(0, (255, 225, 160, 0.75 * light)), (1, (255, 200, 130, 0))])
        ctx.paint()
    layer(1.6)
    palm(ctx, 120, 1120, 520, (40, 60, 38), 0.12, 0.04 * math.sin(t * 0.8))
    palm(ctx, 1840, 1140, 560, (36, 56, 34), -0.1, 0.04 * math.sin(t * 0.7 + 1))
    ctx.restore()


# ------------------------------------------------------------------ 2. souq: row of arched shopfronts
def souq(ctx, t, pan=0.0):
    """Traditional souq street; pan (0..1) slides the camera sideways (tracking shot)."""
    ctx.save()
    ctx.translate(-pan * 900, 0)
    rnd = random.Random(21)
    # back wall with shopfronts
    lin(ctx, 0, 0, 0, 900, [(0, (150, 104, 66)), (1, (205, 158, 104))])
    ctx.rectangle(-200, 0, 3400, 900)
    ctx.fill()
    for _ in range(600):
        x, y, r = rnd.uniform(-200, 3200), rnd.uniform(0, 880), rnd.uniform(2, 8)
        rgb(ctx, (120, 80, 50) if rnd.random() < 0.5 else (235, 195, 150), rnd.uniform(0.05, 0.12))
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.fill()
    for k in range(8):
        x0 = 40 + k * 380
        # shop opening
        pointed_arch(ctx, x0, x0 + 300, 420, 860, 0.45)
        lin(ctx, 0, 250, 0, 860, [(0, (60, 36, 22)), (1, (96, 60, 36))])
        ctx.fill()
        rad(ctx, x0 + 150, 560, 10, 240, [(0, (255, 190, 110, 0.35)), (1, (255, 170, 90, 0))])
        pointed_arch(ctx, x0, x0 + 300, 420, 860, 0.45)
        ctx.fill()
        pointed_arch(ctx, x0, x0 + 300, 420, 860, 0.45)
        rgb(ctx, (232, 196, 146))
        ctx.set_line_width(12)
        ctx.stroke()
        # shelves inside with jars / bolts of cloth
        for sy in (520, 650):
            rgb(ctx, (120, 72, 40))
            ctx.rectangle(x0 + 20, sy, 260, 10)
            ctx.fill()
            xx = x0 + 34
            while xx < x0 + 270:
                col = rnd.choice([(190, 110, 60), (160, 70, 50), (200, 60, 50), (60, 110, 70), (210, 170, 90)])
                hh = rnd.uniform(40, 80)
                rgb(ctx, col)
                round_rect(ctx, xx, sy - hh, 24, hh, 8)
                ctx.fill()
                xx += 34
        # hanging fabric with Omani pattern
        if k % 2 == 0:
            fx = x0 + 300 + 20
            for j, col in enumerate(((180, 30, 40), (30, 110, 60), (40, 70, 150))):
                lin(ctx, fx + j * 18, 0, fx + j * 18 + 16, 0, [(0, tuple(int(c * 0.7) for c in col)), (0.5, col), (1, tuple(int(c * 0.7) for c in col))])
                ctx.rectangle(fx + j * 18, 330, 16, 300 - j * 30)
                ctx.fill()
                rgb(ctx, GOLD_LT, 0.8)
                for yy in range(350, 620 - j * 30, 30):
                    ctx.move_to(fx + j * 18 + 8, yy)
                    ctx.line_to(fx + j * 18 + 13, yy + 8)
                    ctx.line_to(fx + j * 18 + 8, yy + 16)
                    ctx.line_to(fx + j * 18 + 3, yy + 8)
                    ctx.close_path()
                    ctx.fill()
    # palm-trunk ceiling beams and overhang
    lin(ctx, 0, 180, 0, 260, [(0, (80, 48, 26)), (1, (120, 74, 40))])
    ctx.rectangle(-200, 200, 3400, 50)
    ctx.fill()
    for k in range(40):
        lin(ctx, 0, 0, 0, 200, [(0, (70, 42, 22)), (1, (110, 66, 36))])
        ctx.rectangle(-200 + k * 90, 0, 34, 200)
        ctx.fill()
    for k in range(9):
        lantern(ctx, 230 + k * 380, 330 + 6 * math.sin(t * 1.3 + k), 34, 0.85 + 0.15 * math.sin(t * 6 + k), 90)
    # floor
    lin(ctx, 0, 860, 0, H, [(0, (196, 150, 98)), (1, (150, 108, 66))])
    ctx.rectangle(-200, 860, 3400, 300)
    ctx.fill()
    rgb(ctx, (120, 84, 52), 0.35)
    ctx.set_line_width(2)
    for k in range(60):
        ctx.move_to(-200 + k * 60, 860)
        ctx.line_to(-200 + k * 60 - 80, H)
    ctx.stroke()
    # goods in front of the shops
    for k in range(8):
        x0 = 40 + k * 380
        stall(ctx, x0 + 90, 930, 0.95, (k * 0.37) % 1)
        stall(ctx, x0 + 230, 950, 0.85, (k * 0.61 + 0.3) % 1)
    ctx.restore()
    rad(ctx, 960, 540, 300, 1150, [(0, (0, 0, 0, 0)), (1, (30, 14, 6, 0.55))])
    ctx.paint()


def stall(ctx, x, y, s, r):
    # basket of dates or grain sack or clay pot
    kind = int(r * 3)
    if kind == 0:
        rgb(ctx, (150, 105, 55))
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(1, 0.45)
        ctx.arc(0, 0, 120 * s, 0, math.pi)
        ctx.restore()
        ctx.fill()
        rr = random.Random(int(r * 1000))
        for _ in range(26):
            dx, dy = rr.uniform(-100, 100) * s, rr.uniform(-34, 4) * s
            rgb(ctx, rr.choice([(110, 40, 25), (140, 60, 30), (90, 30, 20)]))
            ctx.save()
            ctx.translate(x + dx, y + dy)
            ctx.scale(1, 0.6)
            ctx.arc(0, 0, 16 * s, 0, 2 * math.pi)
            ctx.restore()
            ctx.fill()
        rgb(ctx, (110, 70, 35))
        ctx.set_line_width(max(1, 3 * s))
        for k in range(5):
            ctx.move_to(x - 110 * s + k * 50 * s, y)
            ctx.line_to(x - 90 * s + k * 45 * s, y + 50 * s)
        ctx.stroke()
    elif kind == 1:
        lin(ctx, x - 90 * s, 0, x + 90 * s, 0, [(0, (190, 160, 115)), (0.5, (235, 215, 175)), (1, (170, 140, 100))])
        ctx.move_to(x - 85 * s, y + 60 * s)
        ctx.curve_to(x - 110 * s, y - 60 * s, x - 60 * s, y - 120 * s, x, y - 110 * s)
        ctx.curve_to(x + 60 * s, y - 120 * s, x + 110 * s, y - 60 * s, x + 85 * s, y + 60 * s)
        ctx.close_path()
        ctx.fill()
        rgb(ctx, (245, 235, 210))
        ctx.save()
        ctx.translate(x, y - 108 * s)
        ctx.scale(1, 0.3)
        ctx.arc(0, 0, 60 * s, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
    else:
        lin(ctx, x - 70 * s, 0, x + 70 * s, 0, [(0, (140, 70, 40)), (0.45, (205, 120, 70)), (1, (120, 60, 35))])
        ctx.move_to(x - 30 * s, y - 130 * s)
        ctx.curve_to(x - 100 * s, y - 80 * s, x - 100 * s, y + 40 * s, x - 40 * s, y + 60 * s)
        ctx.line_to(x + 40 * s, y + 60 * s)
        ctx.curve_to(x + 100 * s, y + 40 * s, x + 100 * s, y - 80 * s, x + 30 * s, y - 130 * s)
        ctx.close_path()
        ctx.fill()


# ------------------------------------------------------------------ 3. bakery interior
def bakery(ctx, t, zoom=1.0, fx=960, fy=560):
    ctx.save()
    camera(ctx, zoom, fx, fy)
    rnd = random.Random(11)
    lin(ctx, 0, 0, 0, 860, [(0, (186, 136, 92)), (1, (222, 178, 128))])
    ctx.rectangle(-300, -300, W + 600, 1200)
    ctx.fill()
    for _ in range(420):  # plaster texture
        x, y, r = rnd.uniform(-200, W + 200), rnd.uniform(-200, 860), rnd.uniform(2, 9)
        rgb(ctx, (150, 104, 66) if rnd.random() < 0.5 else (240, 205, 160), rnd.uniform(0.05, 0.14))
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.fill()
    # ceiling beams
    for k in range(9):
        lin(ctx, 0, -10, 0, 40, [(0, WOOD_D), (1, WOOD_C)])
        ctx.rectangle(-300 + k * 290, -40, 70, 90)
        ctx.fill()
    # window arch with daylight
    pointed_arch(ctx, 1240, 1540, 300, 560, 0.5)
    lin(ctx, 0, 140, 0, 560, [(0, (255, 236, 196)), (1, (255, 214, 150))])
    ctx.fill()
    for k in range(3):
        rgb(ctx, (120, 80, 50))
        ctx.rectangle(1240 + k * 150 - 6, 180, 12, 380)
        ctx.fill()
    rgb(ctx, (255, 235, 190), 0.12)
    ctx.move_to(1240, 300)
    ctx.line_to(1540, 300)
    ctx.line_to(1700, 900)
    ctx.line_to(1150, 900)
    ctx.close_path()
    ctx.fill()
    # shelves with jars
    for sy in (330, 520):
        lin(ctx, 0, sy, 0, sy + 24, [(0, WOOD_C), (1, WOOD_D)])
        ctx.rectangle(560, sy, 600, 24)
        ctx.fill()
        x = 590
        while x < 1130:
            hgt = rnd.uniform(70, 130)
            wdt = rnd.uniform(40, 70)
            col = rnd.choice([(170, 90, 50), (200, 120, 70), (150, 80, 45), (120, 140, 120)])
            lin(ctx, x - wdt / 2, 0, x + wdt / 2, 0, [(0, tuple(int(c * 0.7) for c in col)), (0.4, col), (1, tuple(int(c * 0.6) for c in col))])
            ctx.move_to(x - wdt * 0.25, sy - hgt)
            ctx.curve_to(x - wdt * 0.8, sy - hgt * 0.7, x - wdt * 0.7, sy, x - wdt * 0.4, sy)
            ctx.line_to(x + wdt * 0.4, sy)
            ctx.curve_to(x + wdt * 0.7, sy, x + wdt * 0.8, sy - hgt * 0.7, x + wdt * 0.25, sy - hgt)
            ctx.close_path()
            ctx.fill()
            x += wdt + rnd.uniform(14, 30)
    # domed clay oven (left) with fire
    lin(ctx, 60, 0, 520, 0, [(0, (120, 66, 36)), (0.45, (190, 112, 62)), (1, (110, 60, 32))])
    ctx.move_to(40, 900)
    ctx.curve_to(40, 380, 540, 380, 540, 900)
    ctx.close_path()
    ctx.fill()
    for k in range(6):  # clay courses
        rgb(ctx, (90, 48, 26), 0.35)
        ctx.set_line_width(3)
        yy = 520 + k * 62
        ctx.move_to(60, yy + 30)
        ctx.curve_to(200, yy - 20, 380, yy - 20, 520, yy + 30)
        ctx.stroke()
    pointed_arch(ctx, 190, 390, 760, 900, 0.5)
    rgb(ctx, (40, 16, 8))
    ctx.fill()
    flick = 0.85 + 0.15 * math.sin(t * 11) * math.sin(t * 7.3)
    rad(ctx, 290, 880, 5, 160 * flick, [(0, (255, 240, 170)), (0.4, (255, 150, 40)), (1, (255, 80, 20, 0))])
    pointed_arch(ctx, 190, 390, 760, 900, 0.5)
    ctx.fill()
    for i in range(7):  # flame tongues
        fx_ = 220 + i * 25
        hgt = 60 + 40 * abs(math.sin(t * 6 + i * 1.7))
        lin(ctx, 0, 900 - hgt, 0, 900, [(0, (255, 220, 120, 0)), (0.5, (255, 170, 60, 0.9)), (1, (255, 110, 30, 0.9))])
        ctx.move_to(fx_ - 14, 900)
        ctx.curve_to(fx_ - 10, 900 - hgt * 0.6, fx_ + 6, 900 - hgt * 0.7, fx_ + 2, 900 - hgt)
        ctx.curve_to(fx_ + 14, 900 - hgt * 0.5, fx_ + 16, 900 - hgt * 0.2, fx_ + 14, 900)
        ctx.close_path()
        ctx.fill()
    rad(ctx, 290, 860, 20, 520, [(0, (255, 170, 80, 0.35 * flick)), (1, (255, 140, 60, 0))])
    ctx.paint()
    lantern(ctx, 880, 170, 40, 0.9 + 0.1 * math.sin(t * 5), 200)
    # table
    lin(ctx, 0, 820, 0, 1080, [(0, (128, 76, 42)), (1, (82, 46, 24))])
    ctx.rectangle(-300, 830, W + 600, 400)
    ctx.fill()
    rgb(ctx, (60, 32, 16), 0.4)
    ctx.set_line_width(2)
    for k in range(6):
        y = 860 + k * 40
        ctx.move_to(-300, y)
        ctx.curve_to(600, y + 8, 1300, y - 8, W + 300, y)
    ctx.stroke()
    # breads, dates, wheat, flour
    for i, (bx, by) in enumerate(((640, 905), (790, 930), (700, 965))):
        ctx.save()
        ctx.translate(bx, by)
        ctx.scale(1, 0.32)
        rad(ctx, 0, 0, 10, 120, [(0, (238, 205, 150)), (0.85, (214, 165, 100)), (1, (170, 115, 60))])
        ctx.arc(0, 0, 120, 0, 2 * math.pi)
        ctx.fill()
        r2 = random.Random(i)
        for _ in range(14):
            rgb(ctx, (150, 90, 40), 0.55)
            ctx.arc(r2.uniform(-90, 90), r2.uniform(-70, 70), r2.uniform(5, 11), 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()
    rgb(ctx, (150, 95, 45))
    ctx.save()
    ctx.translate(1020, 930)
    ctx.scale(1, 0.4)
    ctx.arc(0, 0, 95, 0, math.pi)
    ctx.restore()
    ctx.fill()
    r3 = random.Random(3)
    for _ in range(22):
        rgb(ctx, r3.choice([(110, 40, 25), (140, 60, 30), (90, 30, 20)]))
        ctx.save()
        ctx.translate(1020 + r3.uniform(-75, 75), 922 + r3.uniform(-24, 2))
        ctx.scale(1, 0.6)
        ctx.arc(0, 0, 14, 0, 2 * math.pi)
        ctx.restore()
        ctx.fill()
    for k in range(9):  # wheat sheaf
        a = -1.9 + k * 0.1
        x0, y0 = 1230, 960
        x1, y1 = x0 + math.cos(a) * 230, y0 + math.sin(a) * 230
        rgb(ctx, (205, 160, 70))
        ctx.set_line_width(3)
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.stroke()
        for g in range(7):
            gx, gy = x1 - math.cos(a) * g * 12, y1 - math.sin(a) * g * 12
            rgb(ctx, (225, 180, 85))
            ctx.save()
            ctx.translate(gx, gy)
            ctx.rotate(a)
            ctx.scale(1, 0.45)
            ctx.arc(0, 0, 9, 0, 2 * math.pi)
            ctx.restore()
            ctx.fill()
    lin(ctx, 1380, 0, 1560, 0, [(0, (190, 160, 115)), (0.5, (235, 215, 175)), (1, (170, 140, 100))])
    ctx.move_to(1385, 1000)
    ctx.curve_to(1360, 860, 1420, 800, 1470, 810)
    ctx.curve_to(1520, 800, 1580, 860, 1555, 1000)
    ctx.close_path()
    ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ 4. woven palm basket (khoos) close-up
def basket_weave(ctx, t, zoom=1.0):
    ctx.save()
    camera(ctx, zoom, 960, 540)
    lin(ctx, 0, 0, 0, H, [(0, (90, 56, 30)), (1, (50, 30, 16))])
    ctx.paint()
    band = 46
    cols = [(222, 190, 128), (214, 178, 112), (228, 198, 138), (206, 170, 106), (178, 58, 48), (222, 190, 128), (214, 178, 112), (228, 198, 138), (70, 122, 76)]
    ctx.save()
    ctx.translate(960, 540)
    ctx.rotate(math.radians(-24))
    ctx.translate(-1400, -1400)
    n = int(2800 / band)
    for i in range(n):          # warp strips
        col = cols[i % len(cols)]
        lin(ctx, i * band, 0, (i + 1) * band, 0, [(0, tuple(int(c * 0.75) for c in col)), (0.5, col), (1, tuple(int(c * 0.7) for c in col))])
        ctx.rectangle(i * band + 2, 0, band - 4, 2800)
        ctx.fill()
    for j in range(n):          # weft strips go over every other warp
        col = cols[(j + 2) % len(cols)]
        for i in range(n):
            if (i + j) % 2 == 0:
                lin(ctx, 0, j * band, 0, (j + 1) * band, [(0, tuple(int(c * 0.7) for c in col)), (0.5, col), (1, tuple(int(c * 0.65) for c in col))])
                ctx.rectangle(i * band - 3, j * band + 2, band + 6, band - 4)
                ctx.fill()
                rgb(ctx, (40, 24, 12), 0.25)
                ctx.rectangle(i * band - 3, j * band + band - 6, band + 6, 4)
                ctx.fill()
    # fibre texture
    rnd = random.Random(2)
    rgb(ctx, (255, 245, 220), 0.12)
    ctx.set_line_width(1.2)
    for _ in range(900):
        x, y = rnd.uniform(0, 2800), rnd.uniform(0, 2800)
        ctx.move_to(x, y)
        ctx.line_to(x + rnd.uniform(-2, 2), y + rnd.uniform(20, 60))
    ctx.stroke()
    ctx.restore()
    rad(ctx, 960, 540, 200, 1100, [(0, (0, 0, 0, 0)), (1, (20, 10, 4, 0.7))])
    ctx.paint()
    ctx.restore()


# ------------------------------------------------------------------ 5. wheat & potatoes (starch sources)
def wheat_potato(ctx, t):
    lin(ctx, 0, 0, 0, H, [(0, (248, 228, 190)), (1, (226, 196, 150))])
    ctx.paint()
    rad(ctx, 960, 420, 50, 900, [(0, (255, 245, 220, 0.8)), (1, (255, 230, 190, 0))])
    ctx.paint()
    for k in range(22):
        x0 = 120 + k * 36
        sway = 0.04 * math.sin(t * 1.2 + k * 0.6)
        a = -math.pi / 2 + (k - 11) * 0.025 + sway
        L = 520 + 40 * math.sin(k)
        x1, y1 = x0 + math.cos(a) * L, 980 + math.sin(a) * L
        rgb(ctx, (190, 150, 70))
        ctx.set_line_width(4)
        ctx.move_to(x0, 980)
        ctx.line_to(x1, y1)
        ctx.stroke()
        for g in range(10):
            for side in (-1, 1):
                gx = x1 - math.cos(a) * g * 14 + side * 9
                gy = y1 - math.sin(a) * g * 14
                rgb(ctx, (222, 176, 80))
                ctx.save()
                ctx.translate(gx, gy)
                ctx.rotate(a + side * 0.35)
                ctx.scale(1, 0.45)
                ctx.arc(0, 0, 11, 0, 2 * math.pi)
                ctx.restore()
                ctx.fill()
    rnd = random.Random(9)
    for i, (px, py, r) in enumerate(((1250, 860, 120), (1450, 900, 140), (1640, 850, 110), (1380, 760, 100), (1560, 740, 95))):
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(rnd.uniform(-0.6, 0.6))
        ctx.scale(1.35, 0.9)
        rad(ctx, -r * 0.3, -r * 0.3, 5, r * 1.2, [(0, (226, 180, 120)), (0.7, (180, 128, 72)), (1, (130, 88, 48))])
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.fill()
        for _ in range(5):
            rgb(ctx, (110, 72, 40), 0.7)
            ctx.arc(rnd.uniform(-r * 0.6, r * 0.6), rnd.uniform(-r * 0.5, r * 0.5), 5, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()


def draw(fn, *a, **k):
    """Render an environment function to a PIL RGBA frame."""
    return cairo_layer(W, H, lambda ctx: fn(ctx, *a, **k))


@functools.lru_cache(None)
def chef_arch(w=620, h=760, src="chef_hero_x4.png"):
    """Upscaled approved chef image inside an Omani pointed-arch frame (crisp: downscaled from the x4 image)."""
    from lib import ROOT, add_shadow
    im = Image.open(ROOT / "assets/hires" / src).convert("RGB")
    # keep the chef (right part of the hero crop) and fill the frame
    box = (430, 0, 1532, 1420)
    im = im.crop(box)
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l = (im.width - w) // 2
    im = im.crop((l, 0, l + w, h)).convert("RGBA")
    def mask(ctx):
        pointed_arch(ctx, 0, w, h * 0.36, h, 0.32)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
    m = cairo_layer(w, h, mask)
    im.putalpha(m.getchannel("A"))
    pad = 22
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(im, (pad, pad))
    def frame(ctx):
        ctx.translate(pad, pad)
        pointed_arch(ctx, 0, w, h * 0.36, h, 0.32)
        rgb(ctx, GOLD)
        ctx.set_line_width(12)
        ctx.stroke()
        pointed_arch(ctx, 12, w - 12, h * 0.36 + 6, h - 6, 0.32)
        rgb(ctx, (90, 50, 26))
        ctx.set_line_width(3)
        ctx.stroke()
    out.alpha_composite(cairo_layer(out.width, out.height, frame))
    return add_shadow(out, 18, 0.55)


@functools.lru_cache(None)
def chef_medal(d=170):
    """Small round speaker badge (face crop from the upscaled image)."""
    from lib import ROOT, add_shadow
    im = Image.open(ROOT / "assets/hires/chef_hero_x4.png").convert("RGB")
    im = im.crop((880, 140, 1420, 680)).resize((d, d), Image.LANCZOS).convert("RGBA")
    m = cairo_layer(d, d, lambda c: (c.arc(d / 2, d / 2, d / 2 - 1, 0, 2 * math.pi), c.set_source_rgb(1, 1, 1), c.fill()))
    im.putalpha(m.getchannel("A"))
    out = Image.new("RGBA", (d + 16, d + 16), (0, 0, 0, 0))
    out.alpha_composite(im, (8, 8))
    def ring(c):
        c.arc(d / 2 + 8, d / 2 + 8, d / 2 + 2, 0, 2 * math.pi)
        rgb(c, GOLD)
        c.set_line_width(6)
        c.stroke()
    out.alpha_composite(cairo_layer(d + 16, d + 16, ring))
    return add_shadow(out, 10, 0.5)
