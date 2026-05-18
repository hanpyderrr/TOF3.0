package JavaTest1;

//import com.sun.jna.Native;

//import com.sun.jna.win32.StdCallLibrary;

import com.sun.jna.Library;  
import com.sun.jna.Native;

public class MainClass1 {
	
	static {
        String filePath = "D:\\JAVASE_workspace\\JavaTest\\"; // 这里是你的动态库所在文件夹的绝对路径
        // 这里引用动态库和他的依赖
        //System.load(filePath + "mfc100.dll");   
        System.load(filePath + "USB2UARTSPIIICDLL.dll");        
    }
	

	public static void main(String[] args) {
		int usbIndex = 0;
		byte[] sendBuf = new byte[5];
		sendBuf[0] = 'a';
		sendBuf[1] = 'b';
		sendBuf[2] = 'c';
		sendBuf[3] = 'd';
		sendBuf[4] = 'e';
		System.out.printf("OpenUsb\r\n");
		USB2UARTSPIIICDll.INSTANCE.OpenUsb(usbIndex);
		System.out.printf("ConfigSPIParam\r\n");
		USB2UARTSPIIICDll.INSTANCE.ConfigSPIParam(0,0,0,usbIndex);
		System.out.printf("SPISendData\r\n");
		USB2UARTSPIIICDll.INSTANCE.SPISendData(0,1,sendBuf,5,usbIndex);
		USB2UARTSPIIICDll.INSTANCE.CloseUsb(usbIndex);
		System.out.printf("CloseUsb\r\n");
	}

	
	// 这里是最关键的地方
    public interface USB2UARTSPIIICDll extends Library {
        // FS_CheckCode是动态库名称，前面的d://test//是路径
    	USB2UARTSPIIICDll INSTANCE = (USB2UARTSPIIICDll) Native.loadLibrary("USB2UARTSPIIICDLL.dll", USB2UARTSPIIICDll.class);
 
        // 我们要调用的动态库里面的方法。
    	int OpenUsb(int UsbIndex);
    	int CloseUsb(int UsbIndex);
    	int ConfigSPIParam(int rate,int fistBit,int subMode,int UsbIndex);
    	int SPISendData(int startCS,int endCS,byte[] sendBuf,int len,int UsbIndex);
    }
}
