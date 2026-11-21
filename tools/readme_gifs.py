#!/usr/bin/env python3
"""The README's animated GIFs, from real engine output (docs/visuals/*.gif).

    tools/readme_gifs.py BUILD WORK [OUT=docs/visuals] [--only hero,mult,modes,blend,flow,game]

Every generated image in the GIFs is a frame chuds_fg_offline produced; the
labels, frame strips and error maps are drawn around them, nothing is
retouched. Steps (each skipped when WORK already holds its result):
  1. WORK/d120: 400 frames of the Vulkan demo, deterministic at 120 fps
     (--deterministic: animation time = frame / fps), 960x540, recorded
     through the layer at x1 (dump) inside a headless gamescope — never in
     the desktop session. Every 4th frame is a 30 fps game, the others its
     exact ground truth; every 8th a 15 fps game (multipliers).
  2. WORK/seq/fps: tools/edge_bench/make_game.py fps (1280x720, 30 fps
     first-person turn seen at 120 Hz, motion blur, HUD, weapon).
  3. chuds_fg_offline (CHUDS_FG_CONFIG=/dev/null: defaults, so the dedicated
     GPU's automatic options) at x4 in each mode, x2/x4/x8 of the 15 fps
     game, x4 of the game scene, with the flow dumped (--dump-flow).
  4. The GIFs (ffmpeg palette, 4x slow motion where frames are 120 Hz).
Needs gamescope, ffmpeg, numpy, Pillow and a Vulkan GPU."""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def font(spec, size):
    try:
        path = subprocess.run(["fc-match", "-f", "%{file}", spec], capture_output=True, text=True).stdout.strip()
        return ImageFont.truetype(path, size)
    except (OSError, FileNotFoundError):
        return ImageFont.load_default(size)


F_B = font("Noto Sans:bold", 15)
F_R = font("Noto Sans:medium", 13)

BG = (13, 17, 23)
BAR = (22, 27, 34)
FG = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (63, 185, 140)        # generated frames
REAL = (201, 209, 217)         # real frames
WARN = (219, 109, 40)
GAP = 6
LABEL_H = 30
STRIP_H = 18

_cache = {}




def offline_env(**extra):
    env = dict(os.environ, CHUDS_FG_CONFIG="/dev/null")
    for k in list(env):
        if k.startswith("CHUDS_FG_") and k != "CHUDS_FG_CONFIG":
            del env[k]
    env.update(extra)
    return env


