#ifndef SERVER_H
#define SERVER_H

#include <QObject>
#include <QTcpServer>
#include <QTcpSocket>

class Server : public QObject
{
    Q_OBJECT

public:
    explicit Server(QObject *parent = nullptr);
    void connectToClient();//开启监听，连接服务器
    void disconnectFromClient();//断开与客户端的连接
    void serverSendMessage(uint8_t *data, int size);//向客户端发送数据

    //服务器相关信息：地址和端口号
    QString IP = "192.168.31.197";
    uint16_t PORT = 8000;

signals:
    void clientDataReceived(const QByteArray &data);//接收到客户端发送的数据后发送此信号给mainwindow
    void clientConnectionStatusUpdated(const QString &status);//服务端与客户端的连接状态发生改变后发送此信号给mainwindow

private slots:
    void onClientConnected();//与客户端连接成功时触发该槽函数
    void onClientDisconnected();//与客户端断开连接时触发该槽函数
    void onClientConnectedError(QAbstractSocket::SocketError socketError);//连接出错时触发该槽函数
    void handleNewClientConnection();//处理新的客户端连接
    void clientDataRead();//客户端发来信息后自动调用此槽函数，该槽函数会发送对应信号

private:
    QTcpServer *tcpServer;
    QTcpSocket *clientSocket;
};

#endif // SERVER_H
