# x11-cloud-desktop

A real X11 desktop drawn entirely in pure Python — no window manager, no desktop
environment. Runs on [Xvfb](https://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml)
and paints windows directly with
[python-xlib](https://github.com/python-xlib/python-xlib), then screenshots
itself with `GetImage`.

Built for a cloud VM where `apt` couldn't install a desktop stack, so the whole
GUI is one self-contained script.

## Files

- `desktop.py` — the desktop: opens a real X11 window on Xvfb, draws a
  wallpaper, top bar (live CPU / memory / clock from `/proc`), terminal-style
  panels and icons with PIL, and writes a screenshot to `/tmp/kit-desktop.png`.
  Gotchas handled in code: `PutImage` requests are chunked (≤ 256 KB each) and
  the window is mapped before drawing, otherwise Xvfb drops the content.
- `start.sh` — boots Xvfb on `:99`, runs the desktop, copies the screenshot to
  `desktop.png`.
- `desktop.png` — sample screenshot.

## Run

```bash
pip install --break-system-packages python-xlib pillow
./start.sh
```

Then open `desktop.png` to see the result. Requires a Linux box with Xvfb and
the Noto CJK / DejaVu fonts (falls back to PIL's default font if missing).
