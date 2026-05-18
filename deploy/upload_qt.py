import paramiko

files = [
    'datarecorder.h', 'datarecorder.cpp',
    'cloudsyncer.h', 'cloudsyncer.cpp',
    'mainwindow.h', 'mainwindow.cpp',
    'main.cpp', 'tof_viewer.pro'
]
src = r'E:\vs-workspace\TOF单光子2.0\qt_app'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.31.79', username='ding', password='1234', timeout=10)
sftp = client.open_sftp()
for f in files:
    local = fr'{src}\{f}'
    remote = f'/home/ding/TOF2.0/qt_app/{f}'
    sftp.put(local, remote)
    print(f'Uploaded: {f}')
sftp.close()
client.close()
print('All files uploaded.')
