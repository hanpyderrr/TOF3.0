#include "clientAliyun.h"
#include "mainwindow.h"
#include <QDebug>
#include <QHostAddress>

ClientAliyun::ClientAliyun(QObject *parent) : QObject(parent), socketAliyun(new QTcpSocket(this))
{
    //初始化重连定时器
    retryConnectTimerAliyun = new QTimer(this);

    connect(retryConnectTimerAliyun, &QTimer::timeout, this, &ClientAliyun::retryConnectToServerAliyun);
    connect(socketAliyun, &QTcpSocket::connected, this, &ClientAliyun::onServerAliyunConnected);
    connect(socketAliyun, &QTcpSocket::disconnected, this, &ClientAliyun::onServerAliyunDisconnected);
    connect(socketAliyun, &QTcpSocket::errorOccurred, this, &ClientAliyun::onServerAliyunConnectedError);
    connect(socketAliyun, &QTcpSocket::readyRead, this, &ClientAliyun::onServerAliyunDataRead); // 连接接收数据的信号
}

void ClientAliyun::connectToServerAliyun(const QString &ip, int port)
{
    if (socketAliyun->state() == QAbstractSocket::UnconnectedState)
    {
        emit connectionStatusChangedAliyun("正在连接阿里云服务器");
        socketAliyun->connectToHost(ip, port);
    }
    else if (socketAliyun->state() == QAbstractSocket::ConnectingState)
    {
        emit connectionStatusChangedAliyun("阿里云服务器正在连接中，请稍后...");
    }
}

//客户端向服务器端发送数据，size是数据个数
void ClientAliyun::clientSenddataAliyun(uint16_t *data, int size)
{
    if (socketAliyun->state() == QAbstractSocket::ConnectedState)
    {
        QByteArray byteArray;
        QDataStream stream(&byteArray, QIODevice::WriteOnly);

        for (int i = 0; i < size; ++i)
        {
            stream << data[i]; // 发送数据
        }
        socketAliyun->write(byteArray); // 发送序列化的字节数组
    }
}

void ClientAliyun::onServerAliyunConnected()
{
    emit connectionStatusChangedAliyun("阿里云服务器已连接");
    retryConnectTimerAliyun->stop();
}

void ClientAliyun::onServerAliyunDisconnected()
{
    emit connectionStatusChangedAliyun("阿里云服务器断开连接");
    qDebug() << "Aliyun server disconnected";  // 添加调试信息
    // 尝试重新连接,500ms连一次
    retryConnectTimerAliyun->start(500);
}

void ClientAliyun::onServerAliyunConnectedError(QAbstractSocket::SocketError socketError)
{
    Q_UNUSED(socketError);//未使用socketError，防止编译器警告
    lastErrorMessageAliyun = socketAliyun->errorString();
    emit connectionStatusChangedAliyun(QString("阿里云服务器连接失败，原因: %1").arg(lastErrorMessageAliyun));
    // 尝试重新连接,500ms连一次
    retryConnectTimerAliyun->start(500);
}

void ClientAliyun::retryConnectToServerAliyun()
{
    if (socketAliyun->state() != QAbstractSocket::ConnectedState)
    {
        // 这里尝试再次连接
        connectToServerAliyun(IP_Aliyun, PORT_Aliyun);
    }
}

void ClientAliyun::onServerAliyunDataRead()
{
    QByteArray receivedData = socketAliyun->readAll(); // 读取所有可用的数据
    emit serverAliyunDataReceived(receivedData); // 发射信号通知mainwindow数据已接收
}
