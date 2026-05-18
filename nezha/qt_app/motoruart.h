#pragma once

#include <QObject>
#include <QSerialPort>

class MotorUart : public QObject {
    Q_OBJECT
public:
    explicit MotorUart(QObject *parent = nullptr);
    ~MotorUart();

    bool open(const QString &portName);
    void close();
    bool isOpen() const;

    // Slide motor (focus, device 0x01)
    bool slideForward(bool roughly = true);
    bool slideBack(bool roughly = true);

    // Gear motor (aperture, device 0x02)
    bool gearClockwise(bool roughly = true);
    bool gearAnticlockwise(bool roughly = true);

signals:
    void errorOccurred(const QString &msg);

private:
    bool sendCmd(uint8_t device, uint8_t cmdHi, uint8_t cmdLo);

    QSerialPort *m_port = nullptr;
};
