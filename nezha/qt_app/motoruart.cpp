#include "motoruart.h"

// STM32 lens-focus serial protocol (19200 8N1).
// Frame: FF 02 [device] [cmdHi] [cmdLo] [checksum],
// checksum = (0x02 + device + cmdHi + cmdLo) & 0xFF.
// NOTE: this is the proven v1.0 protocol; per the confirmed architecture
// decision this controller is to migrate to the RK3568 side
// (see docs/rk3568_framework.md §3.3). Kept here as transition implementation.

// Device IDs
static constexpr uint8_t DEV_SLIDE = 0x01;  // 直线滑台（调焦）
static constexpr uint8_t DEV_GEAR  = 0x02;  // 齿轮（光圈）

// cmdHi: direction, per device
static constexpr uint8_t SLIDE_FWD_HI  = 0x20;  // 滑台前进
static constexpr uint8_t SLIDE_BACK_HI = 0x22;  // 滑台后退
static constexpr uint8_t GEAR_CW_HI    = 0x40;  // 齿轮顺时针
static constexpr uint8_t GEAR_CCW_HI   = 0x42;  // 齿轮逆时针

// cmdLo: step granularity
static constexpr uint8_t LO_ROUGH = 0x01;  // 粗调
static constexpr uint8_t LO_FINE  = 0x02;  // 细调

MotorUart::MotorUart(QObject *parent) : QObject(parent)
{
    m_port = new QSerialPort(this);
}

MotorUart::~MotorUart()
{
    close();
}

bool MotorUart::open(const QString &portName)
{
    m_port->setPortName(portName);
    m_port->setBaudRate(19200);
    m_port->setDataBits(QSerialPort::Data8);
    m_port->setParity(QSerialPort::NoParity);
    m_port->setStopBits(QSerialPort::OneStop);
    m_port->setFlowControl(QSerialPort::NoFlowControl);

    if (!m_port->open(QIODevice::ReadWrite)) {
        emit errorOccurred(QString("motor open failed: %1").arg(m_port->errorString()));
        return false;
    }
    return true;
}

void MotorUart::close()
{
    if (m_port && m_port->isOpen())
        m_port->close();
}

bool MotorUart::isOpen() const
{
    return m_port && m_port->isOpen();
}

bool MotorUart::slideForward(bool roughly)
{
    return sendCmd(DEV_SLIDE, SLIDE_FWD_HI, roughly ? LO_ROUGH : LO_FINE);
}

bool MotorUart::slideBack(bool roughly)
{
    return sendCmd(DEV_SLIDE, SLIDE_BACK_HI, roughly ? LO_ROUGH : LO_FINE);
}

bool MotorUart::gearClockwise(bool roughly)
{
    return sendCmd(DEV_GEAR, GEAR_CW_HI, roughly ? LO_ROUGH : LO_FINE);
}

bool MotorUart::gearAnticlockwise(bool roughly)
{
    return sendCmd(DEV_GEAR, GEAR_CCW_HI, roughly ? LO_ROUGH : LO_FINE);
}

bool MotorUart::sendCmd(uint8_t device, uint8_t cmdHi, uint8_t cmdLo)
{
    if (!isOpen()) return false;

    // Frame: FF 02 [device] [cmdHi] [cmdLo] [checksum]
    const uint8_t checksum = static_cast<uint8_t>(0x02 + device + cmdHi + cmdLo);
    char frame[6] = {
        static_cast<char>(0xFF),
        static_cast<char>(0x02),
        static_cast<char>(device),
        static_cast<char>(cmdHi),
        static_cast<char>(cmdLo),
        static_cast<char>(checksum)
    };

    const qint64 written = m_port->write(frame, 6);
    m_port->flush();
    return written == 6;
}
