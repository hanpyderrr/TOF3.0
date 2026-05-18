import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=10)

_, stdout, _ = client.exec_command('ps aux | grep -E "uvicorn|sim_pf32|tof_viewer" | grep -v grep')
print("Processes:", stdout.read().decode().strip())

_, stdout, _ = client.exec_command('python3 -c "import urllib.request; print(urllib.request.urlopen(\'http://localhost:8765/api/health\').read().decode())" 2>&1')
print("Health:", stdout.read().decode().strip())

_, stdout, _ = client.exec_command('cat /tmp/fastapi.log 2>&1 | tail -5')
print("FastAPI log:", stdout.read().decode().strip())

client.close()
