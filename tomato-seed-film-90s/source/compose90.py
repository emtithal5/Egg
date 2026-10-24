"""90-second film: tomato life cycle, circular diagram, annual vs perennial."""
import math, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

D = os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(D, "..", "film")
W, H, FPS, TOTAL = 1920, 1080, 30, 90.0
P = lambda *a: os.path.join(D, *a)
I = lambda n: P("img", n + ".png") if os.path.exists(P("img", n + ".png")) else os.path.join(OLD, "img", n + ".png")
V = lambda n: os.path.join(OLD, "vid", n + ".mp4")


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def load(path, scale=2):
    im = Image.open(path).convert("RGB")
    return im.resize((W * scale, H * scale), Image.LANCZOS) if scale else im


def kb(im, t, dur, z0, z1, c0=(0.5, 0.5), c1=(0.5, 0.5)):
    """Ken Burns crop of a PIL image -> float array."""
    k = ease(t / dur)
    z = z0 + (z1 - z0) * k
    iw, ih = im.size
    cw, ch = iw / z, ih / z
    cx = (c0[0] + (c1[0] - c0[0]) * k) * iw
    cy = (c0[1] + (c1[1] - c0[1]) * k) * ih
    x0 = min(max(cx - cw / 2, 0), iw - cw)
    y0 = min(max(cy - ch / 2, 0), ih - ch)
    return np.asarray(im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))).astype(np.float32)


# ---------- segment types ----------
class Still:
    def __init__(self, img, dur, z0=1.0, z1=1.06, c0=(0.5, 0.5), c1=None):
        self.im = load(I(img)) if isinstance(img, str) else img
        self.dur, self.z0, self.z1, self.c0, self.c1 = dur, z0, z1, c0, c1 or c0

    def frame(self, t):
        return kb(self.im, t, self.dur, self.z0, self.z1, self.c0, self.c1)


class Grow:
    """Shows image A, then reveals image B (bottom-up 'growth' wipe or crossfade)."""
    def __init__(self, a, b, dur, r0=0.3, rlen=2.2, mode="up", z0=1.0, z1=1.04):
        self.a, self.b = load(I(a)), load(I(b))
        self.dur, self.r0, self.rlen, self.mode, self.z0, self.z1 = dur, r0, rlen, mode, z0, z1
        yy = np.linspace(0, 1, H)[:, None, None]
        self.yy = np.broadcast_to(yy, (H, 1, 1))

    def frame(self, t):
        fa = kb(self.a, t, self.dur, self.z0, self.z1)
        k = ease((t - self.r0) / self.rlen)
        if k <= 0:
            return fa
        fb = kb(self.b, t, self.dur, self.z0, self.z1)
        if k >= 1:
            return fb
        if self.mode == "fade":
            return fa * (1 - k) + fb * k
        edge = 1.0 - k * 1.25  # reveal line moves from bottom (1) to above top
        m = np.clip((self.yy - edge) / 0.2 + 0.5, 0, 1)
        return fa * (1 - m) + fb * m


