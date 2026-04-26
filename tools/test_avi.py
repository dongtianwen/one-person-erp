import time, struct, io, os
from PIL import ImageGrab, Image

OUTPUT = os.path.join(os.path.dirname(__file__), 'test_avi.avi')
FPS = 8; SEC = 5; TOTAL = FPS * SEC

print(f'Test {SEC}s recording...')
time.sleep(1)
frames = []
for i in range(TOTAL):
    t0 = time.time()
    img = ImageGrab.grab().convert('RGB')
    frames.append(img)
    elapsed = time.time() - t0
    time.sleep(max(0, (1.0/FPS) - elapsed))
    if (i+1) % FPS == 0: print(f'  {(i+1)//FPS}/{SEC}s')

print('Encoding...')
jpg_data = []
for f in frames:
    b = io.BytesIO()
    f.save(b, format='JPEG', quality=80)
    jpg_data.append(b.getvalue())

w, h = frames[0].size; n = len(jpg_data)
padded = [d + b'\x00' if len(d)%2 else d for d in jpg_data]
movi_sz = sum(len(p)+8 for p in padded); hdr = 4096

with open(OUTPUT,'wb') as f:
    rsz = 4 + hdr + 12 + movi_sz + 8 + 16*n + 4
    f.write(b'RIFF'); f.write(struct.pack('<I',rsz-8)); f.write(b'AVI ')
    hs = f.tell()
    f.write(b'LIST'); f.write(struct.pack('<I',10000)); f.write(b'hdrl')
    f.write(b'avih'); f.write(struct.pack('<I',56))
    upf = int(1000000/FPS)
    f.write(struct.pack('<IIIII', upf, 0, 0x10, 0, n))
    f.write(struct.pack('<IIII', 0, 1, 0, w))
    f.write(struct.pack('<Ii', h, 0)); f.write(b'\x00'*16)
    f.write(b'LIST'); f.write(struct.pack('<I',116)); f.write(b'strl')
    f.write(b'strh'); f.write(struct.pack('<I',56))
    f.write(b'vidsMJPG')
    f.write(struct.pack('<IIHHII', 0, 0, 0, 0, 1, FPS))
    f.write(struct.pack('<IIIIII', 0, n, w*h*3, 0, 0, 0))
    f.write(struct.pack('<HHHH', 0, 0, w, h))
    f.write(b'strf'); f.write(struct.pack('<I',40))
    f.write(struct.pack('<iiHH4sIII', w, h, 1, 24, b'MJPG', w*h*3, 0, 0))
    pad = hdr - (f.tell() - hs) - 8
    if pad > 0: f.write(b'\x00'*pad)
    he = f.tell(); f.seek(hs+4); f.write(struct.pack('<I',he-hs-8)); f.seek(he)
    f.write(b'LIST'); f.write(struct.pack('<I',movi_sz+4)); f.write(b'movi')
    offs = []
    for i,p in enumerate(padded):
        offs.append(f.tell())
        f.write(b'00dc'+struct.pack('<I',len(p))+p)
    f.write(b'idx1'); f.write(struct.pack('<I',16*n))
    for i in range(n):
        f.write(b'00dc'+struct.pack('<III',0x10,offs[i],len(jpg_data[i])))
    t = f.tell(); f.seek(2); f.write(struct.pack('<I',t-8))

sz = os.path.getsize(OUTPUT)
with open(OUTPUT,'rb') as f:
    d = f.read()
    print(f'Done: {sz//1024}KB | movi={d.find(b"movi")} idx1={d.find(b"idx1")}')
