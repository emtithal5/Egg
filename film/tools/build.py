"""Build 'مخبز الطاقة' end to end.

  python3 tools/build.py timeline        # compute timing from the voice files, write SRT/ASS + timeline.json
  python3 tools/build.py stills          # one preview still per scene (for review)
  python3 tools/build.py scenes [ids]    # render clean scene videos (no subtitles / signature) -> out/scenes
  python3 tools/build.py audio           # mix VO + SFX + music bed -> out/audio
  python3 tools/build.py final           # concat + burn subtitles + fixed signature overlay -> out/
"""
import json
import math
import multiprocessing as mp
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from lib import FPS, H, ROOT, W, split_subs, text_img  # noqa: E402

OUT = ROOT / "out"
SCRIPT = json.load(open(ROOT / "script/script.json"))
DUR = {l.split()[0]: float(l.split()[1]) for l in open(ROOT / "audio/durations.txt")}

# per-scene pacing: lead-in, pause before specific cues, default gap, tail
PACING = {
    1: dict(lead=3.0, pre={"s01_02": 1.6}, tail=4.0),
    2: dict(lead=1.0, pre={"s02_02": 1.0}, tail=1.8),
    3: dict(lead=0.8, pre={"s03_02": 1.6}, tail=2.2),
    4: dict(lead=1.2, tail=2.5),
    5: dict(lead=1.5, tail=2.5),
    6: dict(lead=1.0, pre={"s06_02": 1.0}, tail=2.0),
    7: dict(lead=1.0, pre={"s07_02": 1.2, "s07_03": 1.2, "s07_04": 1.2}, tail=2.5),
    8: dict(lead=1.0, pre={"s08_02": 0.8, "s08_03": 1.2}, tail=2.5),
    9: dict(lead=1.2, pre={"s09_02": 1.0}, tail=2.5),
    10: dict(lead=1.0, pre={"s10_02": 1.0, "s10_03": 1.5}, tail=2.5),
    11: dict(lead=2.2, tail=2.5),
    12: dict(lead=1.0, pre={"s12_02": 1.0}, tail=3.5),
    13: dict(lead=1.0, pre={"s13_02": 1.2, "s13_03": 1.2, "s13_04": 1.2}, tail=5.0),
    14: dict(lead=1.0, pre={"s14_02": 0.8, "s14_03": 1.5, "s14_04": 1.0}, tail=4.5),
}
GAP = 0.7
FADE = 0.45


class Timing:
    def __init__(self, sid, cues, offset):
        p = PACING[sid]
        t = p["lead"]
        self.cue = {}
        for i, c in enumerate(cues):
            if i:
                t += p.get("pre", {}).get(c["id"], GAP)
            self.cue[c["id"]] = (t, t + DUR[c["id"]], c["who"], c["text"])
            t += DUR[c["id"]]
        self.D = round((t + p["tail"]) * FPS) / FPS
        self.offset = offset

    def start(self, cid):
        return self.cue[cid][0]

    def end(self, cid):
        return self.cue[cid][1]


def timeline():
    tl, off = [], 0.0
    for sc in SCRIPT["scenes"]:
        T = Timing(sc["id"], sc["cues"], off)
        tl.append(T)
        off += T.D
    return tl


# ---------------------------------------------------------------- subtitles
def sub_events(tl):
    ev = []
    for T in tl:
        for cid, (s, e, who, text) in T.cue.items():
            chunks = split_subs(text, 60)
            total = sum(len(c) for c in chunks)
            t = s
            for c in chunks:
                d = (e - s) * len(c) / total
                ev.append((T.offset + t, T.offset + t + d, who, c))
                t += d
    return ev


