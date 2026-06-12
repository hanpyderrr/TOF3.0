"""
verify_sync.py — 验证 PF32 SYNC 输入是否收到信号

用法：
  SDK="/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/lib/Linux_x64"
  OK="/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/source/OK/Linux_x64"
  LD_LIBRARY_PATH="$SDK:$OK" python3 verify_sync.py

接线：信号发生器 → PF32 SYNC SMA（+3.3V peak，50Ω，SMA 同轴线）
预期：sync_hz 显示信号发生器频率（如 5000）即为成功
"""
import ctypes, os, time, sys

LIB = "/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/lib/Linux_x64"
OK  = "/home/ding/sdks/pf32/PhotonForce_linux-1.5.25/PhotonForce/source/OK/Linux_x64"
os.environ["LD_LIBRARY_PATH"] = LIB + ":" + OK + ":" + os.environ.get("LD_LIBRARY_PATH", "")

lib = ctypes.CDLL(os.path.join(LIB, "libPF32_API.so"))
lib.PF32_construct.restype      = ctypes.c_void_p
lib.PF32_construct.argtypes     = []
lib.PF32_destruct.argtypes      = [ctypes.c_void_p]
lib.getLinkStatus.restype       = ctypes.c_int
lib.getLinkStatus.argtypes      = [ctypes.c_void_p]
lib.setMode.argtypes            = [ctypes.c_void_p, ctypes.c_int]
lib.setDataSource.argtypes      = [ctypes.c_void_p, ctypes.c_int]
lib.setSPADEnable.argtypes      = [ctypes.c_void_p, ctypes.c_bool]
lib.setExposure_us.argtypes     = [ctypes.c_void_p, ctypes.c_double]
lib.getSync_Hz.restype          = ctypes.c_int
lib.getSync_Hz.argtypes         = [ctypes.c_void_p]
lib.getSyncDutyRatio.restype    = ctypes.c_double
lib.getSyncDutyRatio.argtypes   = [ctypes.c_void_p]
lib.setLogStreamLevel.argtypes  = [ctypes.c_int]

lib.setLogStreamLevel(3)  # INFO

print("构造 PF32...")
pf32 = lib.PF32_construct()
assert pf32, "PF32_construct 返回 null"

for _ in range(100):
    if lib.getLinkStatus(pf32) == 2: break
    time.sleep(0.1)
print(f"link_status={lib.getLinkStatus(pf32)}")

print("设置 laser_master 模式...")
lib.setDataSource(pf32, 0)
lib.setSPADEnable(pf32, True)
lib.setMode(pf32, 1)           # TCSPC_laser_master
lib.setExposure_us(pf32, 200.0)

print()
print("每秒读取 SYNC 频率，持续 30 秒（Ctrl+C 退出）")
print("接上信号发生器后 sync_hz 应显示非零频率")
print()

for i in range(30):
    hz    = lib.getSync_Hz(pf32)
    duty  = lib.getSyncDutyRatio(pf32)
    status = "✓ 收到信号" if hz > 0 else "✗ 无信号"
    print(f"  [{i+1:2d}s] sync_hz={hz:6d}  duty={duty:.3f}  {status}")
    time.sleep(1)

lib.PF32_destruct(pf32)
print("完成")
