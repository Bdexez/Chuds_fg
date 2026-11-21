#!/usr/bin/env python3
"""Compare default generated frames with the pre-census build on one GPU.

Run under a usable graphical display with two built trees:
    python3 tests/check_matcher_invariant.py build baseline/build
The old commit is pinned in the Linux CI workflow. Real frames are checked
first so a scene or display mismatch cannot masquerade as a flow regression.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from pathlib import Path

import numpy as np
from PIL import Image


def layer_env(build, work):
    """Load exactly this build's layer (see tools/layer_env.sh): old loaders
    ignore VK_IMPLICIT_LAYER_PATH but always search XDG_DATA_HOME."""
    xdg = Path(work) / "vulkan" / "implicit_layer.d"
    xdg.mkdir(parents=True, exist_ok=True)
    for m in (build / "layer").glob("*.json"):
        shutil.copy(m, xdg)
    return {"VK_IMPLICIT_LAYER_PATH": str(build / "layer"), "XDG_DATA_HOME": str(work)}


# The baseline (f2cec5f) predates the rename to chuds-fg: its demo is
# bdex_demo and its layer reads BDEX_FG_* (detected per build, not by commit).
PREFIXES = ("CHUDS_FG", "BDEX_FG")


def naming(build):
    if (build / "demo" / "chuds_fg_demo").exists():
        return "CHUDS_FG", build / "demo" / "chuds_fg_demo"
    if (build / "demo" / "bdex_demo").exists():
        return "BDEX_FG", build / "demo" / "bdex_demo"
    raise RuntimeError(f"no demo (chuds_fg_demo or bdex_demo) in {build / 'demo'}")


def render(build, dump):
    prefix, demo = naming(build)
    # Compare the historical default path, regardless of the caller's game
    # profile or experimental settings, under either name.
    env = {k: v for k, v in os.environ.items()
           if k not in PREFIXES and not k.startswith(tuple(p + "_" for p in PREFIXES))
           and k != "VK_ADD_IMPLICIT_LAYER_PATH"}
    settings = {
        "CONFIG": "/dev/null",
        "PRESET": "balanced",
        "MULTIPLIER": "2",
        "GRAD_WEIGHT": "0",
        # The default since 0.4, absent from the baseline: off for the historical path.
        "ZERO_BIAS_CONTRAST": "0",
        # Likewise (0.6): the histogram gate of the scene-cut fallback, the
        # capped zero bias.
        "SCENE_CUT_HIST": "0",
        "ZERO_BIAS_CAP": "0",
        "HUD": "0",
        # What a discrete GPU turns on by itself with any preset but
        # performance (Config::autoConfigure): off, as on the CI's lavapipe.
        "PIXEL_VECTORS": "0", "INTERP_SPLAT": "0", "ROT_WEIGHT": "0",
        "TEMPORAL_PREDICTION": "0", "ZERO_BIAS": "0.002", "SCENE_CUT_LOCAL": "0",
        "EXTRAPOLATE_SPLAT": "0", "REVEAL_FILL": "0", "GLOBAL_MOTION": "0", "HUD_MASK": "0", "STATIC_SOFT": "0", "INTERP_ACCEL": "0", "FALSE_DETAIL": "0", "BORDER_PREDICT": "0", "BORDER_FILL": "0", "STILL_OCCLUDER": "0", "HUD_AVOID": "0", "MOSAIC_BLUR": "0", "SEARCH_FINE": "2", "SMOOTHNESS": "0.004",
        "LOG": "0",
        "STATS": "0",
        "DUMP": str(dump),
        "DUMP_FRAMES": "24",
    }
    env.update(layer_env(build, Path(dump).parent / f"xdg-{build.resolve().as_posix().replace('/', '_')}"))
    env[prefix] = "1"
    env.update({f"{prefix}_{k}": v for k, v in settings.items()})
    return subprocess.Popen([str(demo), "--fps", "30",
                             "--frames", "12", "--size", "800x600", "--deterministic"],
                            env=env, stdout=subprocess.DEVNULL)


def frames(path, kind):
    files = sorted(path.glob(f"*_{kind}_*.ppm"))
    if not files:
        raise RuntimeError(f"no {kind} frames in {path}")
    last = max(int(p.name.split("_")[0][2:]) for p in files)
    files = [p for p in files if int(p.name.split("_")[0][2:]) == last]
    return [np.asarray(Image.open(p)) for p in files]


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    current, baseline = (Path(p).resolve() for p in sys.argv[1:])
    keep = os.environ.get("CHUDS_FG_INVARIANT_KEEP")
    context = nullcontext(keep) if keep else tempfile.TemporaryDirectory(prefix="chuds-fg-invariant-")
    with context as tmp:
        root = Path(tmp)
        if keep:
            print(f"keeping frame dumps in {root}")
        # Local tiling compositors may require concurrent windows to give both
        # demos one extent. CI's Xvfb has no window manager and runs sequentially.
        processes = []
        try:
            for name, build in (("baseline", baseline), ("current", current)):
                (root / name).mkdir()
                process = render(build, root / name)
                processes.append(process)
                if os.environ.get("CHUDS_FG_INVARIANT_SEQUENTIAL") == "1":
                    if process.wait(timeout=120) != 0:
                        raise RuntimeError(f"{name} demo exited with status {process.returncode}")
            for process in processes:
                if process.poll() is None and process.wait(timeout=120) != 0:
                    raise RuntimeError(f"demo exited with status {process.returncode}")
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
        for kind in ("real", "gen"):
            old = frames(root / "baseline", kind)
            new = frames(root / "current", kind)
            if len(old) != len(new):
                raise AssertionError(f"{kind}: frame count {len(old)} != {len(new)}")
            for i, (a, b) in enumerate(zip(old, new)):
                if a.shape != b.shape:
                    raise AssertionError(f"{kind} frame {i}: window sizes {a.shape} != {b.shape}; run under a fixed display such as Xvfb")
                if not np.array_equal(a, b):
                    difference = np.max(np.abs(a.astype(np.int16) - b.astype(np.int16)))
                    raise AssertionError(f"{kind} frame {i} differs (maximum channel delta {difference})")
            print(f"{kind}: {len(old)} frames byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
