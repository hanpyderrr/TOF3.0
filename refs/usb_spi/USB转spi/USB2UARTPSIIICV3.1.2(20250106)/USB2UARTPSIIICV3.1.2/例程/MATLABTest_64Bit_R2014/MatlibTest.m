[notfound,warnings] = loadlibrary('USB2UARTSPIIICDLL','USB2UARTSPIIICDLL.h'); %加载.dll库
usbIndex = 0;
calllib('USB2UARTSPIIICDLL','OpenUsb',usbIndex);
if(ans >= 0)
  fprintf('USB opened successfully!\n');  
else
  fprintf('Failed to open USB!\n');  
end

fprintf('SPISendData!\n'); 
calllib('USB2UARTSPIIICDLL','ConfigSPIParam',0,0,0,usbIndex);       %设置SPI参数
sendBuf = [1,2,3,4,5];
calllib('USB2UARTSPIIICDLL','SPISendData',0,1,sendBuf,5,usbIndex);       %发送5个字节
if(ans >= 0)
  fprintf('SPISendData successfully!\n');  
else
  fprintf('SPISendData failed!\n');  
end

calllib('USB2UARTSPIIICDLL','CloseUsb',usbIndex);
fprintf('CloseUsb!\n'); 
unloadlibrary USB2UARTSPIIICDLL;    %卸载dll
