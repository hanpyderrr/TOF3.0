import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=10)

# Check Qt SQL dev package
_, stdout, _ = client.exec_command('dpkg -l libqt5sql5-sqlite libqt5sql5 2>/dev/null | grep "^ii"')
print("Qt SQL packages:", stdout.read().decode().strip() or "(none found)")

_, stdout, _ = client.exec_command('dpkg -l libqt5network5 2>/dev/null | grep "^ii"')
print("Qt Network packages:", stdout.read().decode().strip() or "(none found)")

# Build
_, stdout, stderr = client.exec_command(
    'cd ~/TOF3.0/nezha/qt_app && qmake tof_viewer.pro 2>&1 && make -j4 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()

print("=== BUILD OUTPUT ===")
print(out[-5000:] if len(out) > 5000 else out)
if err.strip():
    print("=== STDERR ===")
    print(err[-2000:] if len(err) > 2000 else err)

client.close()
