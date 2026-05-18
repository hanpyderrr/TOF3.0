#include "turntableUart.h"
#include <QDebug>

TurntableUart::TurntableUart(const QString &portName, QObject *parent)
    : QObject(parent), serial(new QSerialPort(portName, this)) // 初始化serial，portName是要打开的串口路径
{
    // 连接串口的 readyRead 信号，以便读取数据
    connect(serial, &QSerialPort::readyRead, this, &TurntableUart::readTurntableUartData);
}

bool TurntableUart::openTurntableSerialPort()
{
    if (serial->open(QIODevice::ReadWrite))
    {
        // 串口配置
        serial->setBaudRate(QSerialPort::Baud19200);//设置波特率
        serial->setDataBits(QSerialPort::Data8);//设置8位数据位
        serial->setParity(QSerialPort::NoParity);//无奇偶校验位
        serial->setStopBits(QSerialPort::OneStop);//1位停止位
        serial->setFlowControl(QSerialPort::NoFlowControl);//不使用流控
        return true;
    }
    return false;
}

void TurntableUart::readTurntableUartData()
{
    // 读取可用的数据
    QByteArray data = serial->readAll();

    // 如果接收到的数据长度不是8个字节，直接返回
    if (data.size() != 8)
    {
        return; // 不处理不是8字节的数据
    }

    // 数据包有效，准备处理
    uint16_t packet[8];
    for (int j = 0; j < 8; ++j)
    {
        packet[j] = static_cast<uint8_t>(data[j]);
    }

    // 检查数据包的有效性并存储数据
    if (packet[0] == 0xCA && packet[1] == 0x07 && packet[6] == (0xCA ^ 0x07) && packet[7] == 0xF1)
    {
        QMutexLocker locker(&azimuthMutex);//这里的锁会自动释放
        // 将数据存储在 azimuthBuffer 中，最大为8
        if (azimuthIndex < sizeof(azimuthBuffer) / sizeof(azimuthBuffer[0]))
        {
            azimuthBuffer[azimuthIndex++] = packet[0];
            azimuthBuffer[azimuthIndex++] = packet[1];
            azimuthBuffer[azimuthIndex++] = packet[2];
            azimuthBuffer[azimuthIndex++] = packet[3];
            azimuthBuffer[azimuthIndex++] = packet[4];
            azimuthBuffer[azimuthIndex++] = packet[5];
            azimuthBuffer[azimuthIndex++] = packet[6];
            azimuthBuffer[azimuthIndex++] = packet[7];
        }
        azimuthIndex=0;
    }
    else if (packet[0] == 0xCA && packet[1] == 0x17 && packet[6] == (0xCA ^ 0x17) && packet[7] == 0xF1)
    {
        QMutexLocker locker(&elevationMutex);
        // 将数据存储在 elevationBuffer 中，最大为8
        if (elevationIndex < sizeof(elevationBuffer) / sizeof(elevationBuffer[0]))
        {
            elevationBuffer[elevationIndex++] = packet[0];
            elevationBuffer[elevationIndex++] = packet[1];
            elevationBuffer[elevationIndex++] = packet[2];
            elevationBuffer[elevationIndex++] = packet[3];
            elevationBuffer[elevationIndex++] = packet[4];
            elevationBuffer[elevationIndex++] = packet[5];
            elevationBuffer[elevationIndex++] = packet[6];
            elevationBuffer[elevationIndex++] = packet[7];
        }
        elevationIndex=0;
    }
    else if (packet[0] == 0xCA && packet[1] == 0x27 && packet[6] == (0xCA ^ 0x27) && packet[7] == 0xF1)
    {
        QMutexLocker locker(&velocityMutex);
        // 将数据存储在 velocityBuffer 中，最大为8
        if (velocityIndex < sizeof(velocityBuffer) / sizeof(velocityBuffer[0]))
        {
            velocityBuffer[velocityIndex++] = packet[0];
            velocityBuffer[velocityIndex++] = packet[1];
            velocityBuffer[velocityIndex++] = packet[2];
            velocityBuffer[velocityIndex++] = packet[3];
            velocityBuffer[velocityIndex++] = packet[4];
            velocityBuffer[velocityIndex++] = packet[5];
            velocityBuffer[velocityIndex++] = packet[6];
            velocityBuffer[velocityIndex++] = packet[7];
        }
        velocityIndex = 0;
    }
}

const uint16_t* TurntableUart::getAzimuthBuffer() const
{
    QMutexLocker locker(&azimuthMutex);
    return azimuthBuffer; // 返回指向 azimuthBuffer 的指针
}

const uint16_t* TurntableUart::getElevationBuffer() const
{
    QMutexLocker locker(&elevationMutex);
    return elevationBuffer; // 返回指向 elevationBuffer 的指针
}

const uint16_t* TurntableUart::getVelocityBuffer() const
{
    QMutexLocker locker(&velocityMutex);
    return velocityBuffer; // 返回指向 velocityBuffer 的指针
}
