#include "mainwindow.h"
#include <QFile>
#include <QTextStream>
#include <QDebug>
#include <QVBoxLayout>
#include <QThread>
#include <QPixmap>
#include <sys/file.h>
#include <QDateTime>
#include <sys/time.h>
#include <zlib.h>
#include <cstdint>
#include <QtEndian>
//用于设置屏幕大小的头文件
#include <QGuiApplication>
#include <QScreen>
#include "image.h"

#define ARM 1//ARM为1时，使用开发板屏幕大小显示

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent),
    clientGroup2(new ClientGroup2(this)),
    clientAliyun(new ClientAliyun(this)),
    turntableUart(new TurntableUart("/dev/ttyS3", this)),//转台使用的是串口3
    motorUart(new MotorUart("/dev/ttyS4", this))//电机调焦用的是串口4
{
    QList <QScreen *> list_screen =  QGuiApplication::screens();
    /* 如果是ARM平台，直接设置大小为屏幕的大小 */
#if ARM
    this->resize(list_screen.at(0)->geometry().width(),
                 list_screen.at(0)->geometry().height());
#else
    /* 否则则设置主窗体大小为800x480 */
    this->resize(400, 480);
#endif

    /*服务器连接部分*/
    /*课题二服务器*/
    //初始化服务器连接状态标签
    serverGroup2ConnectStatusLabel = new QLabel("正在连接课题2服务器...", this);
    serverGroup2ConnectStatusLabel->setStyleSheet("font-size: 15px; color: black;");
    //初始化发送数据的定时器
    sendDataToServerGroup2Timer = new QTimer(this);

    /*阿里云服务器*/
    //初始化服务器连接状态标签
    serverAliyunConnectStatusLabel = new QLabel("正在连接阿里云服务器...", this);
    serverAliyunConnectStatusLabel->setStyleSheet("font-size: 15px; color: black;");
    //初始化发送数据的定时器
    sendDataToServerAliyunTimer = new QTimer(this);


    /*成像部分*/
    // 初始化图像标签
    imageLabel = new QLabel(this);
    imageLabel->setAlignment(Qt::AlignCenter);
    imageLabel->setStyleSheet("background-color: lightgrey;"); // 设置标签背景色
    imageLabel->setFixedSize(900, 900);//标签大小要与图像大小适配
    // 初始化读取文件并成像的定时器
    readFileAndImageTimer = new QTimer(this);

    /*转台部分*/
    //转台串口状态标签
    turntableUartStatusLabel = new QLabel("云台串口未打开", this);

    /*电机调焦部分*/
    //电机调焦串口状态标签
    motorUartStatusLabel = new QLabel("调焦串口未打开", this);

    /*布局设计*/
    //将成像标签和服务器连接状态标签、云台串口状态标签放到一个垂直布局中
    MainVerLayout = new QVBoxLayout;
    MainVerLayout->addWidget(imageLabel);
    MainVerLayout->addWidget(serverGroup2ConnectStatusLabel);
    MainVerLayout->addWidget(serverAliyunConnectStatusLabel);
    MainVerLayout->addWidget(turntableUartStatusLabel);
    MainVerLayout->addWidget(motorUartStatusLabel);
    MainVerWidget = new QWidget();
    MainVerWidget->setLayout(MainVerLayout);
    // 创建一个中心部件
    QWidget *centralWidget = new QWidget(this);
    setCentralWidget(centralWidget); // 将中心部件设置为窗口的中央部件
    // 创建布局
    QVBoxLayout *layout = new QVBoxLayout(centralWidget);
    // 将标签添加到布局并设置居中
    layout->addWidget(MainVerWidget, 0, Qt::AlignCenter); // 0表示该控件的拉伸因子为0，防止占据空间
    layout->setAlignment(MainVerWidget, Qt::AlignCenter); // 使标签在布局中居中
    // 将布局设置到中心部件
    centralWidget->setLayout(layout);


    //连接信号与槽
    connect(clientGroup2, &ClientGroup2::connectionStatusChangedGroup2, this, &MainWindow::updateServerGroup2ConnectionStatus);
    connect(clientAliyun, &ClientAliyun::connectionStatusChangedAliyun, this, &MainWindow::updateServerAliyunConnectionStatus);
    connect(sendDataToServerGroup2Timer, &QTimer::timeout, this, &MainWindow::sendDataToServerGroup2);
    connect(sendDataToServerAliyunTimer, &QTimer::timeout, this, &MainWindow::sendDataToServerAliyun);
    connect(clientAliyun, &ClientAliyun::serverAliyunDataReceived, this, &MainWindow::handleReceivedServerAliyunData); // 连接接收数据的信号(只有阿里云服务器会发送数据)
    connect(readFileAndImageTimer, &QTimer::timeout, this, &MainWindow::updateImage);//定时读取文件数据并成像

    readFileAndImageTimer->start(50); // 每隔1秒触发一次成像定时器

    //连接课题二服务器
    clientGroup2->connectToServerGroup2(clientGroup2->IP_Group2, clientGroup2->PORT_Group2);
    //连接阿里云服务器
    clientAliyun->connectToServerAliyun(clientAliyun->IP_Aliyun, clientAliyun->PORT_Aliyun);

    //打开云台串口（串口3）
    if (!turntableUart->openTurntableSerialPort())
    {
        turntableUartStatusLabel->setText("云台串口打开失败");
    }
    else
    {
        turntableUartStatusLabel->setText("云台串口已打开");
    }
    //打开电机串口（串口4）
    if (!motorUart->openMotorSerialPort())
    {
        motorUartStatusLabel->setText("调焦串口打开失败");
    }
    else
    {
        motorUartStatusLabel->setText("调焦串口已打开");
    }
}

