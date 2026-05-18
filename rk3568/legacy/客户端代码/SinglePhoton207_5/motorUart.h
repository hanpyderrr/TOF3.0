#ifndef MOTORUART_H
#define MOTORUART_H

#include <QObject>
#include <QSerialPort>
#include <QString>

class MotorUart : public QObject
{
    Q_OBJECT

public:
    explicit MotorUart(const QString &portName, QObject *parent = nullptr);
    bool openMotorSerialPort();//打开电机控制串口并进行初始化操作
    void sendMotorUartData(const QByteArray &data);//电机串口发送数据


private:
    QSerialPort *serial;//实例化serial对象

};

#endif // MOTORUART_H
