#!/bin/bash
# 启动 Kit 的 X11 桌面 (Xvfb :99)
pkill -f "[X]vfb :99" 2>/dev/null
sleep 1
Xvfb :99 -screen 0 1280x800x24 >/tmp/xvfb.log 2>&1 &
sleep 2
python3 ~/workspace/gui-desktop/desktop.py
cp /tmp/kit-desktop.png ~/workspace/gui-desktop/desktop.png
echo "desktop running, screenshot: ~/workspace/gui-desktop/desktop.png"
