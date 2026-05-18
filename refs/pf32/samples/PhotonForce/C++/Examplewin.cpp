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
   setLogStreamLevel(1);
   cout << "Log file level is: " << getLogFileLevel() << endl;

   PF32_HANDLE pf32 = PF32_construct();

   cout << "Current link status: " << getLinkStatus(pf32) << endl;

   setExposure_us(pf32, 40);

   // 32 width * 32 height
   unsigned int noOfPixels = getNoOfPixels(pf32);

   cout << "Bulk read:" << endl; 

   bool buffered = false;
   bool performInitialPurge = true;
   unsigned int noOfFrames = getNoOfFramesInBuffer(pf32); 

   unsigned int bulkSize = noOfPixels * noOfFrames;
   uint16_t * multipleFrames = new uint16_t[bulkSize];
   getNextFrames(pf32, reinterpret_cast<uint8_t*>(multipleFrames), noOfFrames, buffered, performInitialPurge);


   string rawFileName = "raw.dat";
   ofstream rawFile(rawFileName.c_str());

   uint16_t * data = multipleFrames;
   for(unsigned int f = 0; f < noOfFrames; ++f)
   {
      rawFile << "Frame=" << f << endl;
      for(unsigned int p = 0; p < noOfPixels; ++p, ++data)
      {
         rawFile << (*data) << " ";
      }
      rawFile << endl;
   }
   rawFile << endl;
   rawFile.close();




   cout << "Capturing histogram:" << endl; 

   setMode(pf32, TCSPC_sys_master);
   unsigned int noOfTDCCodes = getNoOfTDCCodes(pf32);
   unsigned int sizeOfHistogram = noOfTDCCodes * noOfPixels;
   uint16_t * histogram = new uint16_t[sizeOfHistogram];
   double noOfSeconds = 10.0;
   getHistogram(pf32, histogram, noOfSeconds);



   string histogramFileName = "histogram.dat";
   ofstream histogramFile(histogramFileName.c_str());

   data = histogram;
   for(unsigned int p = 0; p < noOfPixels; ++p)
   {
      rawFile << "Pixel=" << p << endl;
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
   delete [] multipleFrames;
   delete [] histogram;
   cout << "Exiting" << endl;
}
