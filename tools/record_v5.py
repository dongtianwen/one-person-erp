import time, os
from PIL import ImageGrab, Image

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_agent.gif')
FPS = 4
DURATION_SEC = 15
TOTAL = FPS * DURATION_SEC
# 缩小到 1280x720 减少文件大小，提升兼容性
TARGET_W, TARGET_H = 1280, 720

print(f'Screen Recorder v5 (GIF, {TARGET_W}x{TARGET_H}, optimized)')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')
time.sleep(2)
print('Recording...')

frames = []
for i in range(TOTAL):
    t0 = time.time()
    img = ImageGrab.grab().convert('RGB')
    # 缩小分辨率
    img = img.resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    # 减少颜色数以进一步压缩
    img = img.quantize(colors=128).convert('RGB')
    frames.append(img)
    elapsed = time.time() - t0
    time.sleep(max(0, (1.0/FPS) - elapsed))
    if (i + 1) % FPS == 0:
        print(f'  {(i+1)//FPS}/{DURATION_SEC}s...')

print(f'Saving {len(frames)} frames as optimized GIF...')
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
print('Open with Chrome or any image viewer.')
