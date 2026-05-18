#include "server.h"
#include <QDebug>

Server::Server(QObject *parent)
    : QObject(parent), tcpServer(new QTcpServer(this)), clientSocket(nullptr)
{
    connect(tcpServer, &QTcpServer::newConnection, this, &Server::handleNewClientConnection);
    connect(tcpServer, &QTcpServer::acceptError, this, &Server::onClientConnectedError); // 捕获连接错误
}

void Server::connectToClient()
{
    // 启动服务器，监听特定的IP地址和端口
    if (tcpServer->listen(QHostAddress(IP), PORT))
    {
        emit clientConnectionStatusUpdated("正在连接客户端...");
    }
    else
    {
        emit clientConnectionStatusUpdated("客户端连接失败: " + tcpServer->errorString());
    }
}

void Server::disconnectFromClient()
{
    if (clientSocket)
    {
        clientSocket->disconnectFromHost();
        clientSocket = nullptr;
    }
    tcpServer->close();
    emit clientConnectionStatusUpdated("客户端未连接");
}

void Server::handleNewClientConnection()
{
    clientSocket = tcpServer->nextPendingConnection();

    connect(clientSocket, &QTcpSocket::readyRead, this, &Server::clientDataRead);
    connect(clientSocket, &QTcpSocket::disconnected, this, &Server::onClientDisconnected);

    emit clientConnectionStatusUpdated("客户端已连接");
}

void Server::clientDataRead()
{
    if (clientSocket)
    {
        QByteArray data = clientSocket->readAll();
        emit clientDataReceived(data);
    }
}


void Server::onClientDisconnected()
{
    if (clientSocket)
    {
        clientSocket->deleteLater();
        clientSocket = nullptr;
    }
    emit clientConnectionStatusUpdated("客户端未连接");
}

void Server::onClientConnected()
{
    // 当客户端成功连接时的逻辑
    if (clientSocket)
    {
        emit clientConnectionStatusUpdated(QString("客户端已连接: %1").arg(clientSocket->peerAddress().toString()));
    }
}

void Server::onClientConnectedError(QAbstractSocket::SocketError socketError)
{
    // 处理连接错误
    emit clientConnectionStatusUpdated(QString("连接错误: %1").arg(socketError));
}

void Server::serverSendMessage(uint8_t *data, int size)
{
    if (clientSocket && clientSocket->state() == QAbstractSocket::ConnectedState)
    {
        QByteArray message;
        for (int i = 0; i < size; ++i)
        {
            message.append(static_cast<char>(data[i]));
        }
        clientSocket->write(message);
    }
    else
    {
        qDebug()<<"未连接服务器，发送失败";
    }
}
