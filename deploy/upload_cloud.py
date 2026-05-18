import paramiko, os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=10)
sftp = client.open_sftp()

# Create directories
for cmd in ['mkdir -p ~/TOF3.0/cloud/server', 'mkdir -p ~/tof-data/depth_queue']:
    _, stdout, stderr = client.exec_command(cmd)
    stdout.read(); stderr.read()

# Upload cloud server files
src = r'E:\vs-workspace\TOF3.0\cloud'
files = [
    (r'server\main.py', 'cloud/server/main.py'),
    (r'server\models.py', 'cloud/server/models.py'),
    (r'requirements.txt', 'cloud/requirements.txt'),
]
for local_rel, remote_rel in files:
    local = os.path.join(src, local_rel)
    remote = f'/home/ding/TOF3.0/{remote_rel}'
    sftp.put(local, remote)
    print(f'Uploaded: {remote_rel}')

sftp.close()

# Install Python deps
print("Installing Python deps...")
_, stdout, stderr = client.exec_command(
    'pip3 install --quiet fastapi uvicorn aiosqlite 2>&1'
)
out = stdout.read().decode()
err = stderr.read().decode()
print(out[-500:] if len(out) > 500 else out)
if err.strip():
    print("stderr:", err[-300:])

client.close()
print("Done.")
