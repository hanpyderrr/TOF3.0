#include <iostream>

//#include "../../PF32/PF32_API.h"
//#include "../../PF32/PF_types.h"


#include "PF32_API.h"
#include "PF_types.h"


//#ifdef _WIN32
//#include "../API/stdafx.h"
//#endif
#include <stdio.h>
#include <iostream>
#include <fstream>

using namespace std;


#if defined(__WIN32__) || defined( _MSC_VER )
#include <windows.h>
#endif

void sleepMsec(unsigned long aMsecs)
{
#if defined (__WIN32__) || defined (_MSC_VER)
   Sleep(aMsecs);
#else
   struct timespec time;
   time.tv_sec = aMsecs / 1000;
   time.tv_nsec = (aMsecs % 1000) * (1000 * 1000);
   nanosleep(&time, NULL);
#endif
}





int main(int argc, char *argv[])
{
   setLogStreamLevel(1);
   cout << "Log file level is: " << getLogFileLevel() << endl;

   PF32_HANDLE pf32 = PF32_construct();

   std::string firmware = "../../Firmware/PF32_USB3[1319].bit"; // Local directory
   PF32_conn_status status = loadCustomFirmware(pf32, firmware.c_str());
   if (status != PF32_conn_status::ready)
   {
      cerr << "main: Error loading custom firmware file in local directory:" << firmware.c_str()
           << " Status=" << status;
      closeAll();
      return -1;
    }


   setFramesToSum(pf32, 1); // Needed for cooled camera. Gets set to 10 by default for photon counting mode

   double actualTemp = getActualTemp(pf32);
   cerr << "Current temperature before cooling is enabled: " << actualTemp << endl;


   setEnableCooling(pf32, true);

   const double targetTemp = 233;

   setTargetTemp(pf32, targetTemp);

   double previousTemp = 0;
   while((actualTemp = getActualTemp(pf32)) > targetTemp)
   {
      sleepMsec(2000);
      cerr << actualTemp << "...";
      if(actualTemp == previousTemp)
      {
         break;
      }
      else
      {
         previousTemp = actualTemp;
      }
   }
 




   cout << "Current link status: " << getLinkStatus(pf32) << endl;

   setExposure_us(pf32, 40);

   // 32 width * 32 height
   unsigned int noOfPixels = getNoOfPixels(pf32);

   cout << "Bulk read:" << endl; 

   bool buffered = false;
   bool performInitialPurge = true;
   unsigned int noOfFrames = getNoOfFramesInBuffer(pf32) * 10; 

   unsigned int bulkSize = noOfPixels * noOfFrames;
   uint16_t * multipleFrames = new uint16_t[bulkSize];
   getNextFrames(pf32, reinterpret_cast<uint8_t*>(multipleFrames), noOfFrames, buffered, performInitialPurge);


   string rawFileName = "raw.dat";
   ofstream rawFile(rawFileName.c_str());

   uint16_t * data = multipleFrames;
   for(unsigned int f = 0; f < noOfFrames; ++f, ++data)
   {
      rawFile << "Frame=" << f << endl;
      for(unsigned int p = 0; p < noOfPixels; ++p)
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
   double noOfSeconds = 60.0;
   getHistogram_short(pf32, histogram, noOfSeconds);



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
