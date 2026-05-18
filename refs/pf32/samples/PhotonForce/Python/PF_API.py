import ctypes
import platform
import os

class PF_API:

    # Enumerated types from PF_types.h

    LOGLEVEL_TRACE = 1     # Low level execution tracing information.
    LOGLEVEL_DEBUG = 2     # Debugging information
    LOGLEVEL_INFO  = 3     # Status information.
    LOGLEVEL_WARNING  = 4  # Warnings.
    LOGLEVEL_ERROR = 5     # Critical errors.
    LOGLEVEL_OFF   = 6     # Error logging disabled.

    DAC_VBD = 0                                  # Breakdown voltage DAC.
    DAC_VEB = 1                                  # Excess bias voltage DAC.
    DAC_VQ = 2                                   # Quench voltage DAC.
    DAC_VNBL = 3                                 # TDC resolution control voltage DAC.
    DAC_VIO = 4                                  # Cooled camera
    DAC_VTDC_OR_SYNC_THRESHOLD_MV = 5            # Cooled camera or USBC_V2

    STATUS_DISCONNECTED = 0          # No camera connected.
    STATUS_CONNECTED_PRE_INIT = 1    # Camera connected, but not yet initialised.
    STATUS_READY = 2                 # Camera connected, initialised, and ready for operation.
    STATUS_ERROR = 3                 # Cannot continue without human intervention, e.g. invalid firmware path provided. See error log for details.

    DATA_SOURCE_SENSOR = 0           # Real sensor image data.
    DATA_SOURCE_TEST = 1             # Test data for software debugging.

    MODE_PHOTON_COUNTING = 0      # Photon counting mode
    MODE_TCSPC_LASER_MASTER = 1   # Camera in time-resolved mode, configured to accept external laser SYNC input as TDC stop signal.
    MODE_TCSPC_SYS_MASTER = 2     # Camera in time-resolved mode, configured to generate TRIG output and TDC stop signal.
    MODE_RAW_SPAW = 10            # Raw SPAD output mode. One row of pixel SPAD signals are directly connected to each column outputs. Consult manual before using.
    MODE_TEST_PULSE_COUNTING = 11 # Counting electrical test pulses (TESTSTART signal)
    MODE_TEST_DATA_1 = 20         # Readout test pattern 1.
    MODE_TEST_DATA_2 = 21         # Readout test pattern 2. Stats at pixel 00 in the top left, increasing horizontally along the row and then vertically downwards. With each frame, all values increment by 1, wrapping around at 1023.

    MAX_SERIAL_NUMBER_LENGTH = 32
    MAX_MODEL_NUMBER_LENGTH = 32
    NO_OF_BYTES_PER_FOOTER = 16

    LOWEST_OK_ERROR_CODE = -20
    MAX_LOG_LEVEL = LOGLEVEL_OFF;


    library_is_loaded = False;



    def __init__(self, path_to_library = '', customFirmwareFile = None):
     
        if not PF_API.library_is_loaded:
            self.loadLibrary(path_to_library)

        if customFirmwareFile == None:
            self.handle = self.PF_construct()
        else:
            b_customFirmwareFile = customFirmwareFile.encode('utf-8');
            self.handle = self.PF_constructWithCustomFirmware(b_customFirmwareFile)



    
    # There can be a bug with ctypes in that double parameters are not properly converted.
    # e.g.
    # PF_wrapper.setExposure_us(PF_HANDLE, 7)
    # The driver is given the value of 4.65394e-310 instead. So instead do:
    # PF_wrapper.setExposure_us(PF_HANDLE, ctypes.c_double(7))
    #
    # The only other method that accepts double params is:
    # setFramePeriodAndOpticalExposure_us()
    
    def loadLibrary(self, path_to_library):
        PF_API.library_is_loaded = True

        if not path_to_library[-1] == os.sep:
            path_to_library += os.sep

        sys_name = platform.system();
 
        if sys_name == 'Windows':
            self.libPF_API = ctypes.cdll.LoadLibrary(path_to_library + 'PF32_API.dll')
        elif sys_name == 'Linux':
            self.libPF_API = ctypes.cdll.LoadLibrary(path_to_library + 'libPF32_API.so')
        else:
            print('Error: Unsupported platform (assuming Linux)')
            self.libPF_API = ctypes.cdll.LoadLibrary(path_to_library + 'libPF32_API.so')
    
        self.libPF_API.getVersionMajor.restype = ctypes.c_uint
        self.libPF_API.getVersionMinor.restype = ctypes.c_uint
        self.libPF_API.getVersionPatch.restype = ctypes.c_uint
        self.libPF_API.noOfPF32sInstantiated.restype = ctypes.c_int
        self.libPF_API.getPF32InstanceByIndex.restype = ctypes.POINTER(ctypes.c_void_p)
        self.libPF_API.getPF32InstanceByIndex.arg_types = [ctypes.c_int]
        self.libPF_API.createSession.restype = ctypes.POINTER(ctypes.c_void_p)
        self.libPF_API.addCamera.arg_types = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint]
        self.libPF_API.addCamera_short.arg_types = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_uint]
        self.libPF_API.executeSession.arg_types = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool]
        self.libPF_API.destroySession.arg_types = [ctypes.c_void_p]
        self.libPF_API.getLogFileLevel.restype = ctypes.c_int
        self.libPF_API.setLogFileLevel.arg_types = [ctypes.c_int]
        self.libPF_API.getLogStreamLevel.restype = ctypes.c_int
        self.libPF_API.setLogStreamLevel.arg_types = [ctypes.c_int]
        self.libPF_API.PF32_construct.restype = ctypes.POINTER(ctypes.c_void_p)
        self.libPF_API.PF32_constructWithCustomFirmware.restype = ctypes.POINTER(ctypes.c_void_p)
        self.libPF_API.PF32_constructWithCustomFirmware.arg_types = [ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.PF32_destruct.arg_types = [ctypes.c_void_p]
        self.libPF_API.loadCustomFirmware.restype = ctypes.c_uint
        self.libPF_API.loadCustomFirmware.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.getWidth.restype = ctypes.c_uint
        self.libPF_API.getWidth.arg_types = [ctypes.c_void_p]
        self.libPF_API.getHeight.restype = ctypes.c_uint
        self.libPF_API.getHeight.arg_types = [ctypes.c_void_p]
        self.libPF_API.getNoOfPixels.restype = ctypes.c_uint
        self.libPF_API.getNoOfPixels.arg_types = [ctypes.c_void_p]
        self.libPF_API.getEnabledNoOfPixels.restype = ctypes.c_uint
        self.libPF_API.getEnabledNoOfPixels.arg_types = [ctypes.c_void_p]
        self.libPF_API.getEnabledHeight.restype = ctypes.c_uint
        self.libPF_API.getEnabledHeight.arg_types = [ctypes.c_void_p]
        self.libPF_API.getNoOfTDCCodes.restype = ctypes.c_uint
        self.libPF_API.getNoOfTDCCodes.arg_types = [ctypes.c_void_p]
        self.libPF_API.getLinkStatus.restype = ctypes.c_uint
        self.libPF_API.getLinkStatus.arg_types = [ctypes.c_void_p]
        self.libPF_API.setMode.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.setI2C.restype = ctypes.c_bool
        self.libPF_API.setI2C.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.libPF_API.getI2C.restype = ctypes.c_bool
        self.libPF_API.getI2C.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
        self.libPF_API.applyDACDefaultValues.arg_types = [ctypes.c_void_p]
        self.libPF_API.setDAC.restype = ctypes.c_bool
        self.libPF_API.setDAC.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.libPF_API.getDAC.restype = ctypes.c_int
        self.libPF_API.getDAC.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getMaxValueOfDAC.restype = ctypes.c_int
        self.libPF_API.getMaxValueOfDAC.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getNextFrames.restype = ctypes.c_bool
        self.libPF_API.getNextFrames.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint, ctypes.c_bool, ctypes.c_bool]
        self.libPF_API.getNextFrames_short.restype = ctypes.c_bool
        self.libPF_API.getNextFrames_short.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_uint, ctypes.c_bool, ctypes.c_bool]
        self.libPF_API.getHistogram.restype = ctypes.c_bool
        self.libPF_API.getHistogram.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_double]
        self.libPF_API.getHistogram_short.restype = ctypes.c_bool
        self.libPF_API.getHistogram_short.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_double]
        self.libPF_API.getHistogram_char.restype = ctypes.c_bool
        self.libPF_API.getHistogram_char.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_double]
        self.libPF_API.getNoOfFramesToHistogram.restype = ctypes.c_uint
        self.libPF_API.getNoOfFramesToHistogram.arg_types = [ctypes.c_void_p]
        self.libPF_API.setNoOfFramesToHistogram.arg_types = [ctypes.c_void_p, ctypes.c_uint]
        self.libPF_API.setNoOfBinsInHistogram.arg_types = [ctypes.c_void_p, ctypes.c_uint]
        self.libPF_API.getNoOfBinsInHistogram.restype = ctypes.c_uint
        self.libPF_API.getNoOfBinsInHistogram.arg_types = [ctypes.c_void_p]
        self.libPF_API.getHistogramFromFirmware.restype = ctypes.c_bool
        self.libPF_API.getHistogramFromFirmware.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8)]
        self.libPF_API.getNoOfFramesInBuffer.restype = ctypes.c_uint
        self.libPF_API.getNoOfFramesInBuffer.arg_types = [ctypes.c_void_p]
        self.libPF_API.setNoOfFramesInBuffer.arg_types = [ctypes.c_void_p, ctypes.c_uint]
        self.libPF_API.getMultipleOfBuffer.restype = ctypes.c_uint
        self.libPF_API.getMultipleOfBuffer.arg_types = [ctypes.c_void_p]
        self.libPF_API.setMultipleOfBuffer.arg_types = [ctypes.c_void_p, ctypes.c_uint]
        self.libPF_API.getModelNumber.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.getSerialNumber.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.purgeBulkFrameBuffer.arg_types = [ctypes.c_void_p]
        self.libPF_API.getBitMode.restype = ctypes.c_uint
        self.libPF_API.getBitMode.arg_types = [ctypes.c_void_p]
        self.libPF_API.getSPADEnable.restype = ctypes.c_bool
        self.libPF_API.setSPADEnable.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getSPADEnable.arg_types = [ctypes.c_void_p]
        self.libPF_API.getDataSource.restype = ctypes.c_uint
        self.libPF_API.setDataSource.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getDataSource.arg_types = [ctypes.c_void_p]
        self.libPF_API.getEXTSTOPEnable.restype = ctypes.c_bool
        self.libPF_API.getTestPulseCount.restype = ctypes.c_int
        self.libPF_API.getTestStartDelay.restype = ctypes.c_int
        self.libPF_API.setEXTSTOPEnable.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getEXTSTOPEnable.arg_types = [ctypes.c_void_p]
        self.libPF_API.setTestPulseCount.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getTestPulseCount.arg_types = [ctypes.c_void_p]
        self.libPF_API.setTestStartDelay.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getTestStartDelay.arg_types = [ctypes.c_void_p]
        self.libPF_API.setEXTSTOPDelay.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.getShutterOutState.restype = ctypes.c_bool
        self.libPF_API.getShutterOutState.arg_types = [ctypes.c_void_p]
        self.libPF_API.setShutterOutState.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getBitsPerLine.arg_types = [ctypes.c_void_p]
        self.libPF_API.getBitsPerLine.restype = ctypes.c_int
        self.libPF_API.getLinesPerFrame.restype = ctypes.c_int
        self.libPF_API.getLinesPerFrame.arg_types = [ctypes.c_void_p]
        self.libPF_API.getFramesToSum.restype = ctypes.c_int
        self.libPF_API.getFramesToSum.arg_types = [ctypes.c_void_p]
        self.libPF_API.setFramesToSum.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.setFramePeriodAndOpticalExposure_us.arg_types = [ctypes.c_void_p, ctypes.c_double, ctypes.c_double]
        self.libPF_API.getExposure_us.restype = ctypes.c_double
        self.libPF_API.getExposure_us.arg_types = [ctypes.c_void_p]
        self.libPF_API.setExposure_us.arg_types = [ctypes.c_void_p, ctypes.c_double]
        self.libPF_API.setLineTiming.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.libPF_API.getSensorClk_Hz.restype = ctypes.c_int
        self.libPF_API.getSensorClk_Hz.arg_types = [ctypes.c_void_p]
        self.libPF_API.getSync_Hz.restype = ctypes.c_int
        self.libPF_API.getSync_Hz.arg_types = [ctypes.c_void_p]
        self.libPF_API.getSyncDutyRatio.restype = ctypes.c_double
        self.libPF_API.getSyncDutyRatio.arg_types = [ctypes.c_void_p]
        self.libPF_API.getRegionsOfInterest.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool), ctypes.POINTER(ctypes.c_bool)]
        self.libPF_API.setRegionsOfInterest.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_bool), ctypes.POINTER(ctypes.c_bool)]
        self.libPF_API.GetDeviceMajorVersion.restype = ctypes.c_int
        self.libPF_API.GetDeviceMajorVersion.arg_types = [ctypes.c_void_p]
        self.libPF_API.GetDeviceMinorVersion.restype = ctypes.c_int
        self.libPF_API.GetDeviceMinorVersion.arg_types = [ctypes.c_void_p]
        self.libPF_API.GetSerialNumber.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.SetTimeout.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.UpdateWireIns.arg_types = [ctypes.c_void_p]
        self.libPF_API.GetWireInValue.restype = ctypes.c_int
        self.libPF_API.GetWireInValue.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_uint)]
        self.libPF_API.SetWireInValue.restype = ctypes.c_int
        self.libPF_API.SetWireInValue.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong]
        self.libPF_API.GetWireOutValue.restype = ctypes.c_ulong
        self.libPF_API.GetWireOutValue.arg_types = [ctypes.c_void_p, ctypes.c_int]
        self.libPF_API.UpdateWireOuts.arg_types = [ctypes.c_void_p]
        self.libPF_API.UpdateTriggerOuts.arg_types = [ctypes.c_void_p]
        self.libPF_API.ActivateTriggerIn.restype = ctypes.c_int
        self.libPF_API.ActivateTriggerIn.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self.libPF_API.IsTriggered.restype = ctypes.c_int
        self.libPF_API.IsTriggered.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ulong]
        self.libPF_API.ReadFromPipeOut.restype = ctypes.c_long
        self.libPF_API.ReadFromPipeOut.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.ReadFromBlockPipeOut.restype = ctypes.c_long
        self.libPF_API.ReadFromBlockPipeOut.arg_types = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_long, ctypes.POINTER(ctypes.c_char)]
        self.libPF_API.getEnableFooters.restype = ctypes.c_bool
        self.libPF_API.getActualTemp.restype = ctypes.c_double
        self.libPF_API.getActualTemp.arg_types = [ctypes.c_void_p]
        self.libPF_API.setTargetTemp.arg_types = [ctypes.c_void_p, ctypes.c_double]
        self.libPF_API.getBoardTemp.restype = ctypes.c_double
        self.libPF_API.getBoardTemp.arg_types = [ctypes.c_void_p]
        self.libPF_API.setEnableCooling.restype = ctypes.c_bool
        self.libPF_API.setEnableFooters.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getEnableCooling.restype = ctypes.c_bool
        self.libPF_API.getEnableCooling.arg_types = [ctypes.c_void_p]
        self.libPF_API.setEnableCooling.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getEnableFooters.arg_types = [ctypes.c_void_p]
        self.libPF_API.iteratePositionalData_short.arg_types = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint16), ctypes.c_uint, ctypes.POINTER(ctypes.c_uint16), ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint]
        self.libPF_API.setSyncPolarity.arg_types = [ctypes.c_void_p, ctypes.c_bool]
        self.libPF_API.getSyncThreshold.restype = ctypes.c_int
        self.libPF_API.getSyncThreshold.arg_types = [ctypes.c_void_p]
        self.libPF_API.setSyncThreshold.arg_types = [ctypes.c_void_p, ctypes.c_int]
    
    
    def getVersionMajor(self):
        return self.libPF_API.getVersionMajor()
    
    def getVersionMinor(self):
        return self.libPF_API.getVersionMinor()
    
    def getVersionPatch(self):
        return self.libPF_API.getVersionPatch()
    
    def closeAll(self):
        self.libPF_API.closeAll()
    
    def noOfPFsInstantiated(self):
        return self.libPF_API.noOfPF32sInstantiated()
    
    def getPFInstanceByIndex(self, index):
        return self.libPF_API.getPF32InstanceByIndex(index)
    
    def createSession(self):
        return self.libPF_API.createSession()
    
    def executeSession(self, sessionHandle, buffered, performInitialPurge):
        return self.libPF_API.executeSession(sessionHandle, buffered, performInitialPurge)
    
    def addCamera(self, sessionHandle, cameraHandle, data, noOfFrames):
        return self.libPF_API.addCamera(sessionHandle, cameraHandle, data, noOfFrames)
    
    def addCamera_short(self, sessionHandle, cameraHandle, data, noOfFrames):
        return self.libPF_API.addCamera_short(sessionHandle, cameraHandle, data, noOfFrames)
    
    def destroySession(self, sessionHandle):
        return self.libPF_API.destroySession(sessionHandle)
    
    def setLogFileLevel(self, newLogLevel):
        self.libPF_API.setLogFileLevel(newLogLevel)
    
    def getLogFileLevel(self):
        return self.libPF_API.getLogFileLevel()
    
    def setLogStreamLevel(self, newLogLevel):
        self.libPF_API.setLogStreamLevel(newLogLevel)
    
    def getLogStreamLevel(self):
        return self.libPF_API.getLogStreamLevel()
    
    def PF_construct(self):
        return self.libPF_API.PF32_construct()
    
    def PF_constructWithCustomFirmware(self, firmwareFileName):
        return self.libPF_API.PF32_constructWithCustomFirmware(firmwareFileName)
    
    def PF_destruct(self):
        self.libPF_API.PF32_destruct(self.handle)
    
    def loadCustomFirmware(self, firmwareFileName):
        return self.libPF_API.loadCustomFirmware(self.handle, firmwareFileName)
    
    def getWidth(self):
        return self.libPF_API.getWidth(self.handle)
    
    def getHeight(self):
        return self.libPF_API.getHeight(self.handle)
    
    def getNoOfPixels(self):
        return self.libPF_API.getNoOfPixels(self.handle)
    
    def getEnabledNoOfPixels(self):
        return self.libPF_API.getEnabledNoOfPixels(self.handle)
    
    def getEnabledHeight(self):
        return self.libPF_API.getEnabledHeight(self.handle)
    
    def getNoOfTDCCodes(self):
        return self.libPF_API.getNoOfTDCCodes(self.handle)
    
    def getLinkStatus(self):
        return self.libPF_API.getLinkStatus(self.handle)
    
    def setMode(self, mode):
        self.libPF_API.setMode(self.handle, mode)
    
    def setI2C(self, data, address):
        return self.libPF_API.setI2C(self.handle, data, address)
    
    def getI2C(self, address, dataOut):
        return self.libPF_API.getI2C(self.handle, address, dataOut)
    
    def applyDACDefaultValues(self):
        self.libPF_API.applyDACDefaultValues(self.handle)
    
    def setDAC(self, dacType, value):
        return self.libPF_API.setDAC(self.handle, dacType, value)
    
    def getDAC(self, dacType):
        return self.libPF_API.getDAC(self.handle, dacType)
    
    def getMaxValueOfDAC(self, dacType):
        return self.libPF_API.getMaxValueOfDAC(self.handle, dacType)
    
    def getNextFrames(self, data, noOfFrames, buffered, performInitialPurge):
        return self.libPF_API.getNextFrames(self.handle, data, noOfFrames, buffered, performInitialPurge)
    
    def getNextFrames_short(self, data, noOfFrames, buffered, performInitialPurge):
        return self.libPF_API.getNextFrames_short(self.handle, data, noOfFrames, buffered, performInitialPurge)
    
    def getHistogram(self, data, noOfSeconds):
        return self.libPF_API.getHistogram(self.handle, data, noOfSeconds)
    
    def getHistogram_short(self, data, noOfSeconds):
        return self.libPF_API.getHistogram_short(self.handle, data, noOfSeconds)
    
    def getHistogram_char(self, data, noOfSeconds):
        return self.libPF_API.getHistogram_char(self.handle, data, noOfSeconds)

    def getNoOfFramesToHistogram(self):
        return self.libPF_API.getNoOfFramesToHistogram(self.handle)

    def setNoOfFramesToHistogram(self, noOfFrames):
        return self.libPF_API.setNoOfFramesToHistogram(self.handle, noOfFrames)

    def setNoOfBinsInHistogram(self, noOfBins):
        return self.libPF_API.setNoOfBinsInHistogram(self.handle, noOfBins)

    def getNoOfBinsInHistogram(self):
        return self.libPF_API.getNoOfBinsInHistogram(self.handle)

    def getHistogramFromFirmware(self, data):
        return self.libPF_API.getHistogramFromFirmware(self.handle, data)
    
    def getNoOfFramesInBuffer(self):
        return self.libPF_API.getNoOfFramesInBuffer(self.handle)
    
    def setNoOfFramesInBuffer(self, noOfFrames):
        self.libPF_API.setNoOfFramesInBuffer(self.handle, noOfFrames)
    
    def getMultipleOfBuffer(self):
        return self.libPF_API.getMultipleOfBuffer(self.handle)
    
    def setMultipleOfBuffer(self, multiple):
        self.libPF_API.setMultipleOfBuffer(self.handle, multiple)
    
    def getModelNumber(self, buffer):
        self.libPF_API.getModelNumber(self.handle, buffer)
    
    def getSerialNumber(self, buffer):
        self.libPF_API.getSerialNumber(self.handle, buffer)
    
    def purgeBulkFrameBuffer(self):
        self.libPF_API.purgeBulkFrameBuffer(self.handle)
    
    def getBitMode(self):
        return self.libPF_API.getBitMode(self.handle)
    
    def setSPADEnable(self, SPAD_en):
        self.libPF_API.setSPADEnable(self.handle, SPAD_en)
    
    def getSPADEnable(self):
        return self.libPF_API.getSPADEnable(self.handle)
    
    def setDataSource(self, source):
        self.libPF_API.setDataSource(self.handle, source)
    
    def getDataSource(self):
        return self.libPF_API.getDataSource(self.handle)
    
    def setEXTSTOPEnable(self, EXTSTOP_enable):
        self.libPF_API.setEXTSTOPEnable(self.handle, EXTSTOP_enable)
    
    def getEXTSTOPEnable(self):
        return self.libPF_API.getEXTSTOPEnable(self.handle)
    
    def setTestPulseCount(self, testPulseCount):
        self.libPF_API.setTestPulseCount(self.handle, testPulseCount)
    
    def getTestPulseCount(self):
        return self.libPF_API.getTestPulseCount(self.handle)
    
    def setTestStartDelay(self, testStartDelay):
        self.libPF_API.setTestStartDelay(self.handle, testStartDelay)
    
    def getTestStartDelay(self):
        return self.libPF_API.getTestStartDelay(self.handle)
    
    def setEXTSTOPDelay(self, EXTSTOP_delay):
        self.libPF_API.setEXTSTOPDelay(self.handle, EXTSTOP_delay)
    
    def setShutterOutState(self, shutterOutState):
        self.libPF_API.setShutterOutState(self.handle, shutterOutState)
    
    def getShutterOutState(self):
        return self.libPF_API.getShutterOutState(self.handle)
    
    def getBitsPerLine(self):
        return self.libPF_API.getBitsPerLine(self.handle)
    
    def getLinesPerFrame(self):
        return self.libPF_API.getLinesPerFrame(self.handle)
    
    def setFramesToSum(self, framesToSum):
        self.libPF_API.setFramesToSum(self.handle, framesToSum)
    
    def getFramesToSum(self):
        return self.libPF_API.getFramesToSum(self.handle)
    
    def setExposure_us(self, exposure):
        self.libPF_API.setExposure_us(self.handle, exposure)
    
    def setFramePeriodAndOpticalExposure_us(self, framePeriod, opticalExposure):
        self.libPF_API.setFramePeriodAndOpticalExposure_us(self.handle, framePeriod, opticalExposure)
    
    def getExposure_us(self):
        return self.libPF_API.getExposure_us(self.handle)
    
    def setLineTiming(self, bitsPerLine, linesPerFrame):
        self.libPF_API.setLineTiming(self.handle, bitsPerLine, linesPerFrame)
    
    def getSensorClk_Hz(self):
        return self.libPF_API.getSensorClk_Hz(self.handle)
    
    def getSync_Hz(self):
        return self.libPF_API.getSync_Hz(self.handle)
    
    def getSyncDutyRatio(self):
        return self.libPF_API.getSyncDutyRatio(self.handle)
    
    def getRegionsOfInterest(self, columns, rows):
        self.libPF_API.getRegionsOfInterest(self.handle, columns, rows)
    
    def setRegionsOfInterest(self, columns, rows):
        self.libPF_API.setRegionsOfInterest(self.handle, columns, rows)
    
    def GetDeviceMajorVersion(self):
        return self.libPF_API.GetDeviceMajorVersion(self.handle)
    
    def GetDeviceMinorVersion(self):
        return self.libPF_API.GetDeviceMinorVersion(self.handle)
    
    def GetSerialNumber(self, buf):
        self.libPF_API.GetSerialNumber(self.handle, buf)
    
    def SetTimeout(self, timeout):
        self.libPF_API.SetTimeout(self.handle, timeout)
    
    def UpdateWireIns(self):
        self.libPF_API.UpdateWireIns(self.handle)
    
    def GetWireInValue(self, epAddr, val):
        return self.libPF_API.GetWireInValue(self.handle, epAddr, val)
    
    def SetWireInValue(self, ep, val, mask):
        return self.libPF_API.SetWireInValue(self.handle, ep, val, mask)
    
    def UpdateWireOuts(self):
        self.libPF_API.UpdateWireOuts(self.handle)
    
    def GetWireOutValue(self, epAddr):
        return self.libPF_API.GetWireOutValue(self.handle, epAddr)
    
    def ActivateTriggerIn(self, epAddr, bit):
        return self.libPF_API.ActivateTriggerIn(self.handle, epAddr, bit)
    
    def UpdateTriggerOuts(self):
        self.libPF_API.UpdateTriggerOuts(self.handle)
    
    def IsTriggered(self, epAddr, mask):
        return self.libPF_API.IsTriggered(self.handle, epAddr, mask)
    
    def ReadFromPipeOut(self, epAddr, length, data):
        return self.libPF_API.ReadFromPipeOut(self.handle, epAddr, length, data)
    
    def ReadFromBlockPipeOut(self, epAddr, blockSize, length, data):
        return self.libPF_API.ReadFromBlockPipeOut(self.handle, epAddr, blockSize, length, data)
    
    def setEnableFooters(self, enableFooters):
        self.libPF_API.setEnableFooters(self.handle, enableFooters)
    
    def getEnableFooters(self):
        return self.libPF_API.getEnableFooters(self.handle)
    
    def iteratePositionalData_short(self, data, whichFrame, frameData, positionalData, enabledHeight):
        self.libPF_API.iteratePositionalData_short(self.handle, data, whichFrame, frameData, positionalData, enabledHeight)
    
    def setTargetTemp(self, setpoint_K):
        self.libPF_API.setTargetTemp(self.handle, setpoint_K)
    
    def getActualTemp(self):
        return self.libPF_API.getActualTemp(self.handle)
    
    def getBoardTemp(self):
        return self.libPF_API.getBoardTemp(self.handle)
    
    def setEnableCooling(self, enableCooling):
        return self.libPF_API.setEnableCooling(self.handle, enableCooling)
    
    def getEnableCooling(self):
        return self.libPF_API.getEnableCooling(self.handle)
    
    def setSyncPolarity(self, positive):
        return self.libPF_API.setSyncPolarity(self.handle, positive)
    
    def setSyncThreshold(self, threshold):
        return self.libPF_API.setSyncThreshold(self.handle, threshold)
    
    def getSyncThreshold(self):
        return self.libPF_API.getSyncThreshold(self.handle)
    
    
    def createSession(self):
        return self.libPF_API.createSession()
    
    def createLogCallback(self, callback):
        return ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int)(callback)
    
    def setLogCallback(self, logCallback):
        self.libPF_API.setLogCallback(logCallback)
    
    def createStatusCallback(self, callback):
        return ctypes.CFUNCTYPE(None, ctypes.c_int)(callback)
    
    def setStatusCallback(self, statusCallback):
        self.libPF_API.setStatusCallback(self.handle, statusCallback)
    
    def statusMessage(self, status):
        if status == 0:
            return "Connected"
        elif status == 1:
            return "ConnectedButNotInitialised"
        elif status == 2:
            return "Ready"
        elif status == 3:
            return "Error"
        else:
            return "UnknowStatus"
    

