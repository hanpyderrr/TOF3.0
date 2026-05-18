#ifndef TURNTABLEUART_H
#define TURNTABLEUART_H

#include <QObject>
#include <QSerialPort>
#include <QString>
#include <QMutex>

class TurntableUart : public QObject
{
    Q_OBJECT

public:
    explicit TurntableUart(const QString &portName, QObject *parent = nullptr);
    bool openTurntableSerialPort();//打开云台串口并进行初始化操作


    // 提供访问串口数据的接口函数
    const uint16_t* getAzimuthBuffer() const; // 返回方位数据数组指针
    const uint16_t* getElevationBuffer() const; // 返回俯仰数据数组指针
    const uint16_t* getVelocityBuffer() const; // 返回速度数据数组指针


private slots:
    /*这个函数被连接到QSerialPort的readyRead()信号，串口有数据到达时，串口会发射readyRead()信号给Uart，
      从而触发Uart的readTurntableUartData()函数*/
    void readTurntableUartData();

private:
    QSerialPort *serial;//实例化serial对象

    // 存储接收到的串口数据的数组，最大长度为8
    uint16_t azimuthBuffer[8] = {0}; // 方位缓冲区
    uint16_t elevationBuffer[8] = {0}; // 俯仰缓冲区
    uint16_t velocityBuffer[8] = {0}; // 速度缓冲区

    size_t azimuthIndex = 0; // 记录方位缓冲区的写入位置
    size_t elevationIndex = 0; // 记录俯仰缓冲区的写入位置
    size_t velocityIndex = 0; // 记录速度缓冲区的写入位置

    // 创建三把锁对串口数据进行保护
    mutable QMutex azimuthMutex;
    mutable QMutex elevationMutex;
    mutable QMutex velocityMutex;

};

#endif // TURNTABLEUART_H
