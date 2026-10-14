"""Download completed ElevenLabs generations from a saved run-status JSON, matching each to a script cue by text."""
import json, re, sys, subprocess, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
script = json.load(open(ROOT / "script/script.json"))
cues = {c["id"]: c["text"] for s in script["scenes"] for c in s["cues"]}
# short version (v2) cues share the same download folder
v2 = json.load(open(ROOT / "script/script_v2.json"))
cues.update({c["id"]: c["text"] for p in v2["parts"] for c in p["cues"]})
def norm(t): return re.sub(r"\[[^\]]*\]|\s+", "", t)
by_text = {norm(t): cid for cid, t in cues.items()}
out = ROOT / "audio/vo"
SFX = {"Calm traditional Arabian market": "souq_ambience", "A heavy old wooden fortress gate": "door_open",
       "Wood fire igniting": "oven_fire", "Soft magical shimmering whoosh": "whoosh",
       "A single soft, warm glass bell": "bond_chime", "A single clean water droplet": "water_drop",
       "Gentle sounds of placing clay pots": "pottery"}
for path in sys.argv[1:]:
    d = json.load(open(path))
    for g in d["generations"]:
        key = norm(g["prompt"])
        # status responses truncate prompts to 200 chars, so fall back to a prefix match
        cid = by_text.get(key) or next((c for t, c in by_text.items() if t.startswith(key)), None)
        sfx = next((n for k, n in SFX.items() if g["prompt"].startswith(k)), None)
        if sfx and g["status"] == "completed":
            dst = ROOT / f"audio/sfx/{sfx}.mp3"
            if not dst.exists():
                subprocess.run(["curl", "-sSfL", "-o", str(dst), g["content_url"]], check=True); print("ok", sfx)
            continue
        if g["status"] != "completed" or not cid:
            print("skip", g["status"], cid, g["prompt"][:30]); continue
        dst = out / f"{cid}.mp3"
        if dst.exists(): continue
        subprocess.run(["curl", "-sSfL", "-o", str(dst), g["content_url"]], check=True)
        print("ok", cid, g.get("duration_secs"))
