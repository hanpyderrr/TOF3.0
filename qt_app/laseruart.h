#pragma once

#include <QObject>
#include <QSerialPort>

struct LaserParams {
    uint8_t level = 0;     // voltage level 1-200
    uint32_t freqHz = 0;
    uint8_t pulseNs = 0;   // pulse width in ns/5 units
    uint8_t mode = 0;      // 0=internal, 2=external trigger
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
};