class Clip:
    def __init__(self, path, dur, speed=1.0, crop=None):
        self.path, self.dur, self.speed, self.crop = path, dur, speed, crop
        self.proc, self.last = None, None

    def frame(self, t):
        if self.proc is None:
            vf = f"setpts=PTS/{self.speed},fps={FPS},scale={W}:{H}:flags=lanczos,tpad=stop_mode=clone:stop_duration=4"
            self.proc = subprocess.Popen(["ffmpeg", "-v", "quiet", "-i", self.path, "-vf", vf, "-f", "rawvideo",
                                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        buf = self.proc.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            self.last = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
        return self.last


class Split:
    """Two clips side by side: left half and right half (center-cropped), with divider."""
    def __init__(self, left, right, dur, speed):
        self.l, self.r, self.dur = Clip(left, dur, speed), Clip(right, dur, speed), dur

    def frame(self, t):
        fl, fr = self.l.frame(t), self.r.frame(t)
        out = np.empty_like(fl)
        out[:, :960] = fl[:, 480:1440]
        out[:, 960:] = fr[:, 480:1440]
        out[:, 954:966] = (255, 236, 170)
        return out


def ov_img(name):
    return Image.open(P("ov", name + ".png")).convert("RGBA")


class Pollination:
    """Simplified tomato flower section: wind shakes the flower, pollen reaches the stigma (pollination),
    then a pollen tube grows to an ovule (fertilization)."""
    def __init__(self, dur, t_abs0):
        bg = Image.open(I("k7_flower")).convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        self.bg = bg
        self.fl = ov_img("flower")
        self.dur, self.T0 = dur, t_abs0
        rng = np.random.default_rng(3)
        self.grains = [(948 + rng.random() * 24, 380 + rng.random() * 90, 0.0 + i * 0.12,
                        (rng.random() - 0.5) * 22, (rng.random() - 0.5) * 16) for i in range(18)]

    def frame(self, t):
        a = t + self.T0  # absolute time
        im = self.bg.copy().convert("RGBA")
        shake = 5 * math.sin(2 * math.pi * 5 * a) if 27.0 <= a < 29.8 else 0
        im.alpha_composite(self.fl, (int(shake), 0))
        d = ImageDraw.Draw(im)
        tp = a - 27.3
        for (x0, y0, st, jx, jy) in self.grains:
            k = ease((tp - st) / 1.1)
            if tp < st:
                x, y = x0 + shake, y0
            else:
                x = x0 + (960 + jx - x0) * k + shake * (1 - k)
                y = y0 + (318 + jy - y0) * k
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(255, 193, 7, 255), outline=(191, 120, 0, 255), width=2)
        kt = ease((a - 30.2) / 1.8)
        if kt > 0:
            y1 = 335 + (722 - 335) * kt
            d.line((960, 335, 960, y1), fill=(255, 112, 67, 255), width=7)
            d.ellipse((953, y1 - 7, 967, y1 + 7), fill=(255, 112, 67, 255))
        if a >= 32.0:
            p = 0.5 + 0.5 * math.sin((a - 32.0) * 7)
            r = 16 + 6 * p
            glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((960 - r, 722 - r, 960 + r, 722 + r), fill=(255, 235, 59, int(150 + 80 * p)))
            im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
            d.ellipse((948, 710, 972, 734), fill=(255, 213, 79, 255), outline=(230, 81, 0, 255), width=3)
        return np.asarray(im.convert("RGB")).astype(np.float32)


def find_cards(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    diff = np.abs(a - a[5, 5]).sum(-1) > 60
    def runs(v, minlen):
        out, s = [], None
        for i, x in enumerate(list(v) + [False]):
            if x and s is None: s = i
            if not x and s is not None:
                if i - s >= minlen: out.append((s, i))
                s = None
        return out
    cols, rows = runs(diff.mean(0) > 0.3, 80), runs(diff.mean(1) > 0.3, 80)
    return [im.crop((c[0], r[0], c[1], r[1])) for r in rows for c in cols]


class Diagram:
    R, CX, CY, S = 330, 960, 560, 220

    def __init__(self, dur):
        self.dur = dur
        bg = Image.open(I("k9_fruit")).convert("RGB").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(16))
        self.bg = Image.blend(bg, Image.new("RGB", (W, H), (20, 52, 28)), 0.55).convert("RGBA")
        cells = find_cards(os.path.join(OLD, "img", "grid_tomato.png"))[:5]
        cut = Image.open(I("k2_cut")).convert("RGB")
        cw, ch = cut.size
        cells.append(cut.crop((int(cw * 0.45), int(ch * 0.42), int(cw * 0.78), int(ch * 0.42 + cw * 0.33))))
        mask = Image.new("L", (self.S, self.S), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, self.S - 1, self.S - 1), 36, fill=255)
        self.cards = []
        for c in cells:
            card = Image.new("RGBA", (self.S + 16, self.S + 16), (0, 0, 0, 0))
            ImageDraw.Draw(card).rounded_rectangle((0, 0, self.S + 15, self.S + 15), 42, fill=(255, 224, 138, 255))
            cc = c.resize((self.S, self.S), Image.LANCZOS).convert("RGBA")
            cc.putalpha(mask)
            card.alpha_composite(cc, (8, 8))
            sh = Image.new("RGBA", (self.S + 60, self.S + 60), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((22, 30, self.S + 38, self.S + 46), 42, fill=(0, 0, 0, 120))
            sh = sh.filter(ImageFilter.GaussianBlur(10))
            sh.alpha_composite(card, (22, 22))
            self.cards.append(sh)
        self.center = ov_img("dg_center")
        self.labels = [ov_img(f"dg_l{i}") for i in range(6)]

    def pos(self, i):
        a = math.radians(-90 + 60 * i)
        return self.CX + self.R * math.cos(a), self.CY + self.R * math.sin(a)

    def frame(self, t):
        im = self.bg.copy()
        def fade(layer, k, dy=0):
            if k <= 0: return
            if k < 1:
                layer = layer.copy()
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * k)))
            im.alpha_composite(layer, (0, int(dy)))
        fade(self.center, ease((t - 0.2) / 0.6))
        arcs = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(arcs)
        for i in range(6):
            ta = 0.6 + 0.9 * i + 0.75
            k = ease((t - ta) / 0.6)
            if k <= 0: continue
            a0 = -90 + 60 * i + 24
            a1 = a0 + (60 - 48) * k
            pts = [(self.CX + self.R * math.cos(math.radians(a)), self.CY + self.R * math.sin(math.radians(a)))
                   for a in np.linspace(a0, a1, 24)]
            d.line(pts, fill=(56, 142, 60, 255), width=16, joint="curve")
            d.line(pts, fill=(129, 199, 132, 255), width=6, joint="curve")
            ar = math.radians(a1)
            tip = (self.CX + (self.R) * math.cos(ar + 0.06), self.CY + (self.R) * math.sin(ar + 0.06))
            tx, ty = -math.sin(ar), math.cos(ar)
            nx, ny = math.cos(ar), math.sin(ar)
            base = (pts[-1][0], pts[-1][1])
            d.polygon([(tip[0] + tx * 14, tip[1] + ty * 14), (base[0] + nx * 22, base[1] + ny * 22),
                       (base[0] - nx * 22, base[1] - ny * 22)], fill=(46, 125, 50, 255))
        im.alpha_composite(arcs)
        for i in range(6):
            k = ease((t - (0.6 + 0.9 * i)) / 0.5)
            if k <= 0: continue
            x, y = self.pos(i)
            c = self.cards[i]
            fade_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            fade_layer.alpha_composite(c, (int(x - c.width / 2), int(y - c.height / 2 + 30 * (1 - k))))
            fade(fade_layer, k)
            fade(self.labels[i], k)
        return np.asarray(im.convert("RGB")).astype(np.float32)


