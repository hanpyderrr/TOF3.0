#include <iostream>

//#include "../../PF32/PF32_API.h"
//#include "../../PF32/PF_types.h"


#include "PF32_API.h"
#include "PF_types.h"
#include "PF32_CORRELATOR_API.h"


//#ifdef _WIN32
//#include "../API/stdafx.h"
//#endif
#include <stdio.h>
#include <iostream>
#include <iomanip>
#include <fstream>

using namespace std;


#if defined(__WIN32__) || defined( _MSC_VER )
#include <windows.h>
#endif



int main(int argc, char *argv[])
{
   setLogStreamLevel(1);
   cout << "Log file level is: " << getLogFileLevel() << endl;

   PF32_HANDLE pf32 = PF32_construct();


   std::string firmware = "../../../../../../../../../branches/PF32_USB3_XEM6310_correlation_s6/Xilinx/Builds/PF32_USB3[2132_corr_v0.51].bit";
   PF32_conn_status status = loadCustomFirmware(pf32, firmware.c_str());
   if(status != PF32_conn_status::ready)
   {
      cerr << "main: Error loading custom firmware file in local directory:" << firmware.c_str()
           << " Status=" << status;
      closeAll();
   }



   setMode(pf32, test_data_2);

   setFramesToSum(pf32, 1);
   setExposure_us(pf32, 1.6); // Exposure time 7us

   unsigned long int noOfTintFrames = 18;
   setTintFrames(pf32, noOfTintFrames);

   bool testMode = false;
   enableCorrelator(pf32, true, testMode);

   uint8_t * raw = new uint8_t[getSizeOfCorrelatorData(pf32)];
   uint8_t * footer = new uint8_t[NO_OF_BYTES_CORRELATOR_FOOTER];
   uint8_t * intensityMap = new uint8_t[NO_OF_BYTES_CORRELATOR_INTENSITY_MAP];

   bool readSuccessful = readFromCorrelator(pf32, raw, footer, intensityMap);

   unsigned int noOfTauValuesPerPixel = getNoOfTauValuesPerPixel(pf32);
   unsigned int enabledHeight = getEnabledHeight(pf32);
   unsigned int width = getWidth(pf32);
   double * converted = new double[enabledHeight * width * noOfTauValuesPerPixel];

   convertCorrelatorOutput(pf32, raw, converted, enabledHeight, width);

   cout << fixed << showpoint << setprecision(14);

   double * c =  converted;
   for(unsigned int row = 0; row < enabledHeight; ++row)
   {
      for(unsigned int tau = 0; tau < noOfTauValuesPerPixel; ++tau)
      {
         cout << "\nRow=" << row << " Tau=" <<  tau << endl; 
         for(unsigned int col = 0; col < width; ++col)
         {
            cout << "\nCol=" << col <<  " " << *(c++); 
         }
         cout << endl; 
      }
   }

   cout << "\nChecking footer" << endl;

   uint32_t * footerValues = reinterpret_cast<uint32_t*>(footer);

   cout << "Footer[0]=FrameId=" << *footerValues << endl;
   cout << "Footer[1]=MarkerChannel=" << *(footerValues+1) << endl;
   cout << "Footer[2]=" << *(footerValues+2) << " Correct=" << (*(footerValues+2) == 0xAAAAAAAA) << endl;
   cout << "Footer[3]=" << *(footerValues+3) << " Correct=" << (*(footerValues+3) == 0x55555555) << endl;


   cout << "Cleaning up." << endl;

   enableCorrelator(pf32, false, false);
   PF32_destruct(pf32);
   delete [] raw;
   delete [] converted;
   cout << "Exiting" << endl;
}
