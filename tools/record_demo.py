import time, os, asyncio
from PIL import ImageGrab, Image

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_5_scenes.gif')
FPS = 3
DURATION_SEC = 60  # 总共录制60秒
TOTAL = FPS * DURATION_SEC
TARGET_W, TARGET_H = 1280, 720

print(f'=== 天枢 AI Agent 5幕演示录屏 ===')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')
print('3秒后开始录制...')
time.sleep(3)

frames = []
for i in range(TOTAL):
    t0 = time.time()
    img = ImageGrab.grab().convert('RGB')
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
