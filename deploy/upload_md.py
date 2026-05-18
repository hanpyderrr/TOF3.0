import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=10)
sftp = client.open_sftp()
sftp.put(r'E:\vs-workspace\TOF单光子2.0\CLAUDE.md', '/home/ding/TOF2.0/CLAUDE.md')
print('CLAUDE.md uploaded.')
sftp.close()
client.close()
