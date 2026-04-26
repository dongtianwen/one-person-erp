import time, os
from PIL import ImageGrab, Image

OUTPUT = os.path.join(os.path.dirname(__file__), 'demo_agent.gif')
FPS = 5
DURATION_SEC = 20
TOTAL = FPS * DURATION_SEC

print(f'Screen Recorder v4 (GIF format - universal compatible)')
print(f'Output: {OUTPUT}')
print(f'Duration: {DURATION_SEC}s | FPS: {FPS} | Frames: {TOTAL}')
time.sleep(2)
print('Recording...')
frames = []
for i in range(TOTAL):
    t0 = time.time()
    img = ImageGrab.grab().convert('RGB')
    frames.append(img)
    elapsed = time.time() - t0
    time.sleep(max(0, (1.0/FPS) - elapsed))
    if (i + 1) % FPS == 0:
        print(f'  {(i+1)//FPS}/{DURATION_SEC}s...')

print(f'Saving {len(frames)} frames as GIF...')
frames[0].save(
    OUTPUT,
    save_all=True,
    append_images=frames[1:],
    duration=int(1000/FPS),
    loop=0,
    optimize=False
)
sz = os.path.getsize(OUTPUT)
print(f'Done: {OUTPUT} ({sz//1024}KB) - Open with any browser/image viewer')
