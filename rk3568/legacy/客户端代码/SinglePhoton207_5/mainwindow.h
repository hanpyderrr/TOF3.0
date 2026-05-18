#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QLabel>
#include <QTimer>
#include <QVector>
#include <QImage>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QMutex>
#include "image.h"
#include "clientAliyun.h"
#include "clientGroup2.h"
#include "turntableUart.h"
#include "motorUart.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:

    //课题二服务器连接相关槽函数
    void updateServerGroup2ConnectionStatus(const QString &status);//更新课题二服务器连接状态标签的槽函数，有状态更新信号发送的时候调用这个函数
    void sendDataToServerGroup2(); // 定期向课题二服务器发送数据的槽函数

    //阿里云服务器连接相关槽函数
    void updateServerAliyunConnectionStatus(const QString &status);//更新阿罗约服务器连接状态标签的槽函数，有状态更新信号发送的时候调用这个函数
    void sendDataToServerAliyun(); // 定期向阿里云服务器发送数据的槽函数
    void handleReceivedServerAliyunData(const QByteArray &data); // 处理接收到的阿里云服务器数据的槽函数

    //成像相关槽函数
    void updateImage(); // 定时器触发时调用成像和显示的槽函数


private:
    //布局部分
    QVBoxLayout *MainVerLayout;//整个界面的垂直布局
    QWidget *MainVerWidget;//整个界面的垂直容器

    //网络连接及数据发送部分控件
    QTimer *sendDataToServerGroup2Timer;//定时向课题2服务器发送数据的定时器
    QTimer *sendDataToServerAliyunTimer;//定时向阿里云服务器发送数据的定时器
    QLabel *serverGroup2ConnectStatusLabel;//课题2服务器连接状态标签
    QLabel *serverAliyunConnectStatusLabel;//阿里云服务器连接状态标签

    //成像功能部分控件
    QTimer *readFileAndImageTimer; // 读取文件并成像的定时器
    QLabel *imageLabel; // 用于显示图像的标签

    //转台部分
    QLabel *turntableUartStatusLabel; //云台串口状态标签

    //电机调焦部分
    QLabel *motorUartStatusLabel; //电机调焦串口状态标签

    ImageProcessor imageProcessor; // 图像处理器实例
    ClientGroup2 *clientGroup2;
    ClientAliyun *clientAliyun;
    TurntableUart *turntableUart;
    MotorUart *motorUart;

};
#endif // MAINWINDOW_H
