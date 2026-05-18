#ifndef CLIENTGROUP2_H
#define CLIENTGROUP2_H

#include <QObject>
#include <QTcpSocket>
#include <QTimer>
#include <QString>
#include <QDataStream>

class ClientGroup2 : public QObject {
    Q_OBJECT

public:
    explicit ClientGroup2(QObject *parent = nullptr);
    void connectToServerGroup2(const QString &ip, int port);//连接服务器的函数
    void clientGroup2Senddata(uint16_t *data, int size);//用于客户端向服务器发送数据

    //服务器相关信息：地址和端口号
    QString IP_Group2 = "202.207.248.104";//课题2服务器
    uint16_t PORT_Group2 = 24100;
    // QString IP_Group2 = "39.105.73.165";//课题2服务器
    // uint16_t PORT_Group2 = 8000;

signals:
    void connectionStatusChangedGroup2(const QString &status);  //连接状态改变时相应函数会向mainwindow发送这个信号，信号中包含了相应的状态

private slots:
    void onServerGroup2Connected();//服务器连接成功时触发该槽函数
    void onServerGroup2Disconnected();//服务器断开连接时触发该槽函数
    void onServerGroup2ConnectedError(QAbstractSocket::SocketError socketError);//连接出错时触发该槽函数
    void retryConnectToServerGroup2();//定时重新连接服务器的槽函数


private:
    QTcpSocket *socketGroup2;
    QTimer *retryConnectTimerGroup2;
    QString lastErrorMessageGroup2;

};


#endif // CLIENTGROUP2_H