MainWindow::~MainWindow() {}

//定时读取文件数据并成像
void MainWindow::updateImage()
{
    // 使用 ImageProcessor中的processImage函数处理图像
    QImage image = imageProcessor.processImage(imageProcessor.imageFilePath);
    if (!image.isNull())
    {
        //显示图像
        imageLabel->setPixmap(QPixmap::fromImage(image).scaled(900, 900, Qt::KeepAspectRatio));//这里设置图像大小
    }
    //qDebug() << "更新图像";
}

//更新Group2服务器连接状态
void MainWindow::updateServerGroup2ConnectionStatus(const QString &status)
{
    serverGroup2ConnectStatusLabel->setText(status);

    if (status == "课题二服务器已连接")
    {
        sendDataToServerGroup2Timer->start(10); // 连接成功后开始定时发送数据,50ms发送一次
    }
    else
    {
        sendDataToServerGroup2Timer->stop(); // 连接失败或断开时停止定时器
    }
}

//更新阿里云服务器连接状态
void MainWindow::updateServerAliyunConnectionStatus(const QString &status)
{
    serverAliyunConnectStatusLabel->setText(status);

    if (status == "阿里云服务器已连接")
    {
        sendDataToServerAliyunTimer->start(50); // 连接成功后开始定时发送数据,50ms发送一次
    }
    else
    {
        sendDataToServerAliyunTimer->stop(); // 连接失败或断开时停止定时器
    }
}

