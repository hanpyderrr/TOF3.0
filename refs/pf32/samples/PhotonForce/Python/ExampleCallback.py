#!/usr/bin/env python
import ctypes
from PF_API import PF_API
import array
import struct
import platform


def logCallback(verboseLevel, section, sectionLength, msg, msgLength):

    section_msg = []
    for x in range(0, sectionLength):
        asInt = section[x]
        asByte = struct.pack("B", asInt)
        section_msg.append(asByte.decode("utf-8"))

    s = (''.join(section_msg))

    message = []
    for x in range(0, msgLength):
        asInt = msg[x]
        asByte = struct.pack("B", asInt)
        message.append(asByte.decode("utf-8"))

    m = (''.join(message))
    print("Python: [" + s + "] " + m)



def statusCallback(status):
    print("Camera status has changed")



def main():

    sys_name = platform.system();

    if sys_name == 'Windows':
        path_to_library = 'C:\\Program Files\\Photon Force\\PF32_API\\Win_x64\\';
    elif sys_name == 'Linux':
        path_to_library = './'
    else:
        print('Error: Unsupported platform (assuming Linux)')
        path_to_library = './'


    camera = PF_API(path_to_library)

    lcb = camera.createLogCallback(logCallback)
    camera.setLogCallback(lcb)

    scb = camera.createStatusCallback(statusCallback)
    camera.setStatusCallback(scb)


    camera.setExposure_us(ctypes.c_double(40)) # Bug with ctypes if you just pass in 40

    camera.PF_destruct()


if __name__ == '__main__':
        main()
