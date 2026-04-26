import time, os, sys
from PIL import ImageGrab, Image, ImageDraw
import ctypes
from ctypes import wintypes

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_final_v4.gif')
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
    r = 12
    # 确保坐标在图片范围内
    x = max(r+5, min(img.size[0]-r-5, x))
    y = max(r+5, min(img.size[1]-r-5, y))
    # 外圈白色描边
    draw.ellipse([x-r-3, y-r-3, x+r+3, y+r+3], outline='white', width=4)
    # 内圈红色
    draw.ellipse([x-r, y-r, x+r, y+r], outline='red', width=3)
    # 十字线白色描边
    draw.line([x-r-6, y, x+r+6, y], fill='white', width=4)
    draw.line([x, y-r-6, x, y+r+6], fill='white', width=4)
    # 十字线红色
    draw.line([x-r-3, y, x+r+3, y], fill='red', width=2)
    draw.line([x, y-r-3, x, y+r+3], fill='red', width=2)
    # 中心点
    draw.ellipse([x-4, y-4, x+4, y+4], fill='red')
    draw.ellipse([x-2, y-2, x+2, y+2], fill='white')
    return img

print(f'=== 天枢 AI Agent 演示录屏 v4 (带鼠标光标) ===')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')

# 获取DPI缩放
dpi_scale = get_dpi_scale()
print(f'DPI Scale: {dpi_scale:.2f}')

# 先截一张图看看屏幕尺寸
print('检测屏幕尺寸...')
test_img = ImageGrab.grab()
print(f'屏幕截图尺寸: {test_img.size}')

# 计算截图区域（只截取浏览器窗口区域，排除左侧Trae侧边栏）
# 假设浏览器在右侧，从x=400开始截取
# 实际应该根据窗口位置调整
sw, sh = test_img.size
print(f'全屏尺寸: {sw}x{sh}')

# 如果屏幕宽度大于1280，尝试居中截取
if sw > TARGET_W:
    left = (sw - TARGET_W) // 2
    top = (sh - TARGET_H) // 2
    if top < 0:
        top = 0
    if left < 0:
        left = 0
else:
    left = 0
    top = 0

print(f'截取区域: left={left}, top={top}, width={TARGET_W}, height={TARGET_H}')
print('3秒后开始录制，请将浏览器窗口放在屏幕中央...')
time.sleep(3)

frames = []
for i in range(TOTAL):
    t0 = time.time()
    # 截图指定区域
    img = ImageGrab.grab(bbox=(left, top, left + TARGET_W, top + TARGET_H)).convert('RGB')
    iw, ih = img.size

    # 获取鼠标物理坐标
    mx, my = get_mouse_pos()

    # 计算相对于截图区域的坐标
    mx_rel = mx - left
    my_rel = my - top

    # 如果鼠标在截图区域内，绘制光标
    if 0 <= mx_rel < iw and 0 <= my_rel < ih:
        draw_cursor(img, mx_rel, my_rel)
    else:
        # 在边界处绘制一个指示器
        draw = ImageDraw.Draw(img)
        bx = max(10, min(iw-10, mx_rel))
        by = max(10, min(ih-10, my_rel))
        draw.ellipse([bx-5, by-5, bx+5, by+5], outline='yellow', width=2)

    # 减少颜色数以减小文件大小
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
