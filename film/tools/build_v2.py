"""Build the short version (≈6 min) of 'مخبز الطاقة'.

  python3 tools/build_v2.py timeline | stills | parts [ids] | audio | final
"""
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from lib import FPS, H, ROOT, W, split_subs, strip_harakat, text_img  # noqa: E402
from build import SR, fmt_ass, fmt_srt, music_bed  # noqa: E402

OUT = ROOT / "out_v2"
SCRIPT = json.load(open(ROOT / "script/script_v2.json"))
FADE = 0.35

PACING = {
    1: dict(lead=1.0, pre={"s01_02": 0.8}, tail=3.0),
    2: dict(lead=0.8, pre={"v02_02": 0.6, "s05_01": 0.6, "v02_03": 0.3, "v02_04": 0.8}, tail=1.5),
    3: dict(lead=0.8, pre={"s08_01": 0.6, "s08_02": 0.4, "v03_02": 1.6, "v03_03": 1.0}, tail=2.0),
    4: dict(lead=0.8, pre={"v04_02": 0.6, "v04_03": 0.8, "v04_04": 0.6}, tail=2.5),
    5: dict(lead=1.0, pre={"s11_03": 0.6}, tail=2.0),
    6: dict(lead=1.2, pre={"v06_02": 1.0, "v06_03": 0.6, "s12_05": 0.6}, tail=3.0),
    7: dict(lead=0.6, pre={"s14_02": 9.0, "s14_03": 0.8, "s14_04": 0.8}, tail=3.5),
}


def _dur(cid):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(ROOT / f"audio/vo/{cid}.mp3")], capture_output=True, text=True).stdout
    return float(out)


DUR = {c["id"]: _dur(c["id"]) for p in SCRIPT["parts"] for c in p["cues"]}


class Timing:
    def __init__(self, pid, cues, offset):
        p = PACING[pid]
        t = p["lead"]
        self.cue = {}
        for i, c in enumerate(cues):
            if i:
                t += p.get("pre", {}).get(c["id"], 0.5)
            self.cue[c["id"]] = (t, t + DUR[c["id"]], c["who"], c.get("sub") or c["text"])
            t += DUR[c["id"]]
        self.D = round((t + p["tail"]) * FPS) / FPS
        self.offset = offset

    def start(self, cid):
        return self.cue[cid][0]

    def end(self, cid):
        return self.cue[cid][1]


def timeline():
    tl, off = [], 0.0
    for p in SCRIPT["parts"]:
        T = Timing(p["id"], p["cues"], off)
        tl.append(T)
        off += T.D
    return tl


