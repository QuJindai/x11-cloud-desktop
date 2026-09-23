#!/usr/bin/env python3
"""Kit's real X11 desktop: draws real X windows on Xvfb and screenshots them."""
import os, subprocess, time, datetime, shutil
from Xlib import X, display
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 800
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
CJK_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

F_TITLE = font(CJK_B, 56)
F_SUB = font(CJK, 26)
F_BAR = font(CJK_B, 15)
F_TERM = font(MONO, 15)
F_TERM_CJK = font(CJK, 15)
F_PANEL = font(CJK_B, 15)
F_ICON = font(CJK, 13)

# ---------- real system data ----------
def sh(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def cpu_percent():
    def snap():
        p = open("/proc/stat").readline().split()[1:]
        p = list(map(int, p))
        return p[0] + p[2], sum(p)  # user+nice, total
    a_idle, a_tot = snap(); time.sleep(0.4)
    b_idle, b_tot = snap()
    tot = b_tot - a_tot
    return round(100 * (1 - (b_idle - a_idle) / tot), 1) if tot else 0.0

def mem_info():
    m = {}
    for line in open("/proc/meminfo"):
        k, v = line.split(":")
        if k in ("MemTotal", "MemAvailable"):
            m[k] = int(v.split()[0])
    total = m["MemTotal"] / 1024 / 1024
    used = (m["MemTotal"] - m["MemAvailable"]) / 1024 / 1024
    return total, used

def disk_info():
    d = shutil.disk_usage("/")
    return d.total / 1e9, d.used / 1e9

UPTIME_S = float(open("/proc/uptime").read().split()[0])
LOAD = os.getloadavg()
CPU_P = cpu_percent()
MEM_T, MEM_U = mem_info()
DISK_T, DISK_U = disk_info()
HOST = sh("hostname")
UNAME = sh("uname -srm")
NPROC = sh("nproc")
NOW = datetime.datetime.now()
CLOCK = NOW.strftime("%H:%M")
DATESTR = NOW.strftime("%m-%d %a")

up_h, up_m = int(UPTIME_S // 3600), int(UPTIME_S % 3600 // 60)

def put_image_tiled(win, gc, img):
    """PutImage in bands: a single X request is limited to 64K 4-byte units."""
    w, h = img.size
    data = pil_to_x(img)
    stride = w * 4
    band_h = max(1, 200000 // stride)
    for y0 in range(0, h, band_h):
        bh = min(band_h, h - y0)
        win.put_image(gc, 0, y0, w, bh, X.ZPixmap, 24, 0,
                      data[y0 * stride:(y0 + bh) * stride])

# ---------- pixel format helpers (X11 BGRX <-> PIL RGB) ----------
def pil_to_x(raw_rgb_img):
    rgb = raw_rgb_img.convert("RGB").tobytes()
    n = raw_rgb_img.width * raw_rgb_img.height
    out = bytearray(n * 4)
    out[0::4] = rgb[2::3]
    out[1::4] = rgb[1::3]
    out[2::4] = rgb[0::3]
    out[3::4] = b"\x00" * n
    return bytes(out)

def x_to_pil(raw, w, h):
    n = w * h
    out = bytearray(n * 3)
    out[0::3] = raw[2::4]
    out[1::3] = raw[1::4]
    out[2::3] = raw[0::4]
    return Image.frombytes("RGB", (w, h), bytes(out))

# ---------- wallpaper ----------
def make_wallpaper(shadows):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            px[x, y] = (int(18 + t * 26), int(20 + t * 52), int(52 + t * 96))
    d = ImageDraw.Draw(img, "RGBA")
    for cx, cy, rad, col in [(180, 140, 150, (56, 189, 248)),
                             (1120, 660, 180, (129, 140, 248)),
                             (1080, 120, 100, (45, 212, 191))]:
        for rr in range(rad, 0, -4):
            a = (1 - rr / rad) * 40
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (int(a),))
    # window shadows
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for (x, y, w, h) in shadows:
        ds.rounded_rectangle([x + 7, y + 9, x + w + 7, y + h + 9], 10, fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img.convert("RGBA"), sh).convert("RGB")
    d = ImageDraw.Draw(img)
    # title in free zone (below terminal window)
    d.text((90, 588), "Kit 的云电脑", font=F_TITLE, fill=(255, 255, 255))
    d.text((92, 664), f"Ubuntu 24.04 · 真实 X11 桌面 · {HOST}", font=F_SUB, fill=(190, 205, 235))
    # desktop icons
    icons = [("主文件夹", (96, 165, 250)), ("终端", (52, 199, 123)), ("系统监视器", (250, 150, 90))]
    for i, (label, col) in enumerate(icons):
        ix, iy = 26, 24 + i * 104
        d.rounded_rectangle([ix, iy, ix + 64, iy + 64], 14, fill=col)
        sym = ["🗀", ">_", "▦"][i]
        f = font(CJK_B, 24)
        bb = d.textbbox((0, 0), sym, font=f)
        d.text((ix + 32 - (bb[2] - bb[0]) / 2, iy + 32 - (bb[3] - bb[1]) / 2 - bb[1]),
               sym, font=f, fill=(255, 255, 255))
        f2 = F_ICON
        bb = d.textbbox((0, 0), label, font=f2)
        d.text((ix + 32 - (bb[2] - bb[0]) / 2, iy + 70), label, font=f2, fill=(230, 235, 245))
    return img

def title_bar_img(w, title):
    bar = Image.new("RGB", (w, 32))
    d = ImageDraw.Draw(bar)
    for x in range(w):
        t = x / w
        d.line([(x, 0), (x, 32)], fill=(int(59 + t * 20), int(90 + t * 14), int(216 - t * 40)))
    d.text((12, 6), title, font=F_BAR, fill=(255, 255, 255))
    for i, ch in enumerate("— ▢ ✕"):
        pass
    # min/max/close
    bx = w - 30
    for col, glyph in [((70, 120, 200), "—"), ((70, 120, 200), "▢"), ((220, 80, 80), "✕")]:
        d.rounded_rectangle([bx, 6, bx + 22, 24], 5, fill=col)
        f = font(CJK, 11)
        bb = d.textbbox((0, 0), glyph, font=f)
        d.text((bx + 11 - (bb[2] - bb[0]) / 2, 7), glyph, font=f, fill=(255, 255, 255))
        bx -= 28
    return bar

def terminal_img(w, h):
    img = Image.new("RGB", (w, h), (22, 22, 30))
    d = ImageDraw.Draw(img)
    lines = [
        ("kit@cloud:~$ ", "cat /etc/os-release | head -2", None),
        (None, 'NAME="Ubuntu"', None),
        (None, 'VERSION="24.04 LTS (Noble Numbat)"', None),
        ("kit@cloud:~$ ", "uname -m && nproc", None),
        (None, f"{UNAME.split()[2]}", None),
        (None, f"{NPROC} vCPU", None),
        ("kit@cloud:~$ ", "uptime", None),
        (None, f"up {up_h}h {up_m}min, load average: {LOAD[0]:.2f} {LOAD[1]:.2f} {LOAD[2]:.2f}", None),
        ("kit@cloud:~$ ", "free -h | head -2", None),
        (None, f"Mem:  total {MEM_T:.1f}G   used {MEM_U:.1f}G", None),
        ("kit@cloud:~$ ", 'echo "这是真实的 X11 桌面"', None),
        (None, "这是真实的 X11 桌面", None),
        ("kit@cloud:~$ ", "█", None),
    ]
    y = 10
    for prompt, text, _ in lines:
        x = 10
        if prompt:
            d.text((x, y), prompt, font=F_TERM, fill=(125, 211, 252))
            x += d.textlength(prompt, font=F_TERM)
        is_cjk = any(ord(c) > 127 for c in text)
        d.text((x, y), text, font=F_TERM_CJK if is_cjk else F_TERM, fill=(74, 222, 128))
        y += 24
        if y > h - 20:
            break
    return img

def bar(d, x, y, w, label, pct, val_text):
    d.text((x, y), label, font=F_TERM_CJK, fill=(200, 205, 220))
    d.text((x + 90, y), val_text, font=F_TERM_CJK, fill=(255, 255, 255))
    bx, by, bw, bh = x, y + 24, w, 16
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 8, fill=(45, 48, 60))
    fw = int(bw * min(pct, 100) / 100)
    col = (74, 222, 128) if pct < 70 else (250, 200, 90) if pct < 90 else (248, 113, 113)
    if fw > 0:
        d.rounded_rectangle([bx, by, bx + fw, by + bh], 8, fill=col)
    d.text((bx + bw + 10, y + 20), f"{pct:.1f}%", font=F_TERM_CJK, fill=(200, 205, 220))

def monitor_img(w, h):
    img = Image.new("RGB", (w, h), (24, 25, 34))
    d = ImageDraw.Draw(img)
    d.text((16, 12), "CPU", font=F_BAR, fill=(255, 255, 255))
    bar(d, 16, 44, w - 110, "CPU", CPU_P, f"{NPROC} 核")
    bar(d, 16, 110, w - 110, "内存", MEM_U / MEM_T * 100, f"{MEM_U:.1f}/{MEM_T:.1f}G")
    bar(d, 16, 176, w - 110, "磁盘", DISK_U / DISK_T * 100, f"{DISK_U:.1f}/{DISK_T:.1f}G")
    d.text((16, 246), f"平均负载 {LOAD[0]:.2f} {LOAD[1]:.2f} {LOAD[2]:.2f}",
           font=F_TERM_CJK, fill=(160, 165, 180))
    return img

def panel_img():
    img = Image.new("RGB", (W, 38), (26, 27, 34))
    d = ImageDraw.Draw(img)
    d.line([(0, 0), (W, 0)], fill=(60, 63, 80), width=1)
    # start button
    d.rounded_rectangle([8, 6, 86, 32], 8, fill=(59, 91, 214))
    d.text((20, 9), "◉ Kit", font=F_PANEL, fill=(255, 255, 255))
    # task buttons
    x = 96
    for t in ["终端 — kit@cloud", "系统监视器"]:
        tw = int(d.textlength(t, font=F_PANEL)) + 28
        d.rounded_rectangle([x, 6, x + tw, 32], 8, fill=(45, 48, 60))
        d.text((x + 14, 9), t, font=F_PANEL, fill=(220, 225, 235))
        x += tw + 8
    # clock
    d.text((W - 150, 9), f"{CLOCK}  {DATESTR}", font=F_PANEL, fill=(220, 225, 235))
    return img

# ---------- X11 session ----------
TERM = (90, 70, 680, 450)
MON = (800, 110, 390, 320)
PANEL = (0, 762, W, 38)

def main():
    dpy = display.Display(":99")
    root = dpy.screen().root
    scr = dpy.screen()
    black = scr.black_pixel

    wp = make_wallpaper([TERM, MON])
    gc_root = root.create_gc()
    put_image_tiled(root, gc_root, wp)
    root.map()

    wins = []
    def make_win(geom, content_img, title):
        x, y, w, h = geom
        win = root.create_window(x, y, w, h, 1, X.CopyFromParent,
                                 X.InputOutput, X.CopyFromParent,
                                 background_pixel=black, override_redirect=1)
        gc = win.create_gc()
        full = Image.new("RGB", (w, h), (0, 0, 0))
        full.paste(title_bar_img(w, title), (0, 0))
        full.paste(content_img, (0, 32))
        d = ImageDraw.Draw(full)
        d.rectangle([0, 0, w - 1, h - 1], outline=(90, 95, 115), width=1)
        put_image_tiled(win, gc, full)
        win.map()
        dpy.flush()
        # redraw after map: Xvfb discards drawing to unmapped windows
        put_image_tiled(win, gc, full)
        wins.append(win)
        return win

    make_win(TERM, terminal_img(TERM[2], TERM[3] - 32), "kit@cloud: ~ — 终端")
    make_win(MON, monitor_img(MON[2], MON[3] - 32), "系统监视器")

    px, py, pw, ph = PANEL
    panel = root.create_window(px, py, pw, ph, 0, X.CopyFromParent,
                               X.InputOutput, X.CopyFromParent,
                               background_pixel=black, override_redirect=1)
    pgc = panel.create_gc()
    panel.map()
    dpy.flush()
    put_image_tiled(panel, pgc, panel_img())

    dpy.flush()
    time.sleep(1.0)
    raw = root.get_image(0, 0, W, H, X.ZPixmap, 0xffffffff)
    shot = x_to_pil(raw.data, W, H)
    shot.save("/tmp/kit-desktop.png")
    print("screenshot saved: /tmp/kit-desktop.png", shot.size)
    if os.environ.get("KEEPALIVE"):
        print("keepalive on: holding X connection so windows stay alive", flush=True)
        while True:
            time.sleep(3600)

if __name__ == "__main__":
    main()
