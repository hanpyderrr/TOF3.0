#include "clientGroup2.h"
#include "mainwindow.h"
#include <QDebug>
#include <QHostAddress>

ClientGroup2::ClientGroup2(QObject *parent) : QObject(parent), socketGroup2(new QTcpSocket(this))
{
    //初始化重连定时器
    retryConnectTimerGroup2 = new QTimer(this);

    connect(retryConnectTimerGroup2, &QTimer::timeout, this, &ClientGroup2::retryConnectToServerGroup2);
    connect(socketGroup2, &QTcpSocket::connected, this, &ClientGroup2::onServerGroup2Connected);
    connect(socketGroup2, &QTcpSocket::disconnected, this, &ClientGroup2::onServerGroup2Disconnected);
    connect(socketGroup2, &QTcpSocket::errorOccurred, this, &ClientGroup2::onServerGroup2ConnectedError);
}

void ClientGroup2::connectToServerGroup2(const QString &ip, int port)
{
    if (socketGroup2->state() == QAbstractSocket::UnconnectedState)
    {
        emit connectionStatusChangedGroup2("正在连接课题二服务器");
        socketGroup2->connectToHost(ip, port);
    }
    else if (socketGroup2->state() == QAbstractSocket::ConnectingState)
    {
        emit connectionStatusChangedGroup2("正在连接课题二服务器中，请稍后...");
    }
}

//客户端向服务器端发送数据，size是数据个数
void ClientGroup2::clientGroup2Senddata(uint16_t *data, int size)
{
    if (socketGroup2->state() == QAbstractSocket::ConnectedState)
    {
        QByteArray byteArray;
        QDataStream stream(&byteArray, QIODevice::WriteOnly);

        for (int i = 0; i < size; ++i)
        {
            stream << data[i]; // 发送数据
        }
        socketGroup2->write(byteArray); // 发送序列化的字节数组
    }
}

void ClientGroup2::onServerGroup2Connected()
{
    emit connectionStatusChangedGroup2("课题二服务器已连接");
    retryConnectTimerGroup2->stop();
}

void ClientGroup2::onServerGroup2Disconnected()
{
    emit connectionStatusChangedGroup2("课题二服务器断开连接");
    qDebug() << "Server disconnected";  // 添加调试信息
    // 尝试重新连接,3000ms连一次
    retryConnectTimerGroup2->start(2000);
}

void ClientGroup2::onServerGroup2ConnectedError(QAbstractSocket::SocketError socketError)
{
    Q_UNUSED(socketError);//未使用socketError，防止编译器警告
    lastErrorMessageGroup2 = socketGroup2->errorString();
    emit connectionStatusChangedGroup2(QString("课题二服务器连接失败，原因: %1").arg(lastErrorMessageGroup2));
    // 尝试重新连接,3000ms连一次
    retryConnectTimerGroup2->start(2000);
}

void ClientGroup2::retryConnectToServerGroup2()
{
    if (socketGroup2->state() != QAbstractSocket::ConnectedState)
    {
        // 这里尝试再次连接
        connectToServerGroup2(IP_Group2, PORT_Group2);
    }
}
