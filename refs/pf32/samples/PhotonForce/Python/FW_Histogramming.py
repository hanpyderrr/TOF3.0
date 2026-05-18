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

    customFirmwareFile = 'PF32_USBC_XEM7310_[6087]_Histogramming.bit';
    #customFirmwareFile = 'PF32_USBC_XEM7310_[6087]-202403181229.bit'
    camera = PF_API(path_to_library, customFirmwareFile)

    camera.setLogStreamLevel(PF_API.LOGLEVEL_TRACE)

    camera.setMode(PF_API.MODE_TCSPC_LASER_MASTER);
    camera.setExposure_us(ctypes.c_double(40)) # Bug with ctypes if you just pass in 40
    camera.setNoOfFramesToHistogram(100);
    camera.setNoOfBinsInHistogram(0); # 0 means all the bins available which is 1024

    no_of_pixels = camera.getNoOfPixels()

    print("Reading histogram data")

    no_of_bins_in_histogram = camera.getNoOfBinsInHistogram()
    size_of_histogram = no_of_bins_in_histogram * no_of_pixels;
    histogram = (ctypes.c_uint16 * size_of_histogram)()

    camera.getHistogramFromFirmware(histogram)


    histogram_data_str = StringIO()

    for p in range(0, no_of_pixels):
        histogram_data_str.write("Pixel " + str(p) + "\n")
        for t in range(0, no_of_bins_in_histogram):
            histogram_data_str.write(str(histogram[(p * no_of_bins_in_histogram) + t]) + " ")
        histogram_data_str.write("\n")
    histogram_data_str.write("\n")

    if write_to_file:
        histogram_data = open("fwHistogram.dat", "w");
        histogram_data.write(histogram_data_str.getvalue())
        histogram_data.close()
    else:
        print(histogram_data_str.getvalue())

    camera.PF_destruct()

 


if __name__ == '__main__':
        main()
