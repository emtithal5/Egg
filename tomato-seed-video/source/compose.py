"""Compose scenes 7-10: base clips/stills with crossfades, text overlays, signature."""
import subprocess, sys, os
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

D = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
P = lambda *a: os.path.join(D, *a)


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ---------- base segments ----------
class Clip:
    def __init__(self, path, dur, speed=1.0):
        self.path, self.dur, self.speed = path, dur, speed
        self.proc = None
        self.last = None

    def frame(self, t):  # sequential access only
        if self.proc is None:
            vf = f"setpts=PTS/{self.speed},fps={FPS},scale={W}:{H}:flags=lanczos,tpad=stop_mode=clone:stop_duration=3"
            self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", self.path, "-vf", vf,
                                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        buf = self.proc.stdout.read(W * H * 3)
        if len(buf) == W * H * 3:
            self.last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        return self.last


class Still:
    def __init__(self, img, dur, z0=1.0, z1=1.08, cx0=0.5, cy0=0.5, cx1=0.5, cy1=0.5):
        im = img if isinstance(img, Image.Image) else Image.open(img).convert("RGB")
        self.im = im.resize((W * 2, H * 2), Image.LANCZOS) if im.size[0] < W * 2 else im
        self.dur, self.z0, self.z1 = dur, z0, z1
        self.c0, self.c1 = (cx0, cy0), (cx1, cy1)

    def frame(self, t):
        k = ease(t / self.dur)
        z = self.z0 + (self.z1 - self.z0) * k
        iw, ih = self.im.size
        cw, ch = iw / z, ih / z
        cx = (self.c0[0] + (self.c1[0] - self.c0[0]) * k) * iw
        cy = (self.c0[1] + (self.c1[1] - self.c0[1]) * k) * ih
        x0 = min(max(cx - cw / 2, 0), iw - cw)
        y0 = min(max(cy - ch / 2, 0), ih - ch)
        return np.asarray(self.im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))


I = lambda n: P("img", n + ".png")
V = lambda n: P("vid", n + ".mp4")

bg_blur = Image.open(I("garden_split")).convert("RGB").filter(ImageFilter.GaussianBlur(14))
bg_blur = Image.blend(bg_blur, Image.new("RGB", bg_blur.size, (18, 40, 22)), 0.45)

# (segment, start time)
segs = []
def add(seg, start):
    segs.append((seg, start))
    return start + seg.dur

t = 0.0
t = add(Clip(V("v1_pullback"), 5.0), 0.0)                       # scene 7
t = add(Still(I("garden_split"), 10.6, 1.0, 1.05), 4.7)
s8 = t - 0.8
t = add(Clip(V("v2_seed"), 4.0, 1.26), s8)                       # scene 8
t = add(Clip(V("v3_grow"), 4.0, 1.26), t)
t = add(Clip(V("v4_flower"), 4.0, 1.26), t)
t = add(Clip(V("v5_die"), 5.0), t)
t = add(Still(I("r5_dead"), 3.0, 1.0, 1.06, 0.5, 0.5, 0.5, 0.45), t)
t = add(Still(I("annual_examples"), 8.5, 1.06, 1.0), t - 0.6)
s9 = t - 0.8
t = add(Clip(V("v6_mgrow"), 4.0, 1.26), s9)                      # scene 9
t = add(Clip(V("v7_mfruit"), 4.0, 1.26), t)
t = add(Clip(V("v8_mharvest"), 4.0, 1.26), t)
t = add(Clip(V("v9_magain"), 4.5, 1.12), t)
t = add(Still(I("perennial_examples"), 8.0, 1.0, 1.06), t - 0.6)
s10 = t - 0.8
t = add(Still(bg_blur, 21.5, 1.0, 1.04), s10)                    # scene 10
s_end = t - 0.8
t = add(Still(I("ending"), 8.0, 1.0, 1.08, 0.5, 0.6, 0.5, 0.6), s_end)
TOTAL = t
print("scene starts", s8, s9, s10, s_end, "total", TOTAL, file=sys.stderr)


