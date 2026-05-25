#include "laseruart.h"

#include <QThread>

// Laser command function codes
static constexpr uint8_t FUNC_VOLTAGE  = 0x01;
static constexpr uint8_t FUNC_FREQ     = 0x02;
static constexpr uint8_t FUNC_PULSE    = 0x03;
static constexpr uint8_t FUNC_TRIGGER  = 0x04;
static constexpr uint8_t FUNC_READ     = 0x06;

static constexpr uint32_t DATA_LASER_OFF      = 0x00;
static constexpr uint32_t DATA_TRIGGER_INT    = 0x01;
static constexpr uint32_t DATA_TRIGGER_EXT    = 0x02;

LaserUart::LaserUart(QObject *parent) : QObject(parent)
{
    m_port = new QSerialPort(this);
}

LaserUart::~LaserUart()
{
    close();
}

bool LaserUart::open(const QString &portName)
{
    m_port->setPortName(portName);
    m_port->setBaudRate(QSerialPort::Baud9600);
    m_port->setDataBits(QSerialPort::Data8);
    m_port->setParity(QSerialPort::NoParity);
    m_port->setStopBits(QSerialPort::OneStop);
    m_port->setFlowControl(QSerialPort::NoFlowControl);

    if (!m_port->open(QIODevice::ReadWrite)) {
        emit errorOccurred(QString("laser open failed: %1").arg(m_port->errorString()));
        return false;
    }
    return true;
}

void LaserUart::close()
{
    if (m_port && m_port->isOpen())
        m_port->close();
}

bool LaserUart::isOpen() const
{
    return m_port && m_port->isOpen();
}

bool LaserUart::setExternalTrigger()
{
    bool ok = sendFrame(buildFrame(FUNC_TRIGGER, DATA_TRIGGER_EXT));
    if (ok) m_extTrigger = true;
    return ok;
}

bool LaserUart::setInternalTrigger()
{
    bool ok = sendFrame(buildFrame(FUNC_TRIGGER, DATA_TRIGGER_INT));
    if (ok) m_extTrigger = false;
    return ok;
}

bool LaserUart::laserOff()
{
    return sendFrame(buildFrame(FUNC_TRIGGER, DATA_LASER_OFF));
}

bool LaserUart::setLevel(uint8_t level)
{
    if (level < 1 || level > 200) return false;
    bool ok = sendFrame(buildFrame(FUNC_VOLTAGE, level));
    if (ok) m_level = level;
    return ok;
}

bool LaserUart::setFreqHz(uint32_t hz)
{
    // In external-trigger mode (PF32 sys_master) the repetition rate is set by
    // the PF32 TRIG output; the laser's internal frequency is ignored. Reject
    // the call so callers don't get a false sense of having changed the rate.
    if (m_extTrigger) {
        emit errorOccurred("setFreqHz ignored: external-trigger mode, rate follows PF32 TRIG");
        return false;
    }
    return sendFrame(buildFrame(FUNC_FREQ, hz));
}

bool LaserUart::setPulseWidth(uint8_t nsDiv5)
{
    return sendFrame(buildFrame(FUNC_PULSE, nsDiv5));
}

bool LaserUart::readParams(LaserParams &out)
{
    // Send read command: 06 00 00 00 00 AC 00  (matches the manual's example).
    //
    // WARNING: the response parsing below does NOT match the manual's worked
    // example reply `06 06 15 00 00 13 88 00 06 00 00 00 E5 41` (14 bytes,
    // voltage level 21 / 5kHz / 30ns) — there byte[1]=0x06 is not the level.
    // The manual's own table (13 bytes) and example (14 bytes) are themselves
    // inconsistent. Do NOT trust this field mapping until verified against a
    // real-device capture (e.g. sscom). See docs/agent-work/progress.md.
    QByteArray frame;
    frame.append('\x06');
    frame.append('\x00');
    frame.append('\x00');
    frame.append('\x00');
    frame.append('\x00');
    frame.append('\xAC');
    frame.append('\x00');

    if (!sendFrame(frame))
        return false;

    // Wait briefly for response (13 bytes)
    QThread::msleep(50);
    QByteArray resp = m_port->readAll();
    if (resp.size() < 13)
        return false;

    // Parse response: [func][voltage][freq 4B big-endian][pulse][mode][CRC 2B]
    out.level   = static_cast<uint8_t>(resp[1]);
    out.freqHz  = (static_cast<uint32_t>(static_cast<uint8_t>(resp[2])) << 24)
                | (static_cast<uint32_t>(static_cast<uint8_t>(resp[3])) << 16)
                | (static_cast<uint32_t>(static_cast<uint8_t>(resp[4])) << 8)
                |  static_cast<uint32_t>(static_cast<uint8_t>(resp[5]));
    out.pulseNs = static_cast<uint8_t>(resp[6]);
    out.mode    = static_cast<uint8_t>(resp[7]);
    return true;
}

// --- private ---

bool LaserUart::sendFrame(const QByteArray &frame)
{
    if (!isOpen()) return false;
    const qint64 written = m_port->write(frame);
    m_port->flush();
    return written == frame.size();
}

QByteArray LaserUart::buildFrame(uint8_t func, uint32_t data)
{
    // Frame: [func 1B][data 4B big-endian][CRC16 2B little-endian]
    uint8_t buf[5];
    buf[0] = func;
    buf[1] = static_cast<uint8_t>((data >> 24) & 0xFF);
    buf[2] = static_cast<uint8_t>((data >> 16) & 0xFF);
    buf[3] = static_cast<uint8_t>((data >>  8) & 0xFF);
    buf[4] = static_cast<uint8_t>( data        & 0xFF);

    uint16_t crc = crc16Modbus(buf, 5);

    QByteArray frame;
    frame.resize(7);
    frame[0] = static_cast<char>(buf[0]);
    frame[1] = static_cast<char>(buf[1]);
    frame[2] = static_cast<char>(buf[2]);
    frame[3] = static_cast<char>(buf[3]);
    frame[4] = static_cast<char>(buf[4]);
    frame[5] = static_cast<char>(crc & 0xFF);
    frame[6] = static_cast<char>((crc >> 8) & 0xFF);
    return frame;
}

uint16_t LaserUart::crc16Modbus(const uint8_t *data, int len)
{
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int j = 0; j < 8; ++j) {
            if (crc & 0x0001)
                crc = (crc >> 1) ^ 0xA001;
            else
                crc >>= 1;
        }
    }
    return crc;
}
