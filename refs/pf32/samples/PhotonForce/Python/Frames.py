#!/usr/bin/env python
import ctypes
from PF_API import PF_API
import array
from io import StringIO
import platform

def main():

    write_to_file = False;

    sys_name = platform.system();

    if sys_name == 'Windows':
        path_to_library = 'C:\\Program Files\\Photon Force\\PF32_API\\Win_x64\\';
    elif sys_name == 'Linux':
        path_to_library = './'
    else:
        print('Error: Unsupported platform (assuming Linux)')
        path_to_library = './'

    camera = PF_API(path_to_library)

    camera.setLogStreamLevel(PF_API.LOGLEVEL_TRACE)

    modelNo = ctypes.create_string_buffer(PF_API.MAX_MODEL_NUMBER_LENGTH+1)
    camera.getModelNumber(modelNo);
    print("\nModelNo=" + str(modelNo, 'UTF-8'));

    serialNo = ctypes.create_string_buffer(PF_API.MAX_SERIAL_NUMBER_LENGTH+1)
    camera.getSerialNumber(serialNo);
    print("SerialNo=" + str(serialNo, 'UTF-8'));

    camera.setMode(PF_API.MODE_TCSPC_LASER_MASTER);
    camera.setExposure_us(ctypes.c_double(40)) # Bug with ctypes if you just pass in 40


    no_of_pixels = camera.getNoOfPixels()
    no_of_frames = 2;
    buffered = False
    perform_initial_purge = True
    bulk_size = no_of_pixels * no_of_frames
    multiple_frames = (ctypes.c_uint16 * bulk_size)()


    print("Reading raw data")
    camera.getNextFrames_short(multiple_frames, no_of_frames, buffered, perform_initial_purge)

    if write_to_file:
        raw_data = open("frames.dat", "w")
    
        for f in range(0, no_of_frames):
            raw_data.write("Frame " + str(f) + "\n")
            for p in range(0, no_of_pixels):
                raw_data.write(str(multiple_frames[(f * no_of_pixels) + p]) + " ")
            raw_data.write("\n")
        raw_data.write("\n")

        raw_data.close()
    else:

        raw_data_str = StringIO()
        for f in range(0, no_of_frames):
            raw_data_str.write("Frame " + str(f) + "\n")
            for p in range(0, no_of_pixels):
                raw_data_str.write(str(multiple_frames[(f * no_of_pixels) + p]) + " ")
            raw_data_str.write("\n")
        raw_data_str.write("\n")

        print(raw_data_str.getvalue())



    camera.PF_destruct()



if __name__ == '__main__':
        main()