//向课题二服务器发送数据（这里读取的文件中有Frame=0,1,2...）
/******这里适配课题2******/
void MainWindow::sendDataToServerGroup2()
{
    // 文件操作部分
    const int totalFrames = 20;        // PF32数据共20帧
    const int dataPerFrame = 32 * 32;  // 每帧数据32*32个
    QVector<uint16_t> fileData(totalFrames * dataPerFrame); // 存放PF32数据的数组
    int dataIndex = 0;
    QFile dataFile(imageProcessor.imageFilePath);

    // 循环读取20次
    for (int frameCount = 0; frameCount < totalFrames; frameCount++) {
        if (!dataFile.open(QIODevice::ReadOnly))
        {
            qDebug() << "[Send] Failed to open data file:" << dataFile.errorString();
            return;
        }

        // 加文件锁
        int fd = dataFile.handle();
        if (flock(fd, LOCK_SH) != 0)
        {
            qDebug() << "[Send] File lock failed:" << strerror(errno);
            dataFile.close();
            return;
        }

        QTextStream stream(&dataFile);
        QString line1 = stream.readLine().trimmed();
        QString line2 = stream.readLine().trimmed();

        // 检查文件格式是否正确
        if (line1 != QString("Frame=0") || line2.isEmpty())
        {
            qDebug() << "[Send] Invalid file format in reading frame" << frameCount;
            flock(fd, LOCK_UN);
            dataFile.close();
            return;
        }

        // 解析数据行
        QStringList dataList = line2.split(' ', Qt::SkipEmptyParts);
        if (dataList.size() != dataPerFrame)
        {
            qDebug() << "[Send] Invalid data count in frame" << frameCount
                     << "Expected:" << dataPerFrame << "Got:" << dataList.size();
            flock(fd, LOCK_UN);
            dataFile.close();
            return;
        }

        // 转换数据
        bool conversionOK = true;
        for (int i = 0; i < dataPerFrame; ++i) {
            bool ok;
            int value = dataList[i].toInt(&ok);
            if ((!ok) || (value < 0) || (value > 65535)) {
                qDebug() << "[Send] Invalid value at frame" << frameCount
                         << "index" << i << ":" << dataList[i];
                conversionOK = false;
                break;
            }
            fileData[dataIndex++] = static_cast<uint16_t>(value);
        }

        // 解锁并关闭文件
        flock(fd, LOCK_UN);
        dataFile.close();

        if (!conversionOK) {
            return;
        }

        // 如果不是最后一次读取，等待50ms
        if (frameCount < totalFrames - 1) {
            QEventLoop loop;
            QTimer::singleShot(50, &loop, &QEventLoop::quit);
            loop.exec();
        }
    }

    if (dataIndex != totalFrames * dataPerFrame)
    {
        qDebug() << "[Send] Data incomplete. Read" << (dataIndex / dataPerFrame) << "/20 frames";
        return;
    }

    //这三个数组用于接收光电转台数据
    uint16_t azimuthBuffer[8]={0};
    uint16_t elevationBuffer[8]={0};
    uint16_t velocityBuffer[8]={0};

    // 从 TurntableUart 获取数据，存到临时缓冲区
    const uint16_t *buffer1 = turntableUart->getAzimuthBuffer();
    const uint16_t *buffer2 = turntableUart->getElevationBuffer();
    const uint16_t *buffer3 = turntableUart->getVelocityBuffer();

    for (int i = 0; i < 8; ++i)
    {
        azimuthBuffer[i] = buffer1[i]; // 将数据复制到本地数组
    }
    for (int i = 0; i < 8; ++i)
    {
        elevationBuffer[i] = buffer2[i]; // 将数据复制到本地数组
    }
    for (int i = 0; i < 8; ++i)
    {
        velocityBuffer[i] = buffer3[i]; // 将数据复制到本地数组
    }

    // 数据结构组装（这里不需要对sendArray进行互斥锁保护，因为写入数组的过程和发送是顺序执行的）
    const int startCodeSize = 2; //起始码2个数据
    const int timestampSize = 8;  //时间戳8个数据
    const int fileDataSize = totalFrames * dataPerFrame; // PF32数据20480个数据
    const int globalArraysSize = 8 * 3;                  // 光电转台24个数据
    const int crcSize = 2; //CRC校验码2个数据
    const int totalSize = startCodeSize + timestampSize + fileDataSize + globalArraysSize + crcSize; //总的数据个数

    QVector<uint16_t> sendArray(totalSize); //要发送到服务器的数组
    int index = 0; //数组下标

    // 1. 起始码
    sendArray[index++] = 1234;
    sendArray[index++] = 5678;

    // 2. 时间戳
    QDateTime now = QDateTime::currentDateTime();
    QDate date = now.date();
    QTime time = now.time();
    struct timeval tv;
    gettimeofday(&tv, nullptr);

    sendArray[index++] = date.year();
    sendArray[index++] = date.month();
    sendArray[index++] = date.day();
    sendArray[index++] = time.hour();
    sendArray[index++] = time.minute();
    sendArray[index++] = time.second();
    sendArray[index++] = tv.tv_usec & 0xFFFF;        // 微秒低16位
    sendArray[index++] = (tv.tv_usec >> 16) & 0x0F;  // 微秒高4位（最大999999=0xF423F）

    // 3. 文件数据
    memcpy(sendArray.data() + index, fileData.constData(), fileDataSize * sizeof(uint16_t));
    index += fileDataSize;

    // 4. 云台数组
    for (int i = 0; i < 8; i++) sendArray[index++] = azimuthBuffer[i];
    for (int i = 0; i < 8; i++) sendArray[index++] = elevationBuffer[i];
    for (int i = 0; i < 8; i++) sendArray[index++] = velocityBuffer[i];

    // 5. CRC校验
    QByteArray crcData(reinterpret_cast<const char*>(sendArray.constData()), (totalSize - crcSize) * sizeof(uint16_t));
    uint32_t crc = crc32(0L, reinterpret_cast<const Bytef*>(crcData.constData()), crcData.size());
    sendArray[index++] = static_cast<uint16_t>((crc >> 16) & 0xFFFF);
    sendArray[index++] = static_cast<uint16_t>(crc & 0xFFFF);

    // 向服务器发送数据
    // 在发送之前对sendArray的数据进行字节序转换
    for (int i = 0; i < totalSize; ++i) {
        sendArray[i] = qToBigEndian(sendArray[i]);
    }

    clientGroup2->clientGroup2Senddata(sendArray.data(), totalSize);
}