def base_frame(tt):
    active = [(s, st) for s, st in segs if st <= tt < st + s.dur]
    if not active:
        active = [segs[-1]]
    if len(active) == 1:
        s, st = active[0]
        return s.frame(tt - st).astype(np.float32)
    (a, sa), (b, sb) = active[-2], active[-1]
    fa = a.frame(tt - sa).astype(np.float32)
    fb = b.frame(tt - sb).astype(np.float32)
    k = ease((tt - sb) / max(1e-6, (sa + a.dur) - sb))
    return fa * (1 - k) + fb * k


# ---------- overlays ----------
class OV:
    cache = {}
    def __init__(self, src, t0, t1, fin=0.5, fout=0.5, alpha=1.0, rise=0):
        if isinstance(src, str):
            if src not in OV.cache:
                im = Image.open(P("ov", src + ".png")).convert("RGBA")
                OV.cache[src] = im
            im = OV.cache[src]
        else:
            im = src
        bb = im.getbbox() or (0, 0, 1, 1)
        x0, y0, x1, y1 = max(bb[0] - 2, 0), max(bb[1] - 2, 0), min(bb[2] + 2, W), min(bb[3] + 2, H)
        arr = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.float32)
        self.rgb, self.a = arr[..., :3], arr[..., 3:] / 255.0
        self.box = (x0, y0)
        self.t0, self.t1, self.fin, self.fout, self.alpha, self.rise = t0, t1, fin, fout, alpha, rise

    def apply(self, fr, tt):
        if not (self.t0 <= tt < self.t1):
            return
        a = self.alpha
        if self.fin > 0:
            a *= ease((tt - self.t0) / self.fin)
        if self.fout > 0:
            a *= ease((self.t1 - tt) / self.fout)
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

# Scene 7
O("s7_split", 6.4, 14.7, fin=0.9)
O("s7_question", 9.0, 14.8, fin=0.6, rise=20)
# Scene 8 radish
O("r_c1", s8 + 0.4, s8 + 2.2)
O("r_c2", s8 + 2.2, s8 + 7.8)
O("r_c3", s8 + 8.0, s8 + 10.2)
O("r_c4", s8 + 10.2, s8 + 14.4)
O("r_c5", s8 + 14.4, s8 + 19.6)
O("r_badge", s8 + 0.4, s8 + 19.6)
an_t = s8 + 19.6 + 0.3
O("annual_title", an_t, an_t + 7.6, fin=0.7, rise=30)
for i, n in enumerate(["ex_radish", "ex_onion", "ex_garlic"]):
    O(n, s8 + 24.3 + i * 0.8, an_t + 7.6, fin=0.4, rise=16)
# Scene 9 mango
O("m_c1", s9 + 0.3, s9 + 2.7)
O("m_c2", s9 + 2.7, s9 + 4.9)
O("m_c3", s9 + 4.9, s9 + 8.0)
O("m_c4", s9 + 8.0, s9 + 12.2)
O("m_c5", s9 + 12.2, s9 + 16.4)
years = [(0.0, 1), (0.7, 2), (1.3, 3), (1.9, 4), (2.5, 5), (3.1, 6), (4.0, 7), (12.0, 8), (14.2, 9)]
for i, (off, y) in enumerate(years):
    end = years[i + 1][0] if i + 1 < len(years) else 16.4
    O(f"year_{y}", s9 + 0.3 + off, s9 + 0.3 + end if i + 1 < len(years) else s9 + end, fin=0.15, fout=0.15)
pe_t = s9 + 16.2
O("perennial_title", pe_t, pe_t + 7.6, fin=0.7, rise=30)
for i, n in enumerate(["ex_mango", "ex_lemon", "ex_palm"]):
    O(n, s9 + 17.2 + i * 0.85, pe_t + 7.6, fin=0.4, rise=16)


