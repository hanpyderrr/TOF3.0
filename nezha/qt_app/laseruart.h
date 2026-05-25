#pragma once

// LaserUart — YSC-SO-M04-4 pulse laser driver (Modbus RTU, 9600 8N1).
//
// Sync architecture (confirmed: ExampleTOF.cpp/FW_Histogramming.cpp run the
// PF32 in TCSPC_sys_master). PF32 is the master and emits a TRIG output that
// drives the laser P3 external-trigger input; PF32's internal EXTSTOP is the
// TDC stop (reverse start-stop, distance = (1023-bin)*55ps*c/2). Therefore:
//   - The laser MUST run in external-trigger mode.
//   - Its repetition rate follows the PF32 TRIG output, NOT setFreqHz; calling
//     setFreqHz in external-trigger mode is meaningless and is rejected.
// Frame: [func 1B][data 4B big-endian][CRC16 2B little-endian], 7 bytes total.
// (PF32 SyncInput_3300mV.pdf describes the opposite wiring — laser SYNC into
//  PF32 SYNC input, i.e. laser_master — and does NOT apply to this project.)

#include <QObject>
#include <QSerialPort>

struct LaserParams {
    uint8_t level = 0;     // voltage level 1-200
    uint32_t freqHz = 0;
    uint8_t pulseNs = 0;   // pulse width in ns/5 units
    uint8_t mode = 0;      // 0=off, 1=internal(start), 2=external trigger
};

class LaserUart : public QObject {
    Q_OBJECT
public:
    explicit LaserUart(QObject *parent = nullptr);
    ~LaserUart();

    bool open(const QString &portName);
    void close();
    bool isOpen() const;

    // Commands
    bool setExternalTrigger();   // switch to PF32 TTL trigger mode
    bool setInternalTrigger();
    bool laserOff();
    bool setLevel(uint8_t level);          // 1-200
    bool setFreqHz(uint32_t hz);           // 1-1000000
    bool setPulseWidth(uint8_t nsDiv5);    // pulse = nsDiv5 * 5 ns
    bool readParams(LaserParams &out);

    uint8_t currentLevel() const { return m_level; }

signals:
    void errorOccurred(const QString &msg);

private:
    bool sendFrame(const QByteArray &frame);
    static QByteArray buildFrame(uint8_t func, uint32_t data);
    static uint16_t crc16Modbus(const uint8_t *data, int len);

    QSerialPort *m_port = nullptr;
    uint8_t m_level = 50;
    bool m_extTrigger = false;  // true after setExternalTrigger() (PF32 sys_master)
};
