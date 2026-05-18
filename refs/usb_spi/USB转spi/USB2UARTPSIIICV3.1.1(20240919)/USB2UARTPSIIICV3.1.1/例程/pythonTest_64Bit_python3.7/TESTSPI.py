# -*- coding: cp936 -*-
import ctypes
import os
import time
#import numpy
from ctypes import *            
from ctypes import create_string_buffer
from ctypes import c_buffer
from ctypes import sizeof

#import pandas

#AbsPath  = os.path.abspath(os.path.dirname(__file__))
Dir_USB2UARTSPIIICDLL = "./USB2UARTSPIIICDLL.dll"

print(Dir_USB2UARTSPIIICDLL)
#导入动态链接库
#64位
SpiDriver_dll_Usb = ctypes.CDLL(Dir_USB2UARTSPIIICDLL)
#32位
#SpiDriver_dll_Usb = ctypes.windll.LoadLibrary(Dir_USB2UARTSPIIICDLL) 

#打开端口
Is_Open  = SpiDriver_dll_Usb.OpenUsb(ctypes.c_int(0))
print(Is_Open)

#配置参数
Is_True = SpiDriver_dll_Usb.ConfigSPIParam(ctypes.c_uint(2),ctypes.c_uint(0),ctypes.c_uint(0),ctypes.c_uint(0))
print(Is_True)

#发送数据
Create_SendBuffer = (c_char * 9)()
Create_SendBuffer = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08"
#print(Create_SendBuffer)


Is_Convey = SpiDriver_dll_Usb.SPISendData(ctypes.c_uint(0),ctypes.c_uint(1),Create_SendBuffer,\
                                                ctypes.c_int(9),ctypes.c_int(0))
print(Is_Convey)

time.sleep(1)

#接收数据
Create_RevBuffer = b"\x00\x00\x00\x00\x00\x00\x00\x00"
Is_Recieve = SpiDriver_dll_Usb.SPIRcvData(ctypes.c_uint(0),ctypes.c_uint(1),Create_RevBuffer,ctypes.c_int(8),ctypes.c_int(0))
print(Is_Recieve)

for i in range(0,8):
    print('%#x'%Create_RevBuffer[i])
    
SpiDriver_dll_Usb.CloseUsb(ctypes.c_uint(0))
#os.system("pause") 



