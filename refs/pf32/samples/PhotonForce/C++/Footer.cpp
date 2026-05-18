#include <iostream>
#include "PF32_API.h"
#include "PF_types.h"
#include <stdio.h>
#include <iostream>
#include <fstream>


using namespace std;

int main(int argc, char *argv[])
{
   setLogStreamLevel(1);
   std::cout << "Log file level is: " << getLogFileLevel() << std::endl;

   PF32_HANDLE pf32 = PF32_construct();
   setEnableFooters(pf32, true);
   
   int ret;
   ret = getEnableFooters (pf32);
   if(ret ==!1)
   {
       cout << "not enable footers,ret =" << ret <<endl;
   }
   else {
       cout <<"success enable footers,ret =" << ret <<endl;
   }
   std::cout << "Current link status: " << getLinkStatus(pf32) << std::endl;

   setExposure_us(pf32, 40);

   unsigned int noOfPixels = getNoOfPixels(pf32);

   std::cout << "Bulk read:" << std::endl; 

   bool buffered = false;
   bool performInitialPurge = true;
   unsigned int noOfFrames = 1024; 

   unsigned int bulkSize = noOfPixels * noOfFrames;
   uint16_t * multipleFrames = new uint16_t[bulkSize];
   getNextFrames(pf32, reinterpret_cast<uint8_t*>(multipleFrames), noOfFrames, buffered, performInitialPurge);

   string rawFileName = "raw.dat";
   std::ofstream rawFile(rawFileName.c_str());

   uint16_t * data = multipleFrames;
   for(unsigned int f = 0; f < noOfFrames; ++f)
   {
      rawFile << "Frame=" << f << std::endl;
      for(unsigned int p = 0; p < noOfPixels; ++p, ++data)
      {
         rawFile << (*data) << " ";
      }
      rawFile << std::endl;
   }

   // Adding the new functionality 
   uint16_t frameData[noOfPixels];
   uint32_t  *positionalData; // Assuming frame count, X, Y, Z coordinates
   
   uint16_t * datanew = multipleFrames;
   iteratePositionalData_short(pf32, datanew, 0, frameData, positionalData, 2); 
   //std::ofstream newDataFile("new.dat");
   string newFileName = "new.dat";
   ofstream newFile(newFileName.c_str());
   
   for(unsigned int f = 0; f < noOfFrames; ++f)
   {
      newFile << "Frame=" << f << std::endl;
      for(unsigned int p = 0; p < noOfPixels; ++p, ++data)
      {
         newFile << (*datanew) << " ";
      }
      newFile << std::endl;
      newFile << "footers:" << positionalData << " ";
   }
   
/*    for (unsigned int i = 0; i < noOfPixels; ++i) {
       newFile << frameData[i] << " ";
   }
   newFile << std::endl;
   for (unsigned int i = 0; i < 32; ++i) {
       
   } */
   newFile << std::endl;
   newFile.close();

   rawFile << std::endl;
   rawFile.close();

   std::cout << "Cleaning up." << std::endl;

   PF32_destruct(pf32);
   delete [] multipleFrames;
   
   std::cout << "Exiting" << std::endl;

   return 0;
}
