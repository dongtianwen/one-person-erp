"""
AI Agent 演示录屏脚本
自动录屏 + 浏览器操作一体化
"""
import subprocess
import time
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDER_PATH = os.path.join(SCRIPT_DIR, 'screen_recorder.py')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'demo_agent.mp4')

def main():
    print("=" * 50)
    print("天枢 AI Agent 演示录屏")
    print("=" * 50)
    print(f"输出文件: {OUTPUT_PATH}")
    print(f"录屏脚本: {RECORDER_PATH}")
    print()

    # 修改录屏脚本为输出 AVI
    with open(RECORDER_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("out = 'd:/one-person-erp/demo.avi'", f"out = '{OUTPUT_PATH}'")
    content = content.replace("fps=10", "fps=8")
    content = content.replace("for i in range(100):", "for i in range(180):")  # 3分钟
    with open(RECORDER_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("[1/3] 录屏脚本已配置（3分钟，8fps）")
    print("[2/3] 等待用户准备好...")
    print("      确保浏览器已打开 http://localhost:5173")
    print("      按 Ctrl+C 取消，或等3秒自动开始...")
    time.sleep(3)

    print("[3/3] 启动录屏...")
    proc = subprocess.Popen(
        [sys.executable, RECORDER_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(RECORDER_PATH)
    )

    print("录屏进行中，等待演示完成...")
    print("请在 Chrome DevTools MCP 中执行演示操作")
    print()

    # 等待录屏完成（会输出进度）
    for line in iter(proc.stdout.readline, b''):
        if line:
            print(f"  [rec] {line.decode('utf-8', errors='replace').rstrip()}")

    print()
    print("=" * 50)
    print("录屏完成!")
    print(f"输出: {OUTPUT_PATH}")
    print("=" * 50)

if __name__ == '__main__':
    main()
