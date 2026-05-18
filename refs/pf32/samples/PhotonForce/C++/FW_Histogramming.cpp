#include <iostream>


#include "PF32_API.h"
#include "PF_types.h"


//#ifdef _WIN32
//#include "../API/stdafx.h"
//#endif
#include <stdio.h>
#include <iostream>
#include <fstream>

using namespace std;


//#if defined(__WIN32__) || defined( _MSC_VER )
//#include <windows.h>
//#endif

int main(int argc, char *argv[])
{
   string firmwareFile = "PF32_USBC_XEM7310_[6087]_Histogramming.bit";
   PF32_HANDLE pf32 = PF32_constructWithCustomFirmware(firmwareFile.c_str());

   cout << "Capturing histogram:" << endl; 

   setMode(pf32, TCSPC_sys_master);
   setNoOfFramesToHistogram(pf32, 1024);

   unsigned int noOfBytesPerHistogram = getNoOfBytesPerHistogram(pf32, true);
   uint16_t * histograms = new uint16_t[noOfBytesPerHistogram];
   getHistogramFromFirmware(pf32, reinterpret_cast<uint8_t*>(histograms));

   unsigned int noOfTDCCodes = getNoOfTDCCodes(pf32);
   unsigned int noOfEnabledPixels = getEnabledNoOfPixels(pf32);

   string histogramFileName = "fwHistogram.dat";
   ofstream histogramFile(histogramFileName.c_str());

   uint16_t * data = histograms;
   for(unsigned int p = 0; p < noOfEnabledPixels; ++p)
   {
      histogramFile << "Pixel=" << p << endl;
      for(unsigned int t = 0; t < noOfTDCCodes; ++t, ++data)
      {
         histogramFile << (*data) << " "; 
      } 
      histogramFile << endl;
   }
   histogramFile << endl;
   histogramFile.close(); 

   
   cout << "Cleaning up." << endl;

   PF32_destruct(pf32);
   delete [] histograms;
   cout << "Exiting" << endl;
}