//向阿里云服务器发送数据
// void MainWindow::sendDataToServerAliyun()
// {
//     //缓冲区用于存储要发送给服务器端的数据
//     static uint16_t sendMessageArray[1024] = {0};
//     // 打开数据文件
//     QFile dataFile(imageProcessor.imageFilePath);
//     if (!dataFile.open(QIODevice::ReadOnly))
//     {
//         qDebug() << "[Send] Failed to open data file! Error:" << dataFile.errorString();
//         return;
//     }
//     //加文件锁
//     int fd = dataFile.handle();
//     if (flock(fd, LOCK_SH) != 0)
//     {  // 获取共享锁
//         qDebug() << "[Send] File lock failed with error:" << strerror(errno);
//         dataFile.close();
//         return;
//     }

//     QTextStream stream(&dataFile);
//     //读取文本数据，下面两行针对的是文件中数据只有32*32个数据，没有Frame=0
//     /*
//     QString rawData = stream.readAll();
//     QStringList dataList = rawData.split(" ", Qt::SkipEmptyParts);
//     */

//     //读取文本数据，下面针对的是文件中数据有Frame=0，和32*32个数据
//     // 读取并忽略第一行（Frame=0）
//     QString frameLine = stream.readLine();
//     if (!frameLine.startsWith("Frame=")) // 可选的检查
//     {
//         qDebug() << "[Send] Invalid frame line!" << frameLine;
//         flock(fd, LOCK_UN);  // 关闭文件之前解锁文件
//         dataFile.close();
//         return;
//     }
//     // 读取并存储第二行数据
//     QString rawDataLine = stream.readLine(); // 读取第二行包含32*32个数据
//     QStringList dataList = rawDataLine.split(" ", Qt::SkipEmptyParts);

//     // 数据有效性检查
//     if (dataList.size() < 1024)
//     {
//         qDebug() << "[Send] Insufficient data:" << dataList.size() << "/1024";
//         flock(fd, LOCK_UN);  //关闭文件之前解锁文件
//         dataFile.close();
//         return;
//     }

//     // 数据转换处理
//     bool conversionOK = true;
//     for (int i = 0; i < 1024; ++i)
//     {
//         bool ok;
//         int value = dataList[i].toInt(&ok);
//         // 检查转换状态和数值范围
//         if ((!ok) || (value < 0) || (value > 65535))
//         {
//             qDebug() << "[Send] Invalid data at index" << i << ":" << dataList[i];
//             conversionOK = false;
//             break;
//         }
//         sendMessageArray[i] = static_cast<uint16_t>(value);
//     }
//     //关闭文件之前解锁
//     flock(fd, LOCK_UN);
//     // 关闭文件（在作用域结束前显式关闭）
//     dataFile.close();

