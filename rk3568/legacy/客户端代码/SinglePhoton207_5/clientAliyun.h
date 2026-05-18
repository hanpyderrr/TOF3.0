#ifndef CLIENTALIYUN_H
#define CLIENTALIYUN_H

#include <QObject>
#include <QTcpSocket>
#include <QTimer>
#include <QString>
#include <QDataStream>

class ClientAliyun : public QObject {
    Q_OBJECT

public:
    explicit ClientAliyun(QObject *parent = nullptr);
    void connectToServerAliyun(const QString &ip, int port);//连接服务器的函数
    void clientSenddataAliyun(uint16_t *data, int size);//用于客户端向服务器发送数据

    //服务器相关信息：地址和端口号
    QString IP_Aliyun = "123.57.89.44";//阿里云服务器
    uint16_t PORT_Aliyun = 8000;//阿里云服务器端口

signals:
    void connectionStatusChangedAliyun(const QString &status);  //连接状态改变时相应函数会向mainwindow发送这个信号，信号中包含了相应的状态
    void serverAliyunDataReceived(const QByteArray &data); // 服务器数据接收信号，接收到服务器端数据时会向mainwindow发送这个信号，信号中包含了服务端发送的数据

private slots:
    void onServerAliyunConnected();//服务器连接成功时触发该槽函数
    void onServerAliyunDisconnected();//服务器断开连接时触发该槽函数
    void onServerAliyunConnectedError(QAbstractSocket::SocketError socketError);//连接出错时触发该槽函数
    void retryConnectToServerAliyun();//定时重新连接服务器的槽函数
    void onServerAliyunDataRead(); // 收到服务端数据时触发该槽函数，处理接收到的数据（即向mianwindow发送serverDataReceived信号）

private:
    QTcpSocket *socketAliyun;
    QTimer *retryConnectTimerAliyun;
    QString lastErrorMessageAliyun;

};


#endif // CLIENTALIYUN_H
