#include "motorUart.h"
#include <QDebug>

MotorUart::MotorUart(const QString &portName, QObject *parent)
    : QObject(parent), serial(new QSerialPort(portName, this)) // 初始化serial，portName是要打开的串口路径
{

}

bool MotorUart::openMotorSerialPort()
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

void MotorUart::sendMotorUartData(const QByteArray &data)
{
    if (serial->isOpen())
    {
        serial->write(data);
    }
}
