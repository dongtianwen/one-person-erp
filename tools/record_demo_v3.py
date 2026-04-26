import time, os
from PIL import ImageGrab, Image, ImageDraw
import ctypes
from ctypes import wintypes

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_final.gif')
FPS = 3
DURATION_SEC = 60
TOTAL = FPS * DURATION_SEC
TARGET_W, TARGET_H = 1280, 720

# Windows API 获取鼠标位置（物理坐标）
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def get_mouse_pos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

# 获取屏幕DPI缩放比例
def get_dpi_scale():
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except:
        return 1.0

# 绘制鼠标光标（更明显的样式）
def draw_cursor(img, x, y):
    draw = ImageDraw.Draw(img)
    r = 10
    # 外圈白色描边
    draw.ellipse([x-r-2, y-r-2, x+r+2, y+r+2], outline='white', width=3)
    # 内圈红色
    draw.ellipse([x-r, y-r, x+r, y+r], outline='red', width=2)
    # 十字线白色描边
    draw.line([x-r-4, y, x+r+4, y], fill='white', width=3)
    draw.line([x, y-r-4, x, y+r+4], fill='white', width=3)
    # 十字线红色
    draw.line([x-r-2, y, x+r+2, y], fill='red', width=1)
    draw.line([x, y-r-2, x, y+r+2], fill='red', width=1)
    # 中心点
    draw.ellipse([x-3, y-3, x+3, y+3], fill='red')
    return img

print(f'=== 天枢 AI Agent 演示录屏 v3 (带鼠标光标) ===')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')

# 获取DPI缩放
dpi_scale = get_dpi_scale()
print(f'DPI Scale: {dpi_scale:.2f}')
print('3秒后开始录制...')
time.sleep(3)

frames = []
for i in range(TOTAL):
    t0 = time.time()
    # 截图（获取物理像素）
    img = ImageGrab.grab().convert('RGB')
    sw, sh = img.size
    
    # 获取鼠标物理坐标
    mx, my = get_mouse_pos()
    
    # 计算缩放后的坐标（考虑DPI和分辨率缩放）
    scale_x = TARGET_W / sw
    scale_y = TARGET_H / sh
    mx_scaled = int(mx * scale_x)
    my_scaled = int(my * scale_y)
    
    # 缩放图片
    img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    
    # 绘制鼠标光标
    draw_cursor(img, mx_scaled, my_scaled)
    
    # 减少颜色数
    img = img.quantize(colors=128).convert('RGB')
    frames.append(img)
    
    elapsed = time.time() - t0
    sleep_time = max(0, (1.0/FPS) - elapsed)
    time.sleep(sleep_time)
    
    if (i + 1) % (FPS * 5) == 0:
        print(f'  {(i+1)//FPS}/{DURATION_SEC}s...')

print(f'Saving {len(frames)} frames...')
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
