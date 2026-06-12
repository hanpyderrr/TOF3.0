#!/usr/bin/env python3
"""
用 1.5.25 Python SDK 测试 sys_master 模式 TRIG 输出。
运行后接示波器到 PF32 TRIG SMA，观察是否有波形。
"""
import sys
import os
import time
import ctypes

SDK_PY  = '/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/Python'
SDK_LIB = '/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/lib/Linux_x64'
FW_DIR  = '/home/ding/Firmware'   # PF32_USB3.bit 所在目录（symlink）

sys.path.insert(0, SDK_PY)
os.environ['LD_LIBRARY_PATH'] = SDK_LIB + ':' + os.environ.get('LD_LIBRARY_PATH', '')

# 必须在修改 LD_LIBRARY_PATH 后再 import（ctypes.cdll.LoadLibrary 用运行时路径）
from PF32_Factory import PF32_Factory

factory = PF32_Factory(path_to_library=SDK_LIB + '/')
factory.setLogStreamLevel(3)   # INFO 级别

print(f'SDK version: {factory.getVersionMajor()}.{factory.getVersionMinor()}.{factory.getVersionPatch()}')

cam = factory.PF_construct()
print(f'Link status: {cam.getLinkStatus()}  (2=ready)')
print(f'Model: {cam.getModelNumber()}  Serial: {cam.getSerialNumber()}')
print(f'Size: {cam.getWidth()}x{cam.getHeight()}  TDC bins: {cam.getNoOfTDCCodes()}')

# 设置 sys_master 模式
cam.setDataSource(cam.DATA_SOURCE_SENSOR)
cam.setSPADEnable(True)
cam.setMode(cam.MODE_TCSPC_SYS_MASTER)
cam.setEXTSTOPEnable(True)
cam.setExposure_us(200.0)

print(f'\nMode set to TCSPC_SYS_MASTER')
print(f'EXTSTOP enabled: {cam.getEXTSTOPEnable()}')
print(f'Exposure: {cam.getExposure_us()} us')
print(f'Sync Hz (SYNC input): {cam.getSync_Hz()}')
print()
print('>>> 现在接示波器到 PF32 TRIG SMA，等待 5 秒...')
time.sleep(2)

# 积累一帧（0.5s）—— 这段时间 TRIG 应该持续输出脉冲
print('开始采集（0.5s）...')
t0 = time.time()
hist = cam.getHistogram(0.5)
dt = time.time() - t0
print(f'采集完成，耗时 {dt:.2f}s')
print(f'Sync Hz after acquisition: {cam.getSync_Hz()}')

# 再等几秒，方便示波器观察
print('再等 5 秒，观察 TRIG 波形...')
time.sleep(5)

factory.PF_destruct(cam)
print('完成，PF32 已释放')
