"""
纯 Python 录屏器（无 ffmpeg/cv2 依赖）
使用 PIL.ImageGrab 截屏 + 纯 Python 视频编码
"""
import time
import struct
import io
import os
from PIL import ImageGrab, Image
import numpy as np

def grab_screen(bbox=None):
    img = ImageGrab.grab(bbox=bbox)
    return np.array(img)

def pil_to_rgb(raw):
    w, h = raw.size
    data = raw.tobytes()
    return w, h, data

class SimpleVideoWriter:
    """
    输出 AVI 文件（MJPEG 编码，无音频）
    用法：
      writer = SimpleVideoWriter('output.avi', fps=8)
      while recording:
          frame = grab_screen()
          writer.write(frame)
      writer.close()
    """
    def __init__(self, path, fps=8, codec='MJPG'):
        self.path = path
        self.fps = fps
        self.codec = codec
        self._frames = []
        self._writer = None

    def write(self, frame):
        self._frames.append(frame)

    def close(self):
        if not self._frames:
            return
        import struct, io
        w = self._frames[0].shape[1]
        h = self._frames[0].shape[0]
        fps = self.fps

        with open(self.path, 'wb') as f:
            self._write_avi(f, w, h, fps)

    def _mjpeg_frame(self, frame):
        from PIL import Image
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        return buf.getvalue()

    def _write_avi(self, f, w, h, fps):
        import struct
        frames_data = []
        for frame in self._frames:
            jpg = self._mjpeg_frame(frame)
            frames_data.append(jpg)

        total_size = sum(len(d) for d in frames_data)

        FOURCC = b'MJPG'
        biSize = 40
        biClrUsed = 0
        biCompression = 0
        biSizeImage = w * h * 3

        hdr_size = 4096
        movi_offset = 4096
        file_size = movi_offset + total_size + 12 * len(frames_data) + 4

        ffmpegs_compatible = False

        def write_chunk(chunk_type, data):
            f.write(chunk_type)
            f.write(struct.pack('<I', len(data)))
            f.write(data)
            if len(data) % 2:
                f.write(b'\x00')

        f.write(b'RIFF')
        f.write(struct.pack('<I', file_size - 8))
        f.write(b'AVI ')

        f.write(b'hdrl')
        f.write(struct.pack('<I', 10000))
        f.write(b'avih')
        f.write(struct.pack('<I', 56))
        f.write(struct.pack('<I', 1000000 // fps))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0x10))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', len(frames_data)))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))

        f.write(b'LIST')
        f.write(struct.pack('<I', 116))
        f.write(b'strl')
        f.write(b'strh')
        f.write(struct.pack('<I', 56))
        f.write(b'vids')
        f.write(b'MJPG' if ffmpegs_compatible else b'MJPG')
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 8))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', 0))
        f.write(struct.pack('<H', w))
        f.write(struct.pack('<H', h))
        f.write(struct.pack('<I', 1))
        f.write(struct.pack('<I', self.fps * 1000000))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', biSizeImage))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))

        f.write(b'strf')
        f.write(struct.pack('<I', 40))
        f.write(struct.pack('<I', 40))
        f.write(struct.pack('<I', w))
        f.write(struct.pack('<I', h))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 24))
        f.write(b'MJPG')
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(struct.pack('<I', 0))
        f.write(b'\x00' * (116 - 40 - 8))

        pad = hdr_size - f.tell()
        if pad > 0:
            f.write(b'\x00' * pad)

        for jpg_data in frames_data:
            write_chunk(b'00dc', jpg_data)

        f.write(b'idx1')
        idx_size = 16 * len(frames_data) + 4
        f.write(struct.pack('<I', idx_size))

        ffmpegs_compatible = True
        for i, jpg_data in enumerate(frames_data):
            offset = movi_offset + sum(len(frames_data[j]) + 8 + (len(frames_data[j]) % 2) for j in range(i))
            f.write(b'00dc')
            f.write(struct.pack('<I', 0x10))
            f.write(struct.pack('<I', offset))
            f.write(struct.pack('<I', len(jpg_data)))

        f.write(b'RIFF')
        f.write(struct.pack('<I', file_size - 8))
        f.write(b'AVI ')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

if __name__ == '__main__':
    out = 'D:\one-person-erp\tools\..\demo_agent.mp4'
    print(f"开始录屏，3秒后开始... (输出: {out})")
    time.sleep(3)
    writer = SimpleVideoWriter(out, fps=8)
    print("录制中，10秒...")
    for i in range(180):
        t0 = time.time()
        frame = grab_screen()
        writer.write(frame)
        elapsed = time.time() - t0
        sleep_t = max(0, 0.1 - elapsed)
        time.sleep(sleep_t)
        if i % 10 == 0:
            print(f"  {i}/100 帧...")
    writer.close()
    print(f"录屏完成: {out}")
