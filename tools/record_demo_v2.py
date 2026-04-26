import time, os, threading
from PIL import ImageGrab, Image, ImageDraw
import ctypes
from ctypes import wintypes

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_with_cursor.gif')
FPS = 3
DURATION_SEC = 60
TOTAL = FPS * DURATION_SEC
TARGET_W, TARGET_H = 1280, 720

# 鼠标光标绘制（简单十字+圆圈）
def draw_cursor(img, x, y):
    draw = ImageDraw.Draw(img)
    r = 8  # 光标半径
    # 外圈（红色）
    draw.ellipse([x-r, y-r, x+r, y+r], outline='red', width=2)
    # 十字线
    draw.line([x-r-2, y, x+r+2, y], fill='red', width=2)
    draw.line([x, y-r-2, x, y+r+2], fill='red', width=2)
    # 中心点
    draw.ellipse([x-2, y-2, x+2, y+2], fill='red')
    return img

# Windows API 获取鼠标位置
def get_mouse_pos():
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

print(f'=== 天枢 AI Agent 5幕演示录屏 (带鼠标光标) ===')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')
print('3秒后开始录制...')
time.sleep(3)

frames = []
for i in range(TOTAL):
    t0 = time.time()
    # 截图
    img = ImageGrab.grab().convert('RGB')
    # 获取鼠标位置并绘制光标
    try:
        mx, my = get_mouse_pos()
        # 如果缩放分辨率，需要按比例调整鼠标坐标
        sw, sh = img.size
        scale_x = TARGET_W / sw
        scale_y = TARGET_H / sh
        mx = int(mx * scale_x)
        my = int(my * scale_y)
        img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
        draw_cursor(img, mx, my)
    except Exception as e:
        img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    img = img.quantize(colors=128).convert('RGB')
    frames.append(img)
    elapsed = time.time() - t0
    time.sleep(max(0, (1.0/FPS) - elapsed))
    if (i + 1) % (FPS * 5) == 0:
        print(f'  {(i+1)//FPS}/{DURATION_SEC}s...')

print(f'Saving {len(frames)} frames as GIF...')
frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=int(1000/FPS),
    loop=0,
    optimize=True
)
sz = os.path.getsize(OUTPUT)
print(f'Done: {OUTPUT} ({sz//1024}KB)')
