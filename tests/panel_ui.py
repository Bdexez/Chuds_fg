#!/usr/bin/env python3
"""The control panel's window driven without a person, on a virtual display
(tools/ci/panel-check.sh runs it under Xvfb in a container — never on a
desktop): the « Simple » page's game, multiplier, frame limit, priority and
counter, « Démarrer » / « Arrêter », and the « Avancé » page's options (every
one of options_ui.json has its row; « Auto », a value, back to the default;
the search; « Tout réinitialiser ») — each checked in the file the layer
reads. The running game is a stand-in (detect_games), nothing is mirrored
anywhere. Exits 77 (skipped) without GTK 4 or a display.

Usage: panel_ui.py <chuds-fg-gui>"""
import faulthandler
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import traceback

# A home of its own, in the environment the process starts with: the panel
# reads the stand-in game's (this process's) directories from
# /proc/<pid>/environ — set later, the session went to the real home's.
if "CHUDS_FG_PANEL_UI_HOME" not in os.environ:
    home = tempfile.mkdtemp()
    env = dict(os.environ, CHUDS_FG_PANEL_UI_HOME=home, HOME=home, XDG_CONFIG_HOME=os.path.join(home, ".config"),
               XDG_CACHE_HOME=os.path.join(home, ".cache"), XDG_DATA_HOME=os.path.join(home, ".local", "share"),
               CHUDS_FG_STATUS_DIR=os.path.join(home, "run"))
    env.pop("CHUDS_FG_CONFIG", None)
    os.execve(sys.executable, [sys.executable] + sys.argv, env)
os.makedirs(os.environ["CHUDS_FG_STATUS_DIR"])
os.makedirs(os.environ["XDG_CONFIG_HOME"])
if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    print("skipped: no display")
    sys.exit(77)
try:
    loader = importlib.machinery.SourceFileLoader("panel", sys.argv[1])
    spec = importlib.util.spec_from_loader("panel", loader)
    panel = importlib.util.module_from_spec(spec)
    loader.exec_module(panel)
except (ImportError, ValueError) as e:
    print(f"skipped: {e}")
    sys.exit(77)
if not panel.HAVE_GTK:
    print("skipped: no GTK 4")
    sys.exit(77)
from gi.repository import GLib  # noqa: E402

# A game that runs (this process stands for it), armed by the layer.
GAME = os.getpid()
with open(os.path.join(os.environ["CHUDS_FG_STATUS_DIR"], f"{GAME}.status"), "w") as f:
    f.write(f"process=mygame\npid={GAME}\ntime=0\n\n[device 1]\nstate=active\ndevice=Test GPU\n\n"
            "[swapchain 2]\nstate=ready\nsize=1920x1080\nmode=interpolate\nmultiplier=0\ngame_fps=40.0\n"
            "output_fps=40.0\nrefresh_hz=0.0\n")
panel.find_layer = lambda: (True, "chuds_fg.json")
panel.detect_games = lambda: [(GAME, "mygame")]
panel.layer_replaced = lambda pid: False
panel.mirror_config = lambda: None
panel.display_name = lambda pid, name: "MyGame"
panel.calibrate_binary = lambda: None
with open(panel.CONFIG_PATH, "w") as f:
    f.write("[*]\nmultiplier = 2\nmy_own_key = 7\n[mygame]\nmultiplier = 3\n")

failures = []


def check(cond, what):
    if not cond:
        failures.append(what)
        print("FAIL:", what)


def conf(win):
    win.save()
    c = panel.ConfigFile.load()
    return c.glob, c


def row(win, key):
    return next(r for r in win.setting_rows if r.s.key == key)


