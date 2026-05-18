import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=30)

def run(cmd, wait=True):
    _, stdout, stderr = client.exec_command(cmd)
    if wait:
        return (stdout.read() + stderr.read()).decode().strip()
    return ""

# Kill existing processes
print("Killing old processes...")
run('pkill -f "uvicorn main:app" 2>/dev/null || true')
run('pkill -f "tof_viewer" 2>/dev/null || true')
run('pkill -f "sim_pf32" 2>/dev/null || true')
time.sleep(2)

# Start FastAPI from correct directory
print("Starting FastAPI server from ~/TOF2.0/cloud/server/ ...")
run(
    'cd ~/TOF2.0/cloud/server && '
    'nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 '
    '> /tmp/fastapi.log 2>&1 &'
)
time.sleep(4)

# Verify server is up
out = run('python3 -c "import urllib.request; r=urllib.request.urlopen(\'http://localhost:8765/api/health\'); print(r.read().decode())"')
print(f"Health check: {out}")

# Check log
out = run('tail -5 /tmp/fastapi.log 2>&1')
print(f"FastAPI log:\n{out}")

# Start sim_pf32
print("\nStarting sim_pf32...")
run('nohup ~/TOF2.0/acquisition/sim_pf32 > /tmp/sim_pf32.log 2>&1 &')
time.sleep(3)
out = run('ls -lh /tmp/depth.dat 2>&1')
print(f"depth.dat: {out}")

# Start tof_viewer with all args
print("\nStarting tof_viewer...")
run(
    'mkdir -p ~/tof-data/depth_queue && '
    'DISPLAY=:1 nohup ~/TOF2.0/qt_app/tof_viewer '
    '--depth-file /tmp/depth.dat '
    '--data-dir ~/tof-data/depth_queue '
    '--cloud-url http://localhost:8765 '
    '> /tmp/tof_viewer.log 2>&1 &'
)
time.sleep(5)

out = run('cat /tmp/tof_viewer.log 2>&1')
print(f"tof_viewer log:\n{out or '(empty)'}")

print("\n=== Running processes ===")
out = run('ps aux | grep -E "uvicorn|sim_pf32|tof_viewer" | grep -v grep')
print(out)

client.close()