def prepare(build, work):
    work.mkdir(parents=True, exist_ok=True)
    demo = work / "d120"
    if not demo.exists():
        raw = work / "d120_raw"
        shutil.rmtree(raw, ignore_errors=True)
        raw.mkdir()
        script = (f". '{ROOT}/tools/layer_env.sh'; chuds_fg_use_layer '{build}/layer'; "
                  "export CHUDS_FG_CONFIG=/dev/null; "
                  "exec gamescope --backend headless -W 960 -H 540 -w 960 -h 540 -- "
                  f"env -u WAYLAND_DISPLAY CHUDS_FG=1 CHUDS_FG_MULTIPLIER=1 CHUDS_FG_DUMP='{raw}' "
                  f"CHUDS_FG_DUMP_FRAMES=400 '{build}/demo/chuds_fg_demo' --fps 120 --frames 400 "
                  "--deterministic --size 960x540 --ignore-resize")
        subprocess.run(["bash", "-c", script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        files = sorted(raw.glob("*.ppm"))
        if len(files) < 400:
            raise SystemExit(f"demo capture: {len(files)} frames of 400 in {raw}")
        demo.mkdir()
        for i, f in enumerate(files):
            f.rename(demo / f"f{i:04d}.ppm")
        raw.rmdir()
    for st in (2, 4):
        sub = work / f"d120_s{st}"
        if not sub.exists():
            sub.mkdir()
            for i, n in enumerate(range(0, 400, st)):
                (sub / f"f{i:04d}.ppm").symlink_to(demo / f"f{n:04d}.ppm")
    game = work / "seq/fps"
    if not game.exists():
        subprocess.run(["python3", str(ROOT / "tools/edge_bench/make_game.py"), str(game), "fps", "97"],
                       check=True, stdout=subprocess.DEVNULL)
    off = str(build / "tools/offline/chuds_fg_offline")
    runs = [("d_interp", demo, 4, {}, ["--dump-flow", str(work / "out/d_flow")]),
            ("d_hybrid", demo, 4, {"CHUDS_FG_MODE": "hybrid"}, []),
            ("d_extrap", demo, 4, {"CHUDS_FG_MODE": "extrapolate"}, []),
            ("m8", demo, 8, {}, []),
            ("m4", work / "d120_s2", 4, {}, []),
            ("m2", work / "d120_s4", 2, {}, []),
            ("fps_x4", game, 4, {}, [])]
    for name, src, m, env, args in runs:
        out = work / "out" / name
        if (out / "manifest.txt").exists():
            continue
        subprocess.run([off, str(src), str(out), "--multiplier", str(m), *args], check=True,
                       env=offline_env(**env), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def load(p):
    p = str(p)
    if p not in _cache:
        _cache[p] = Image.open(p).convert("RGB")
    return _cache[p]


def idx(p):
    return int(Path(p).stem[1:])


def timeline(out, indir, mult, stride=1):
    """content time (in units of the finest grid) -> (image path, kind)."""
    tl = {}
    for f in sorted(Path(indir).glob("f*.ppm")):
        n = idx(f)
        if n % mult == 0:
            tl[n * stride] = (f, "real")
    for line in (Path(out) / "manifest.txt").read_text().splitlines():
        g, gt = line.split()[:2]
        tl[idx(gt) * stride] = (Path(out) / g, "gen")
    return tl


def held(indir, every, stride=1):
    files = {idx(f) * stride: f for f in Path(indir).glob("f*.ppm")}
    return lambda t: (files[(t // every) * every], "real" if t % every == 0 else "held")


def label_bar(w, title, tag, tag_col):
    im = Image.new("RGB", (w, LABEL_H), BAR)
    d = ImageDraw.Draw(im)
    d.text((10, LABEL_H // 2), title, font=F_B, fill=FG, anchor="lm")
    if tag:
        tw = d.textlength(tag, font=F_R)
        x1 = w - 10; x0 = x1 - tw - 16
        d.rounded_rectangle((x0, 6, x1, LABEL_H - 6), radius=9, fill=tag_col)
        d.text(((x0 + x1) / 2, LABEL_H // 2), tag, font=F_R, fill=BG, anchor="mm")
    return im


def strip(w, kinds, cur):
    """A row of cells: one per displayed frame of a window, current outlined."""
    im = Image.new("RGB", (w, STRIP_H), BG)
    d = ImageDraw.Draw(im)
    n = len(kinds)
    cw = (w - 20) / n
    for i, k in enumerate(kinds):
        x0 = 10 + i * cw + 1; x1 = 10 + (i + 1) * cw - 2
        col = {"real": REAL, "gen": ACCENT, "held": (72, 79, 88)}[k]
        if i == cur:
            d.rectangle((x0 - 1, 2, x1 + 1, STRIP_H - 2), fill=FG)
            d.rectangle((x0 + 1, 4, x1 - 1, STRIP_H - 4), fill=col)
        else:
            d.rectangle((x0, 5, x1, STRIP_H - 5), fill=col)
    return im


def panel(img, title, tag, tag_col, crop, scale, kinds=None, cur=None):
    im = img.crop(crop)
    if scale != 1:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    parts = [label_bar(im.width, title, tag, tag_col), im]
    if kinds is not None:
        parts.append(strip(im.width, kinds, cur))
    h = sum(p.height for p in parts)
    out = Image.new("RGB", (im.width, h), BG)
    y = 0
    for p in parts:
        out.paste(p, (0, y)); y += p.height
    return out


def grid(panels, cols):
    rows = [panels[i:i + cols] for i in range(0, len(panels), cols)]
    w = max(sum(p.width for p in r) + GAP * (len(r) - 1) for r in rows) + 2 * GAP
    h = sum(max(p.height for p in r) for r in rows) + GAP * (len(rows) + 1)
    out = Image.new("RGB", (w, h), BG)
    y = GAP
    for r in rows:
        x = GAP
        for p in r:
            out.paste(p, (x, y)); x += p.width + GAP
        y += max(p.height for p in r) + GAP
    return out


def footer(img, text, legend=False):
    out = Image.new("RGB", (img.width, img.height + 26), BG)
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    y = img.height + 11
    d.text((GAP + 4, y), text, font=F_R, fill=MUTED, anchor="lm")
    if legend:
        x = img.width - GAP - 4
        for name, col in reversed((("rendered", REAL), ("generated", ACCENT), ("repeated", (72, 79, 88)))):
            x -= d.textlength(name, font=F_R)
            d.text((x, y), name, font=F_R, fill=MUTED, anchor="lm")
            x -= 16
            d.rectangle((x, y - 5, x + 10, y + 5), fill=col)
            x -= 14
    return out


def encode(frames, name, fps, colors=192, dither="bayer:bayer_scale=4"):
    tmp = Path(tempfile.mkdtemp(dir=S))
    for i, f in enumerate(frames):
        f.save(tmp / f"{i:04d}.png")
    out = DST / name
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", str(tmp / "%04d.png"),
                    "-filter_complex",
                    f"[0]split[a][b];[a]palettegen=max_colors={colors}:stats_mode=full[p];"
                    f"[b][p]paletteuse=dither={dither}:diff_mode=rectangle",
                    "-loop", "0", str(out)], check=True)
    shutil.rmtree(tmp)
    print(f"{name}: {len(frames)} frames, {out.stat().st_size / 1e6:.2f} MB, {frames[0].size}")




def want(name):
    return not WHICH or name in WHICH


ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("build", type=Path)
ap.add_argument("work", type=Path)
ap.add_argument("out", type=Path, nargs="?", default=ROOT / "docs/visuals")
ap.add_argument("--only", default="")
A = ap.parse_args()
WHICH = set(filter(None, A.only.split(",")))
S = A.work.resolve()
DST = A.out
DST.mkdir(parents=True, exist_ok=True)
prepare(A.build.resolve(), S)

DEMO_CROP = (0, 44, 960, 484)
DEMO = S / "d120"


def window_kinds(kindf, t, n):
    """Kinds of the n displayed frames of the window that holds t."""
    t0 = (t // n) * n
    return [kindf(t0 + i) for i in range(n)], t - t0


# 1. hero: 30 fps game vs x4 -------------------------------------------------
if want("hero"):
    tl = timeline(S / "out/d_interp", DEMO, 4)
    game = held(DEMO, 4)
    frames = []
    for t in range(8, 168):
        kg, c = window_kinds(lambda u: game(u)[1], t, 8)
        ke, _ = window_kinds(lambda u: tl[u][1], t, 8)
        a = panel(load(game(t)[0]), "Game alone", "30 fps", REAL, DEMO_CROP, 0.5, kg, c)
        b = panel(load(tl[t][0]), "chuds-fg ×4", "120 fps", ACCENT, DEMO_CROP, 0.5, ke, c)
        frames.append(footer(grid([a, b], 2), "Vulkan demo · real engine output · 4× slow motion", True))
    encode(frames, "hero-x4.gif", 30, 96, "none")

# 2. multipliers ---------------------------------------------------------------
if want("mult"):
    tls = {8: timeline(S / "out/m8", DEMO, 8, 1), 4: timeline(S / "out/m4", S / "d120_s2", 4, 2),
           2: timeline(S / "out/m2", S / "d120_s4", 2, 4)}
    game = held(DEMO, 8)

    def view(m):
        if m == 1:
            return lambda t: game(t)
        step = 8 // m
        return lambda t: (tls[m][(t // step) * step][0],
                          tls[m][(t // step) * step][1] if t % step == 0 else "held")

    frames = []
    for t in range(16, 144):
        ps = []
        for m, tag in ((1, "15 fps"), (2, "30 fps"), (4, "60 fps"), (8, "120 fps")):
            v = view(m)
            k, c = window_kinds(lambda u: v(u)[1], t, 16)
            ps.append(panel(load(v(t)[0]), "Game alone" if m == 1 else f"×{m}", tag,
                            REAL if m == 1 else ACCENT, DEMO_CROP, 0.5, k, c))
        frames.append(footer(grid(ps, 2), "Same 15 fps input · real engine output · 4× slow motion", True))
    encode(frames, "multipliers.gif", 30, 96, "none")

# 3. modes ---------------------------------------------------------------------
def err_map(img, truth):
    e = np.abs(np.asarray(img, np.float32) - np.asarray(truth, np.float32)).mean(-1)
    e = np.clip(e / 24.0, 0, 1)[..., None]
    lo = np.array(BG, np.float32); hi = np.array((255, 166, 87), np.float32)
    return Image.fromarray((lo * (1 - e) + hi * e).astype(np.uint8))


if want("modes"):
    tls = [("Interpolation", "between two frames", ACCENT, timeline(S / "out/d_interp", DEMO, 4)),
           ("Hybrid", "around the real frame", ACCENT, timeline(S / "out/d_hybrid", DEMO, 4)),
           ("Extrapolation", "predicts ahead", WARN, timeline(S / "out/d_extrap", DEMO, 4))]
    crop = (240, 44, 960, 484)
    frames = []
    for t in range(12, 108):
        truth = load(DEMO / f"f{t:04d}.ppm")
        ps = []
        for name, tag, col, tl in tls:
            ps.append(panel(load(tl[t][0]), name, tag, col, crop, 0.42))
        for name, tag, col, tl in tls:
            ps.append(panel(err_map(load(tl[t][0]), truth), "Error vs. ground truth", "", col, crop, 0.42))
        frames.append(footer(grid(ps, 3), "30 fps input, ×4 · each frame compared with the rendered image of its moment · 4× slow motion"))
    encode(frames, "modes.gif", 30, 96, "none")

# 4. cross-fade vs optical flow -----------------------------------------------
if want("blend"):
    tl = timeline(S / "out/m2", S / "d120_s4", 2, 4)   # x2 of a 15 fps game: large motion
    crop = (120, 80, 440, 400)
    frames = []
    for t in range(8, 160):
        if t % 4:
            continue
        a, b = (t // 8) * 8, (t // 8) * 8 + 8
        w = (t - a) / 8
        A = np.asarray(load(DEMO / f"f{a:04d}.ppm"), np.float32)
        B = np.asarray(load(DEMO / f"f{b:04d}.ppm"), np.float32)
        fade = Image.fromarray((A * (1 - w) + B * w + 0.5).astype(np.uint8))
        kind = "real" if t % 8 == 0 else "gen"
        ps = [panel(fade, "Cross-fade", "ghosting", WARN, crop, 1.0),
              panel(load(tl[t][0]), "chuds-fg", "motion-compensated", ACCENT, crop, 1.0),
              panel(load(DEMO / f"f{t:04d}.ppm"), "Ground truth", "", REAL, crop, 1.0)]
        g = grid(ps, 3)
        frames += [footer(g, ("Generated frame" if kind == "gen" else "Rendered frame") +
                          " · 15 fps input, ×2 · real engine output")] * (6 if kind == "gen" else 3)
    encode(frames, "crossfade-vs-flow.gif", 10, 160, "none")

# 5. optical flow --------------------------------------------------------------
def flow_rgb(path):
    b = path.read_bytes()
    w, h, blk, lw, lh = np.frombuffer(b[4:24], np.uint32)
    fwd = np.frombuffer(b[28:28 + w * h * 8], np.float32).reshape(h, w, 2)
    u, v = fwd[..., 0], fwd[..., 1]
    mag = np.sqrt(u * u + v * v)
    ang = (np.arctan2(v, u) / (2 * np.pi)) % 1.0
    val = np.clip(mag / 16.0, 0, 1) ** 0.6
    hsv = np.stack([ang * 255, np.full_like(ang, 215), val * 255], -1).astype(np.uint8)
    im = Image.fromarray(hsv, "HSV").convert("RGB")
    return im.resize((960, 540), Image.NEAREST)


if want("flow"):
    frames = []
    for k in range(1, 70):
        f = S / f"out/d_flow/flow_{k:04d}.bin"
        if not f.exists():
            continue
        ps = [panel(load(DEMO / f"f{k * 4:04d}.ppm"), "Rendered frame", "", REAL, DEMO_CROP, 0.5),
              panel(flow_rgb(f), "Estimated motion", "hue = direction", ACCENT, DEMO_CROP, 0.5)]
        frames.append(footer(grid(ps, 2), "Forward optical flow of each 30 fps pair (the backdrop scrolls too) · brightness = speed"))
    encode(frames, "optical-flow.gif", 10)

# 6. game-like scene ------------------------------------------------------------
if want("game"):
    seq = S / "seq/fps"
    tl = timeline(S / "out/fps_x4", seq, 4)
    game = held(seq, 4)
    crop = (0, 0, 1280, 720)
    frames = []
    for t in range(8, 72):
        kg, c = window_kinds(lambda u: game(u)[1], t, 8)
        ke, _ = window_kinds(lambda u: tl[u][1], t, 8)
        a = panel(load(game(t)[0]), "Game alone", "30 fps", REAL, crop, 0.375, kg, c)
        b = panel(load(tl[t][0]), "chuds-fg ×4", "120 fps", ACCENT, crop, 0.375, ke, c)
        frames.append(footer(grid([a, b], 2), "Synthetic first-person turn · motion blur, static HUD, held weapon · 4× slow motion", True))
    encode(frames, "game-scene-x4.gif", 30, 128, "none")