def write_subs(tl):
    OUT.mkdir(exist_ok=True)
    ev = []
    for T in tl:
        for cid, (s, e, who, text) in T.cue.items():
            text = re.sub(r"\[[^\]]*\]", "", text)
            chunks = split_subs(text, 60)
            total = sum(len(c) for c in chunks)
            tt = s
            for c in chunks:
                d = (e - s) * len(c) / total
                ev.append((T.offset + tt, T.offset + tt + d, who, c))
                tt += d
    with open(OUT / "makhbaz_al_taqa_short_ar.srt", "w", encoding="utf-8") as f:
        for i, (a, b, who, c) in enumerate(ev, 1):
            f.write(f"{i}\n{fmt_srt(a)} --> {fmt_srt(b - 0.04)}\n{c}\n\n")
    head = open(ROOT / "out/subs_burn.ass", encoding="utf-8").read().split("[Events]")[0]
    with open(OUT / "subs_burn.ass", "w", encoding="utf-8") as f:
        f.write(head + "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for a, b, who, c in ev:
            f.write(f"Dialogue: 0,{fmt_ass(a)},{fmt_ass(b - 0.04)},{'Chef' if who == 'chef' else 'Narr'},,0,0,0,,‏{c}‏\n")
    data = [{"part": p["id"], "title": p["title"], "start": round(T.offset, 2), "duration": round(T.D, 2),
             "cues": {k: [round(T.offset + v[0], 2), round(T.offset + v[1], 2), v[2]] for k, v in T.cue.items()}}
            for T, p in zip(tl, SCRIPT["parts"])]
    json.dump(data, open(OUT / "timeline.json", "w"), ensure_ascii=False, indent=1)
    return ev


def frame(pid, T, t):
    import scenes_v2
    im = scenes_v2.PARTS[pid](t, T)
    a = min(1.0, t / FADE, (T.D - t) / FADE)
    if a < 1:
        im.alpha_composite(Image.new("RGBA", im.size, (12, 6, 8, int(255 * (1 - max(0.0, a))))))
    return im.convert("RGB")


def render_part(pid):
    T = timeline()[pid - 1]
    out = OUT / "parts" / f"part{pid}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(T.D * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                          "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(pid, T, i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return pid, n


def stills():
    d = OUT / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for i, T in enumerate(timeline(), 1):
        cues = list(T.cue)
        picks = [0.6 * T.start(c) + 0.4 * T.end(c) for c in cues] + [T.end(cues[-1]) + 0.4]
        for k, t in enumerate(picks):
            frame(i, T, t).save(d / f"p{i}_{k}.jpg", quality=90)


def sfx_cues(tl):
    T = {i + 1: x for i, x in enumerate(tl)}
    g = lambda p, t: T[p].offset + t  # noqa: E731
    at = lambda p, c, f: g(p, T[p].start(c) + f * (T[p].end(c) - T[p].start(c)))  # noqa: E731
    s1 = T[1].start("s01_01")
    return [
        (g(1, 0.0), "souq_ambience", -16),
        (g(1, s1 + 3.0), "door_open", -10),
        (g(1, s1 + 10.0), "oven_fire", -15),
        (g(1, T[1].end("s01_02") - 0.6), "bond_chime", -13),
        (g(2, 0.2), "whoosh", -11),
        (at(2, "v02_02", 0.55), "bond_chime", -13),
        (at(3, "s07_01", 0.75), "bond_chime", -13),
        (at(3, "s08_01", 0.75), "water_drop", -9),
        (g(3, T[3].start("s08_02") + 0.5), "bond_chime", -12),
        (g(3, T[3].start("v03_02") - 0.4), "water_drop", -9),
        (g(4, T[4].start("v04_02") - 0.3), "whoosh", -11),
        (g(6, 0.3), "pottery", -15),
        (g(6, T[6].end("v06_01") + 0.2), "whoosh", -10),
        (at(6, "v06_02", 0.75), "bond_chime", -13),
        (g(6, T[6].end("s12_05")), "whoosh", -11),
        (g(7, T[7].start("s14_02") - 0.2), "bond_chime", -11),
    ]


def audio():
    tl = timeline()
    total = tl[-1].offset + tl[-1].D
    adir = OUT / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    music_bed(total, adir / "music_bed.wav")
    inputs, filters, vo, fx = [], [], [], []
    k = 0
    for T in tl:
        for cid, (s, e, who, text) in T.cue.items():
            inputs += ["-i", str(ROOT / f"audio/vo/{cid}.mp3")]
            d = int(round((T.offset + s) * 1000))
            # first-version and new takes are levelled to the same loudness before mixing
            filters.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo,loudnorm=I=-18:TP=-2,adelay={d}|{d}[v{k}]")
            vo.append(f"[v{k}]")
            k += 1
    for t, name, gain in sfx_cues(tl):
        inputs += ["-i", str(ROOT / f"audio/sfx/{name}.mp3")]
        d = int(round(t * 1000))
        extra = ",afade=t=out:st=12:d=4" if name == "souq_ambience" else ""
        filters.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo{extra},volume={gain}dB,adelay={d}|{d}[f{k}]")
        fx.append(f"[f{k}]")
        k += 1
    inputs += ["-i", str(adir / "music_bed.wav")]
    filters.append(f"{''.join(vo)}amix=inputs={len(vo)}:normalize=0,apad[vo]")
    filters.append("[vo]asplit=2[vo1][vo2]")
    filters.append(f"[{k}:a]volume=-21dB[mraw]")
    filters.append("[mraw][vo2]sidechaincompress=threshold=0.03:ratio=6:attack=60:release=600[mduck]")
    filters.append(f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0,apad[fxm]")
    filters.append(f"[vo1][fxm][mduck]amix=inputs=3:normalize=0:duration=first,atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    (adir / "filter.txt").write_text(";".join(filters))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex_script", str(adir / "filter.txt"),
                    "-map", "[out]", "-ar", str(SR), str(adir / "mix.wav")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(adir / "mix.wav"), "-c:a", "aac", "-b:a", "192k",
                    str(adir / "mix_final.m4a")], check=True)
    print("audio", round(total, 2))


def final():
    tl = timeline()
    total = tl[-1].offset + tl[-1].D
    (OUT / "parts.txt").write_text("".join(f"file 'parts/part{i}.mp4'\n" for i in range(1, 8)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "parts.txt"),
                    "-c", "copy", str(OUT / "video_clean.mp4")], check=True)
    sig = text_img("أ. إمتثال العطابي", 40, (246, 236, 214), "amiri", shadow=True)
    sig.save(OUT / "signature.png")
    x, y = W - sig.width - 44, H - sig.height - 22
    common = ["-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart"]
    base = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "video_clean.mp4"), "-i", str(OUT / "audio/mix.wav"),
            "-loop", "1", "-i", str(OUT / "signature.png"), "-filter_complex"]
    subprocess.run(base + [f"[0:v]subtitles={OUT / 'subs_burn.ass'}:fontsdir={ROOT / 'assets/fonts'}[s];[s][2:v]overlay={x}:{y}[v]"]
                   + common + [str(OUT / "makhbaz_al_taqa_short_1080p.mp4")], check=True)
    subprocess.run(base + [f"[0:v][2:v]overlay={x}:{y}[v]"] + common + [str(OUT / "makhbaz_al_taqa_short_1080p_nosubs.mp4")], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "timeline"
    if cmd == "timeline":
        tl = timeline()
        ev = write_subs(tl)
        for T, p in zip(tl, SCRIPT["parts"]):
            print(f"part {p['id']} {p['title']:<20} start {T.offset:7.2f} dur {T.D:6.2f}")
        print("TOTAL", round(tl[-1].offset + tl[-1].D, 2), "s;", len(ev), "subtitles")
    elif cmd == "stills":
        stills()
    elif cmd == "parts":
        ids = [int(x) for x in sys.argv[2:]] or list(range(1, 8))
        tl = timeline()
        ids.sort(key=lambda i: -tl[i - 1].D)
        with mp.Pool(min(4, len(ids))) as pool:
            for pid, n in pool.imap_unordered(render_part, ids):
                print("rendered part", pid, n, flush=True)
    elif cmd == "audio":
        audio()
    elif cmd == "final":
        final()
