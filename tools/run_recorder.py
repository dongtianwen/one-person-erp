import subprocess, sys, os, time

recorder = os.path.join(os.path.dirname(__file__), 'screen_recorder.py')
output = os.path.join(os.path.dirname(__file__), 'demo_output.avi')
output = os.path.normpath(output)

with open(recorder, encoding='utf-8') as f:
    src = f.read()
src = src.replace("out = 'd:/one-person-erp/demo.avi'", f"out = r'{output}'")
src = src.replace('for i in range(100):', 'for i in range(200):')
tmp = os.path.join(os.path.dirname(__file__), 'screen_recorder_tmp.py')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(src)

print(f'Output: {output}', flush=True)
print('Recording 20 seconds...', flush=True)
p = subprocess.Popen([sys.executable, tmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
for line in p.stdout:
    try:
        print(line.decode('utf-8', errors='replace').rstrip(), flush=True)
    except Exception as e:
        print(f'err: {e}', flush=True)
print('Done', flush=True)