# ---------- timeline ----------
segs = []
def add(seg, start):
    segs.append((seg, start))
    return start + seg.dur

add(Still("tomato_fixed", 3.2, 1.0, 1.9, (0.5, 0.55), (0.58, 0.66)), 0.0)            # S1
add(Still("k2_cut", 2.9, 1.15, 1.55, (0.55, 0.62), (0.63, 0.64)), 2.6)
add(Still("k3_seed", 5.1, 1.0, 1.12, (0.5, 0.62), (0.5, 0.64)), 5.0)                  # S2
add(Grow("k3_seed", "k4_germ", 5.0), 10.1)
add(Grow("k4_germ", "k5_seedling", 5.0), 15.1)
add(Grow("k5_seedling", "k6_mature", 4.6), 20.1)
add(Grow("k6_mature", "k7_flower", 2.6, 0.2, 1.4, "fade"), 24.7)
add(Pollination(7.5, 26.9), 26.9)
add(Grow("k8_green", "k9_fruit", 4.2, 1.2, 2.2, "fade"), 34.0)
add(Still("k2_cut", 3.3, 1.05, 1.4, (0.5, 0.6), (0.4, 0.64)), 37.7)
add(Diagram(12.4), 40.6)                                                             # S3
add(Still("garden_split", 5.5, 1.0, 1.1, (0.5, 0.5), (0.55, 0.55)), 52.4)             # S4
add(Clip(V("v3_grow"), 2.52, 2.0), 57.5)                                             # S5
add(Clip(V("v4_flower"), 2.52, 2.0), 60.02)
add(Clip(V("v5_die"), 3.36, 1.5), 62.54)
add(Still("r5_dead", 1.0, 1.0, 1.03), 65.9)
add(Still("annual_examples", 3.4, 1.06, 1.0), 66.6)
add(Clip(V("v6_mgrow"), 2.4, 2.1), 69.5)                                             # S6
add(Clip(V("v7_mfruit"), 2.4, 2.1), 71.9)
add(Clip(V("v8_mharvest"), 2.4, 2.1), 74.3)
add(Clip(V("v9_magain"), 2.4, 2.1), 76.7)
add(Still("perennial_examples", 3.3, 1.0, 1.06), 78.8)
add(Split(V("v9_magain"), V("v5_die"), 4.9, 1.03), 81.5)                              # S7
add(Still("ending", 4.6, 1.0, 1.07, (0.5, 0.6)), 85.4)


def base_frame(tt):
    active = [(s, st) for s, st in segs if st <= tt < st + s.dur] or [segs[-1]]
    if len(active) == 1:
        s, st = active[0]
        return s.frame(tt - st)
    (a, sa), (b, sb) = active[-2], active[-1]
    fa, fb = a.frame(tt - sa), b.frame(tt - sb)
    k = ease((tt - sb) / max(1e-6, (sa + a.dur) - sb))
    return fa * (1 - k) + fb * k