//     // 仅当数据有效时发送
//     if (conversionOK)
//     {
//         clientAliyun->clientSenddataAliyun(sendMessageArray, 1024);
//     }
// }

void MainWindow::sendDataToServerAliyun()
{
    //缓冲区用于存储要发送给服务器端的数据
    static uint16_t sendMessageArray[1024] = {0};
    // 新数组，加入起始码
    uint16_t sendMessageWithHeader[1026] = {0}; // 1024数据+2起始码

    // 打开数据文件
    QFile dataFile(imageProcessor.imageFilePath);
    if (!dataFile.open(QIODevice::ReadOnly))
    {
        qDebug() << "[Send] Failed to open data file! Error:" << dataFile.errorString();
        return;
    }

    //加文件锁
    int fd = dataFile.handle();
    if (flock(fd, LOCK_SH) != 0)
    {  // 获取共享锁
        qDebug() << "[Send] File lock failed with error:" << strerror(errno);
        dataFile.close();
        return;
    }

    QTextStream stream(&dataFile);
    //读取文本数据，下面两行针对的是文件中数据只有32*32个数据，没有Frame=0
    /*
    QString rawData = stream.readAll();
    QStringList dataList = rawData.split(" ", Qt::SkipEmptyParts);
    */

    //读取文本数据，下面针对的是文件中数据有Frame=0，和32*32个数据
    // 读取并忽略第一行（Frame=0）
    QString frameLine = stream.readLine();
    if (!frameLine.startsWith("Frame="))
    {
        qDebug() << "[Send] Invalid frame line!" << frameLine;
        flock(fd, LOCK_UN);
        dataFile.close();
        return;
    }
    // 读取并存储第二行数据
    QString rawDataLine = stream.readLine(); // 读取第二行包含32*32个数据
    QStringList dataList = rawDataLine.split(" ", Qt::SkipEmptyParts);

    // 数据有效性检查
    if (dataList.size() < 1024)
    {
        qDebug() << "[Send] Insufficient data:" << dataList.size() << "/1024";
        flock(fd, LOCK_UN);
        dataFile.close();
        return;
    }

    // 数据转换处理
    bool conversionOK = true;
    for (int i = 0; i < 1024; ++i)
    {
        bool ok;
        int value = dataList[i].toInt(&ok);
        if ((!ok) || (value < 0) || (value > 65535))
        {
            qDebug() << "[Send] Invalid data at index" << i << ":" << dataList[i];
            conversionOK = false;
            break;
        }
        sendMessageArray[i] = static_cast<uint16_t>(value);
    }

    // 解锁文件
    flock(fd, LOCK_UN);
    dataFile.close();

    if (conversionOK)
    {
        // 在前面加入起始码
        sendMessageWithHeader[0] = 1234;
        sendMessageWithHeader[1] = 5678;

        // 复制读取到的数据到新数组，从第3个位置开始
        for (int i = 0; i < 1024; ++i)
        {
            sendMessageWithHeader[i + 2] = sendMessageArray[i];
        }

        // 发送带有起始码的数据
        clientAliyun->clientSenddataAliyun(sendMessageWithHeader, 1026);
    }
}

//处理服务端发来的数据（服务端发来的数据都是uint8_t类型）（控制镜头调焦的指令）
void MainWindow::handleReceivedServerAliyunData(const QByteArray &data)
{
    // 处理接收到的数据
    qDebug() << "接收到服务器数据:" << data; // 打印接收到的数据
    //将服务器发来的数据转发给调焦串口
    if(data.size() == 6 && static_cast<unsigned char>(data[0]) == 0xFF && static_cast<unsigned char>(data[1]) == 0x02)
    {
        motorUart->sendMotorUartData(data);
    }
}
