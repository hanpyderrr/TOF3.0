#include "motoruart.h"

// Device IDs
static constexpr uint8_t DEV_SLIDE = 0x01;
static constexpr uint8_t DEV_GEAR  = 0x02;

// Command bytes [hi, lo]
static constexpr uint8_t CMD_FORWARD_ROUGHLY_HI = 0x20;
static constexpr uint8_t CMD_FORWARD_ROUGHLY_LO = 0x01;
static constexpr uint8_t CMD_BACK_ROUGHLY_HI    = 0x22;
static constexpr uint8_t CMD_BACK_ROUGHLY_LO    = 0x01;
static constexpr uint8_t CMD_FORWARD_FINELY_HI  = 0x20;
static constexpr uint8_t CMD_FORWARD_FINELY_LO  = 0x02;
static constexpr uint8_t CMD_BACK_FINELY_HI     = 0x22;
static constexpr uint8_t CMD_BACK_FINELY_LO     = 0x02;

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
    return roughly
        ? sendCmd(DEV_SLIDE, CMD_FORWARD_ROUGHLY_HI, CMD_FORWARD_ROUGHLY_LO)
        : sendCmd(DEV_SLIDE, CMD_FORWARD_FINELY_HI,  CMD_FORWARD_FINELY_LO);
}

bool MotorUart::slideBack(bool roughly)
{
    return roughly
        ? sendCmd(DEV_SLIDE, CMD_BACK_ROUGHLY_HI, CMD_BACK_ROUGHLY_LO)
        : sendCmd(DEV_SLIDE, CMD_BACK_FINELY_HI,  CMD_BACK_FINELY_LO);
}

bool MotorUart::gearClockwise(bool roughly)
{
    return roughly
        ? sendCmd(DEV_GEAR, CMD_FORWARD_ROUGHLY_HI, CMD_FORWARD_ROUGHLY_LO)
        : sendCmd(DEV_GEAR, CMD_FORWARD_FINELY_HI,  CMD_FORWARD_FINELY_LO);
}

bool MotorUart::gearAnticlockwise(bool roughly)
{
    return roughly
        ? sendCmd(DEV_GEAR, CMD_BACK_ROUGHLY_HI, CMD_BACK_ROUGHLY_LO)
        : sendCmd(DEV_GEAR, CMD_BACK_FINELY_HI,  CMD_BACK_FINELY_LO);
}

bool MotorUart::sendCmd(uint8_t device, uint8_t cmdHi, uint8_t cmdLo)
{
    if (!isOpen()) return false;

    // Frame: FF 02 [device] [cmdHi] [cmdLo] 00
    char frame[6] = {
        static_cast<char>(0xFF),
        static_cast<char>(0x02),
        static_cast<char>(device),
        static_cast<char>(cmdHi),
        static_cast<char>(cmdLo),
        static_cast<char>(0x00)
    };

    const qint64 written = m_port->write(frame, 6);
    m_port->flush();
    return written == 6;
}