class OV:
    def __init__(self, name, t0, t1, fin=0.5, fout=0.5, alpha=1.0, rise=0):
        im = ov_img(name) if os.path.exists(P("ov", name + ".png")) else Image.open(os.path.join(OLD, "ov", name + ".png")).convert("RGBA")
        bb = im.getbbox() or (0, 0, 1, 1)
        x0, y0, x1, y1 = max(bb[0] - 2, 0), max(bb[1] - 2, 0), min(bb[2] + 2, W), min(bb[3] + 2, H)
        arr = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float32)
        self.rgb, self.a, self.box = arr[..., :3], arr[..., 3:] / 255.0, (x0, y0)
        self.t0, self.t1, self.fin, self.fout, self.alpha, self.rise = t0, t1, fin, fout, alpha, rise

    def apply(self, fr, tt):
        if not (self.t0 <= tt < self.t1):
            return
        a = self.alpha * (ease((tt - self.t0) / self.fin) if self.fin else 1) * (ease((self.t1 - tt) / self.fout) if self.fout else 1)
        if a <= 0.001:
            return
        dy = int(round(self.rise * (1 - ease((tt - self.t0) / max(self.fin, 1e-6))))) if self.rise else 0
        x0, y0 = self.box
        y0 += dy
        h, w = self.a.shape[:2]
        h = min(h, H - y0)
        reg = fr[y0:y0 + h, x0:x0 + w]
        al = self.a[:h] * a
        reg[:] = reg * (1 - al) + self.rgb[:h] * al


ovs = []
O = lambda *a, **k: ovs.append(OV(*a, **k))
O("title", 0.4, 4.7, fin=0.7, rise=30)
O("st1", 5.5, 10.0); O("st2", 10.2, 15.0); O("st3", 15.2, 20.0); O("st4", 20.2, 24.8)
O("lbl_shoot", 12.0, 14.9); O("lbl_radicle", 12.0, 14.9)
O("st5", 25.0, 34.1)
O("cap_poll", 27.0, 30.1, fin=0.4, fout=0.3); O("cap_fert", 30.1, 33.9, fin=0.3)
O("st6", 34.3, 40.6)
O("lbl_ripen", 34.6, 37.9); O("lbl_seeds", 38.1, 40.6)
O("q_life", 52.8, 57.3, fin=0.6, rise=20)
O("annual_title", 57.7, 69.3, fin=0.6, rise=30)
O("r_badge", 57.7, 66.4)
for i, n in enumerate(["ex_radish", "ex_onion", "ex_garlic"]):
    O(n, 66.9 + i * 0.6, 69.3, fin=0.4, rise=16)
O("perennial_title", 69.8, 81.5, fin=0.6, rise=30)
for y, (t0, t1) in enumerate([(69.6, 70.1), (70.1, 70.6), (70.6, 71.1), (71.1, 71.6), (71.6, 72.2), (72.2, 76.7), (76.7, 79.0)], start=1):
    O(f"year_{y if y < 7 else 8}", t0, t1, fin=0.12, fout=0.12)
for i, n in enumerate(["ex_mango", "ex_lemon", "ex_palm"]):
    O(n, 79.2 + i * 0.6, 81.6, fin=0.4, rise=16)
O("split_q", 81.8, 85.7, fin=0.5)
O("split_annual", 82.0, 85.7); O("split_perennial", 82.0, 85.7)
O("end_phrase", 85.9, 91, fin=1.0, fout=0, rise=25)
O("end_sig", 87.0, 91, fin=0.9, fout=0)
O("sig_small", 0.0, 87.2, fin=0.8, fout=0.6, alpha=0.75)


def progress(fr, tt):
    a0, a1 = 57.7, 66.4
    if not (a0 <= tt < a1):
        return
    k = min(max((tt - 57.5) / 8.4, 0), 1)
    f = ease((tt - a0) / 0.5) * ease((a1 - tt) / 0.5)
    x0, y0, w, h = 70, 136, 260, 14
    reg = fr[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - 0.55 * f) + np.array([20, 50, 28]) * 0.55 * f
    fw = int(w * k)
    if fw > 4:
        r2 = fr[y0 + 2:y0 + h - 2, x0 + 2:x0 + fw]
        r2[:] = r2 * (1 - f) + np.array([255, 214, 102]) * f


if __name__ == "__main__":
    out = sys.argv[1]
    t_only = [float(x) for x in sys.argv[2:]]
    if t_only:  # preview stills
        for tt in t_only:
            fr = base_frame(tt); progress(fr, tt)
            for o in ovs: o.apply(fr, tt)
            Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).resize((640, 360)).save(f"{out}_{tt}.jpg")
        sys.exit()
    n = int(round(TOTAL * FPS))
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f in range(n):
        tt = f / FPS
        fr = base_frame(tt)
        progress(fr, tt)
        for o in ovs:
            o.apply(fr, tt)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if f % 300 == 0:
            print(f"{tt:.1f}/{TOTAL}", file=sys.stderr, flush=True)
    enc.stdin.close(); enc.wait()
    for s, _ in segs:
        for c in (getattr(s, "proc", None), getattr(getattr(s, "l", None), "proc", None), getattr(getattr(s, "r", None), "proc", None)):
            if c: c.kill()