# Scene 10 cards
def find_cards(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(int)
    bgc = a[5, 5]
    diff = np.abs(a - bgc).sum(-1) > 60
    def runs(v, minlen):
        out, s = [], None
        for i, x in enumerate(v):
            if x and s is None: s = i
            if not x and s is not None:
                if i - s >= minlen: out.append((s, i))
                s = None
        if s is not None and len(v) - s >= minlen: out.append((s, len(v)))
        return out
    cols = runs(diff.mean(0) > 0.3, 80)
    rows = runs(diff.mean(1) > 0.3, 80)
    cells = []
    for r in rows:
        for c in cols:
            cells.append(im.crop((c[0], r[0], c[1], r[1])))
    return cells


def card_layer(cells, order_rtl=True, size=280, y=520):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), 34, fill=255)
    layers = []
    for i, c in enumerate(cells):
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        cx = W - (175 + i * 314) if order_rtl else 175 + i * 314
        x, yy = cx - size // 2, y - size // 2
        sh = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 26, size + 20, size + 26), 38, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        L.alpha_composite(sh, (x - 20, yy - 20))
        border = Image.new("RGBA", (size + 12, size + 12), (0, 0, 0, 0))
        ImageDraw.Draw(border).rounded_rectangle((0, 0, size + 11, size + 11), 40, fill=(255, 236, 170, 255))
        L.alpha_composite(border, (x - 6, yy - 6))
        cc = c.resize((size, size), Image.LANCZOS).convert("RGBA")
        cc.putalpha(mask)
        L.alpha_composite(cc, (x, yy))
        layers.append(L)
    return layers


tom = find_cards(I("grid_tomato"))
pl = find_cards(I("grid_plants"))
print("cards", len(tom), len(pl), file=sys.stderr)
O("ch_title", s10 + 0.3, s10 + 3.4, fin=0.7, rise=30)
q1 = s10 + 3.5
O("ch_q1", q1, q1 + 9.2, fin=0.6, rise=20)
for i, L in enumerate(card_layer(tom)):
    O(L, q1 + 0.8 + i * 0.45, q1 + 9.2, fin=0.45, rise=30)
q2 = q1 + 9.6
O("ch_q2", q2, s_end + 0.6, fin=0.6, rise=20)
for i, L in enumerate(card_layer(pl, y=470)):
    O(L, q2 + 0.5 + i * 0.4, s_end + 0.6, fin=0.45, rise=30)
    O(f"pn_{i}", q2 + 0.7 + i * 0.4, s_end + 0.6, fin=0.45)

# Ending
end_phrase_t = s_end + 0.9
O("end_phrase", end_phrase_t, TOTAL + 1, fin=1.0, fout=0, rise=25)
O("end_sig", TOTAL - 3.0, TOTAL + 1, fin=1.0, fout=0)
# persistent small signature (fades out as the big one comes in)
O("sig_small", 0.0, TOTAL - 2.7, fin=1.0, fout=0.6, alpha=0.75)

# progress bar for the annual "one year" badge
def progress(fr, tt):
    a0, a1 = s8 + 0.4, s8 + 19.6
    if not (a0 <= tt < a1):
        return
    k = min(max((tt - s8) / 17.0, 0), 1)
    fade = ease((tt - a0) / 0.5) * ease((a1 - tt) / 0.5)
    x0, y0, w, h = 70, 136, 260, 14
    reg = fr[y0:y0 + h, x0:x0 + w]
    reg[:] = reg * (1 - 0.55 * fade) + np.array([20, 50, 28]) * 0.55 * fade
    fw = int(w * k)
    if fw > 0:
        r2 = fr[y0 + 2:y0 + h - 2, x0 + 2:x0 + fw]
        r2[:] = r2 * (1 - fade) + np.array([255, 214, 102]) * fade


if __name__ == "__main__":
    out = sys.argv[1]
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
        if f % 150 == 0:
            print(f"{tt:.1f}/{TOTAL:.1f}", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()
    with open(P("timeline.txt"), "w") as fh:
        fh.write(f"s8={s8}\ns9={s9}\ns10={s10}\ns_end={s_end}\ntotal={TOTAL}\nq1={q1}\nq2={q2}\n")
