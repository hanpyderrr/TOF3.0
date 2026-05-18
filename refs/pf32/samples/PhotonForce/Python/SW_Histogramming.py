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

    no_of_pixels = camera.getNoOfPixels()

    print("Reading histogram data")

    camera.setMode(PF_API.MODE_TCSPC_LASER_MASTER);
    camera.setExposure_us(ctypes.c_double(40)) # Bug with ctypes if you just pass in 40

    no_of_TDC_codes = camera.getNoOfTDCCodes()
    size_of_histogram = no_of_TDC_codes * no_of_pixels;
    histogram = (ctypes.c_uint16 * size_of_histogram)()
    no_of_seconds =  ctypes.c_double(5)

    camera.getHistogram_short(histogram, no_of_seconds)


    histogram_data_str = StringIO()

    for p in range(0, no_of_pixels):
        histogram_data_str.write("Pixel " + str(p) + "\n")
        for t in range(0, no_of_TDC_codes):
            histogram_data_str.write(str(histogram[(p * no_of_TDC_codes) + t]) + " ")
        histogram_data_str.write("\n")
    histogram_data_str.write("\n")

    if write_to_file:
        histogram_data = open("swHistogram.dat", "w");
        histogram_data.write(histogram_data_str.getvalue())
        histogram_data.close()
    else:
        print(histogram_data_str.getvalue())

    camera.PF_destruct()

 


if __name__ == '__main__':
        main()
