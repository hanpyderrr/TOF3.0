#include "PF32_API.h"
#include "PF_types.h"


//#ifdef _WIN32
//#include "../API/stdafx.h"
//#endif
#include <stdio.h>
#include <iostream>
#include <thread>
#include <fstream>

using namespace std;


//#if defined(__WIN32__) || defined( _MSC_VER )
//#include <windows.h>
//#endif


void getNextFrames_local(string modelNo, string serialNo, PF32_HANDLE pf32, uint16_t * multipleFrames, unsigned int noOfFrames, bool buffered, bool performInitialPurge)
{
   cerr << "Reading " << modelNo << " " << serialNo << endl;
   getNextFrames(pf32, reinterpret_cast<uint8_t*>(multipleFrames), noOfFrames, buffered, performInitialPurge);
   cerr << "Finished " << modelNo << " " << serialNo << endl;
}



pair<string, string> getID(PF32_HANDLE pf32)
{
   char serialNo[MAX_SERIAL_NUMBER_LENGTH];
   char modelNo[MAX_MODEL_NUMBER_LENGTH];

   getSerialNumber(pf32, serialNo);
   getModelNumber(pf32, modelNo);
   return make_pair(string(modelNo), string(serialNo));
}



int main(int argc, char *argv[])
{
   setLogStreamLevel(1);
   cout << "Log file level is: " << getLogFileLevel() << endl;


   PF32_HANDLE pf32_a = PF32_construct();
   PF32_HANDLE pf32_b = PF32_construct();

   // To demonstrate that they are separate cameras.
   setExposure_us(pf32_a, 10);
   setExposure_us(pf32_b, 12);

   cerr << "A) Current link status: " << getLinkStatus(pf32_a) << endl;
   cerr << "B) Current link status: " << getLinkStatus(pf32_b) << endl;


   pair<string, string> id_a = getID(pf32_a);
   pair<string, string> id_b = getID(pf32_b);


   // 32 width * 32 height
   unsigned int noOfPixels = getNoOfPixels(pf32_a);

   // How many frames can be copied over USB in a single packet.
   // Let's ask for ten packet's worth of data
   unsigned int noOfFrames = getNoOfFramesInBuffer(pf32_a) * 10;

   bool buffered = false;
   bool performInitialPurge = true;

   unsigned int bulkSize = noOfPixels * noOfFrames;

   uint16_t * multipleFrames_a = new uint16_t[bulkSize];
   uint16_t * multipleFrames_b = new uint16_t[bulkSize];

   thread thread_a
   (
      getNextFrames_local, id_a.first, id_a.second, pf32_a, multipleFrames_a, noOfFrames, buffered, performInitialPurge
   );

   thread thread_b
   (
      getNextFrames_local, id_b.first, id_b.second, pf32_b, multipleFrames_b, noOfFrames, buffered, performInitialPurge
   );


   thread_a.join();
   thread_b.join();

   cerr << "Finished with object, closing" << endl;

   PF32_destruct(pf32_a);
   PF32_destruct(pf32_b);
   delete [] multipleFrames_a;
   delete [] multipleFrames_b;
   cerr << "Exiting" << endl;
}