def steps(win):
    # -- « Simple »
    check(win.stack.get_visible_child_name() == "simple", "opens on « Simple »")
    check(GAME in win.game_rows and win.game_rows[GAME].row.get_title() == "MyGame", "the running game is listed")
    check(win.selected == (GAME, "mygame"), "a single game is selected by itself")
    check(win.hero_btn.get_label() == panel.tr("Démarrer") and win.hero_btn.get_sensitive(), "« Démarrer » offered")
    win._pick_mult("3")
    g, c = conf(win)
    check(g.get("multiplier") == "3" and "target_fps" not in g, f"×3 written: {g}")
    check(g.get("my_own_key") == "7" and c.game_dict("mygame") == {"multiplier": "3"}, "hand-written keys survive")
    check(row(win, "multiplier").value() == "3", "« Avancé » follows « Simple » (multiplier)")
    win._pick_mult("auto")
    g, _ = conf(win)
    check(g.get("target_fps") == "auto" and g.get("multiplier") == str(panel.auto_ceiling()), f"Auto written: {g}")
    win.limit_switch.set_active(True)
    g, _ = conf(win)
    check(g.get("fps_limit", "0").isdigit() and win.limit_row.get_visible(), f"limit on: {g.get('fps_limit')}")
    win._pick_limit("45")
    check(conf(win)[0].get("fps_limit") == "45" and row(win, "fps_limit").value() == "45", "45 i/s")
    win.limit_adj.set_value(50)
    check(conf(win)[0].get("fps_limit") == "50", "another cap typed in")
    win._pick_limit("auto")
    check(conf(win)[0].get("fps_limit") == "auto" and row(win, "fps_limit").value() == "auto", "auto limit")
    win.limit_switch.set_active(False)
    check("fps_limit" not in conf(win)[0] and not win.limit_row.get_visible(), "limit off")
    win.limit_switch.set_active(True)
    check(conf(win)[0].get("fps_limit") == "auto", "limit back on: the cap it had")
    win._pick_mode("extrapolate")
    check(conf(win)[0].get("mode") == "extrapolate", "priority: responsiveness")
    win.hud_switch.set_active(True)
    check(conf(win)[0].get("overlay") == "2", "fps counter on")
    win.on_hero_button(None)
    session = open(os.path.join(os.environ["CHUDS_FG_STATUS_DIR"], "app.session")).read().split()
    check(win.target == (GAME, "mygame") and session[1] == str(GAME), f"Démarrer targets the game: {session}")
    check(win.hero_btn.get_label() == panel.tr("Arrêter") and win.hero_pause.get_visible(), "« Arrêter », « Pause »")
    win.on_pause(None)
    check(conf(win)[0].get("paused") == "1", "paused")
    win.on_pause(None)
    win.on_hero_button(None)
    session = open(os.path.join(os.environ["CHUDS_FG_STATUS_DIR"], "app.session")).read().split()
    check(win.target is None and session[1] == "0", "Arrêter")

    # -- « Avancé »: every option has its row
    win.stack.set_visible_child_name("advanced")
    keys = {r.s.key for r in win.setting_rows}
    missing = {o["key"] for o in panel.OPTIONS} - keys
    check(not missing, f"options without a row: {missing}")
    mb = row(win, "mosaic_blur")
    check(mb.value() == "auto" and "mosaic_blur" not in conf(win)[0], "mosaic_blur on « Auto », not written")
    mb._auto.set_selected(1)
    check(conf(win)[0].get("mosaic_blur") == "1", "mosaic_blur leaves « Auto » at full effect")
    mb._spin.set_value(0)
    check(conf(win)[0].get("mosaic_blur") == "0", "mosaic_blur 0 is written (pins it off)")
    check("chuds-fg-modified" in mb.row.get_css_classes() and mb.reset.get_sensitive(), "modified mark")
    mb.reset.emit("clicked")
    check("mosaic_blur" not in conf(win)[0] and mb.value() == "auto", "back to the default")
    pv = row(win, "pixel_vectors")
    pv._dd.set_selected([c[1] for c in pv.s.choices].index("0"))
    check(conf(win)[0].get("pixel_vectors") == "0", "pixel_vectors forced off")
    sw = row(win, "fps_limit_wait")
    sw._switch.set_active(False)
    check(conf(win)[0].get("fps_limit_wait") == "0", "a switch")
    ll = row(win, "latency_log")
    ll._entry.set_text("/tmp/lat.log")
    ll._entry.emit("activate")
    check(conf(win)[0].get("latency_log") == "/tmp/lat.log", "a text option")
    up = row(win, "render_scale")
    check(not up.row.get_sensitive(), "render scale waits for upscaling")
    row(win, "upscale")._switch.set_active(True)
    check(up.row.get_sensitive() and conf(win)[0].get("render_scale") == "0.67", "upscaling on")
    win.search.set_text("latence" if panel.FRENCH else "latency")
    win._on_search(win.search)
    check(row(win, "max_frame_latency").row.get_visible() and not mb.row.get_visible(), "search filters the rows")
    check(win.cats["motion"]["head"].get_visible() is False or any(
        r.row.get_visible() for _g, rows in win.cats["motion"]["groups"] for r in rows), "empty categories hidden")
    win.search.set_text("")
    win._on_search(win.search)
    check(mb.row.get_visible(), "search cleared")
    win._refresh_counts()
    check(win.reset_all_btn.get_sensitive(), "« Tout réinitialiser » offered")
    win.on_reset_all(None)
    g, _ = conf(win)
    left = {k for k in g if k in keys} - {"multiplier", "target_fps", "mode", "preset", "present_mode",
                                          "require_app", "enabled"}
    check(not left, f"everything back to its default: {left}")
    check(g.get("my_own_key") == "7", "reset keeps hand-written keys")
    # The header menu's actions run (a toast or a dialog, no exception).
    for name in ("copy-steam", "open-config", "about"):
        win.lookup_action(name).activate(None)
    win.stack.set_visible_child_name("simple")
    win.focus_search()
    check(win.stack.get_visible_child_name() == "advanced", "Ctrl+F opens « Avancé »")
    win.close()


def main():
    faulthandler.dump_traceback_later(80, exit=True)   # (a hang: where)
    app = panel.App()
    result = {}

    def drive():
        win = app.get_active_window()
        if win is None:
            return True
        try:
            steps(win)
        except Exception:
            traceback.print_exc()
            failures.append("exception")
        result["done"] = True
        app.quit()
        return False

    GLib.timeout_add(1500, drive)
    GLib.timeout_add_seconds(60, lambda: app.quit() or False)
    app.run([sys.argv[0]])
    if not result.get("done"):
        failures.append("the window never came up")
    print("panel window: " + ("OK" if not failures else f"{len(failures)} failure(s)"))
    return 1 if failures else 0


sys.exit(main())