def fmt_srt(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def fmt_ass(x):
    cs = int(round(x * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_subs(tl):
    ev = sub_events(tl)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "makhbaz_al_taqa_ar.srt", "w", encoding="utf-8") as f:
        for i, (a, b, who, c) in enumerate(ev, 1):
            name = "الشيف رقية" if who == "chef" else "الراوية"
            f.write(f"{i}\n{fmt_srt(a)} --> {fmt_srt(b - 0.04)}\n{c}\n\n")
    # ASS for burning in: opaque rounded-looking box, centred, kept clear of the signature corner
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narr,Noto Naskh Arabic,68,&H00F2F6FB,&H000000FF,&H8C0A0612,&H8C0A0612,1,0,0,0,100,100,0,0,3,12,0,2,310,310,14,178
Style: Chef,Noto Naskh Arabic,68,&H0078CDF0,&H000000FF,&H8C0A0612,&H8C0A0612,1,0,0,0,100,100,0,0,3,12,0,2,310,310,14,178

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    with open(OUT / "subs_burn.ass", "w", encoding="utf-8") as f:
        f.write(head)
        for a, b, who, c in ev:
            # RLM keeps libass in right-to-left paragraph order (punctuation on the correct side)
            f.write(f"Dialogue: 0,{fmt_ass(a)},{fmt_ass(b - 0.04)},{'Chef' if who == 'chef' else 'Narr'},,0,0,0,,\u200f{c}\u200f\n")
    data = [{"scene": T_i + 1, "title": sc["title"], "start": round(T.offset, 2), "duration": round(T.D, 2),
             "cues": {k: [round(T.offset + v[0], 2), round(T.offset + v[1], 2), v[2]] for k, v in T.cue.items()}}
            for T_i, (T, sc) in enumerate(zip(tl, SCRIPT["scenes"]))]
    json.dump(data, open(OUT / "timeline.json", "w"), ensure_ascii=False, indent=1)
    return ev


# ---------------------------------------------------------------- video
def frame(sid, T, t):
    import scenes
    im = scenes.SCENES[sid](t, T)
    # dip-to-dark at scene boundaries (scene 1 opens from black, scene 14 closes to black)
    a = min(1.0, t / FADE, (T.D - t) / FADE)
    if a < 1:
        dark = Image.new("RGBA", im.size, (12, 6, 8, int(255 * (1 - max(0.0, a)))))
        im.alpha_composite(dark)
    return im.convert("RGB")


def render_scene(sid):
    tl = timeline()
    T = tl[sid - 1]
    out = OUT / "scenes" / f"scene{sid:02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(T.D * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(sid, T, i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return sid, n


def stills():
    tl = timeline()
    d = OUT / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for T_i, T in enumerate(tl, 1):
        cues = list(T.cue)
        picks = [0.5 * (T.start(cues[0]) + T.end(cues[0]))] + [0.75 * T.start(c) + 0.25 * T.end(c) for c in cues[1:]] + [
            T.end(cues[-1]) + 0.3]
        for k, t in enumerate(picks):
            frame(T_i, T, t).save(d / f"s{T_i:02d}_{k}.jpg", quality=88)


# ---------------------------------------------------------------- audio
SR = 48000


def music_bed(seconds, path):
    """Gentle, low ambient pad (D drone with a soft Hijaz colour) synthesised locally – no third-party music."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    base = 73.42  # D2
    for f, a in [(base, 0.5), (base * 1.5, 0.25), (base * 2, 0.22), (base * 3, 0.06)]:
        sig += a * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.07 * t))
    # slow melodic colour: D, Eb, F#, G, A (Hijaz on D) as soft swells every ~8 s
    notes = [293.66, 311.13, 369.99, 392.0, 440.0, 392.0, 369.99, 311.13]
    for i in range(int(seconds / 8) + 1):
        f = notes[i % len(notes)]
        s0 = int(i * 8 * SR)
        L = min(n - s0, int(7.5 * SR))
        if L <= 0:
            break
        env = np.sin(np.linspace(0, np.pi, L)) ** 2
        tt = np.arange(L) / SR
        sig[s0:s0 + L] += 0.12 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt))
    sig *= 0.8 + 0.2 * np.sin(2 * np.pi * t / 23)
    fade = np.minimum(1, np.minimum(t / 3, (seconds - t) / 4))
    sig = sig * fade / np.max(np.abs(sig)) * 0.5
    st = np.stack([sig, np.roll(sig, int(0.013 * SR))], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def sfx_cues(tl):
    """(global time, file, gain dB). Times mirror the visual events in scenes.py."""
    T = {i + 1: x for i, x in enumerate(tl)}
    g = lambda sid, t: T[sid].offset + t  # noqa: E731
    at = lambda sid, cid, f: g(sid, T[sid].start(cid) + f * (T[sid].end(cid) - T[sid].start(cid)))  # noqa: E731
    s1 = T[1]
    ev = [
        (g(1, 0.0), "souq_ambience", -15),
        (g(1, s1.start("s01_01") + 9.3), "door_open", -9),
        (g(1, s1.start("s01_02") + 1.0), "oven_fire", -14),
        (g(1, s1.end("s01_02") - 3.5), "bond_chime", -12),
        (g(2, 0.3), "pottery", -14),
        (g(2, T[2].start("s02_02") - 0.6), "whoosh", -10),
        (g(3, T[3].end("s03_01") - 1.0), "whoosh", -8),
        (at(4, "s04_02", 0.62), "bond_chime", -12),
        (g(7, 0.3), "pottery", -14),
        (at(7, "s07_01", 0.8), "bond_chime", -12),
        (g(7, T[7].end("s07_01")), "whoosh", -10),
        (at(7, "s07_02", 0.4), "bond_chime", -13),
        (at(7, "s07_03", 0.4), "bond_chime", -13),
        (at(7, "s07_04", 0.4), "bond_chime", -13),
        (at(8, "s08_01", 0.75), "water_drop", -8),
        (g(8, T[8].start("s08_02") + 0.6), "bond_chime", -11),
        (at(8, "s08_03", 0.2), "water_drop", -8),
        (g(9, 0.4), "door_open", -11),
        (g(9, T[9].end("s09_01")), "whoosh", -10),
        (at(9, "s09_02", 0.5), "bond_chime", -13),
        (at(10, "s10_01", 0.3), "whoosh", -10),
        (g(12, T[12].end("s12_01")), "whoosh", -10),
        (at(12, "s12_03", 0.4), "bond_chime", -13),
        (at(12, "s12_05", 0.85), "whoosh", -11),
        (g(14, T[14].start("s14_02") - 0.2), "bond_chime", -10),
    ]
    return ev


def audio():
    tl = timeline()
    total = tl[-1].offset + tl[-1].D
    adir = OUT / "audio"
    adir.mkdir(parents=True, exist_ok=True)
    music_bed(total, adir / "music_bed.wav")
    inputs, filters, labels_vo, labels_fx = [], [], [], []
    k = 0
    for T in tl:
        for cid, (s, e, who, text) in T.cue.items():
            inputs += ["-i", str(ROOT / f"audio/vo/{cid}.mp3")]
            d = int(round((T.offset + s) * 1000))
            filters.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo,adelay={d}|{d},volume=1.0[v{k}]")
            labels_vo.append(f"[v{k}]")
            k += 1
    for t, name, gain in sfx_cues(tl):
        inputs += ["-i", str(ROOT / f"audio/sfx/{name}.mp3")]
        d = int(round(t * 1000))
        extra = ",afade=t=out:st=18:d=4" if name == "souq_ambience" else ""
        filters.append(f"[{k}:a]aresample={SR},aformat=channel_layouts=stereo{extra},volume={gain}dB,adelay={d}|{d}[f{k}]")
        labels_fx.append(f"[f{k}]")
        k += 1
    inputs += ["-i", str(adir / "music_bed.wav")]
    mus = k
    filters.append(f"{''.join(labels_vo)}amix=inputs={len(labels_vo)}:normalize=0:dropout_transition=0,apad[vo]")
    filters.append("[vo]asplit=2[vo1][vo2]")
    filters.append(f"[{mus}:a]volume=-21dB[mraw]")
    filters.append("[mraw][vo2]sidechaincompress=threshold=0.03:ratio=6:attack=60:release=600[mduck]")
    filters.append(f"{''.join(labels_fx)}amix=inputs={len(labels_fx)}:normalize=0,apad[fx]")
    filters.append(f"[vo1][fx][mduck]amix=inputs=3:normalize=0:duration=first,atrim=0:{total:.3f},"
                   f"loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    fc = ";".join(filters)
    (adir / "filter.txt").write_text(fc)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex_script", str(adir / "filter.txt"),
                                                             "-map", "[out]", "-ar", str(SR), "-c:a", "pcm_s16le",
                                                             str(adir / "mix.wav")]
    subprocess.run(cmd, check=True)
    # stems for re-editing
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs[: 2 * len(labels_vo)] + [
        "-filter_complex", ";".join(filters[: len(labels_vo)]) + ";" + f"{''.join(labels_vo)}amix=inputs={len(labels_vo)}:normalize=0,atrim=0:{total:.3f}[o]",
        "-map", "[o]", "-ar", str(SR), str(adir / "stem_voice.wav")], check=True)
    print("audio total", total)


def signature_png():
    sig = text_img("أ. إمتثال العطابي", 40, (246, 236, 214), "amiri", shadow=True)
    sig.save(OUT / "signature.png")
    return sig


def final():
    tl = timeline()
    total = tl[-1].offset + tl[-1].D
    lst = OUT / "scenes.txt"
    lst.write_text("".join(f"file 'scenes/scene{i:02d}.mp4'\n" for i in range(1, 15)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(OUT / "video_clean.mp4")], check=True)
    for wav, m4a in (("mix.wav", "mix_final.m4a"), ("stem_voice.wav", "stem_voice.m4a")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "audio" / wav), "-c:a", "aac", "-b:a", "192k",
                        str(OUT / "audio" / m4a)], check=True)
    sig = signature_png()
    # bottom-right, fixed, safe margin: 56 px from the right edge, 34 px from the bottom
    x, y = W - sig.width - 44, H - sig.height - 22
    vf = (f"[0:v]subtitles={OUT / 'subs_burn.ass'}:fontsdir={ROOT / 'assets/fonts'}[s];"
          f"[s][2:v]overlay={x}:{y}:format=auto[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "video_clean.mp4"), "-i", str(OUT / "audio/mix.wav"),
                    "-loop", "1", "-i", str(OUT / "signature.png"), "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{total:.3f}", "-movflags", "+faststart", str(OUT / "makhbaz_al_taqa_carbohydrates_1080p.mp4")],
                   check=True)
    # signature-only version without burned subtitles (subtitles available as .srt)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "video_clean.mp4"), "-i", str(OUT / "audio/mix.wav"),
                    "-loop", "1", "-i", str(OUT / "signature.png"), "-filter_complex", f"[0:v][2:v]overlay={x}:{y}[v]",
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart",
                    str(OUT / "makhbaz_al_taqa_carbohydrates_1080p_nosubs.mp4")], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "timeline"
    if cmd == "timeline":
        tl = timeline()
        ev = write_subs(tl)
        for T, sc in zip(tl, SCRIPT["scenes"]):
            print(f"scene {sc['id']:2d} {sc['title']:<28} start {T.offset:7.2f}  dur {T.D:6.2f}")
        print("TOTAL", round(tl[-1].offset + tl[-1].D, 2), "s;", len(ev), "subtitle events")
    elif cmd == "stills":
        stills()
    elif cmd == "scenes":
        ids = [int(x) for x in sys.argv[2:]] or list(range(1, 15))
        tl = timeline()
        ids.sort(key=lambda i: -tl[i - 1].D)
        with mp.Pool(min(4, len(ids))) as pool:
            for sid, n in pool.imap_unordered(render_scene, ids):
                print("rendered scene", sid, n, "frames", flush=True)
    elif cmd == "audio":
        audio()
    elif cmd == "final":
        final()
