#include "mainwindow.h"
#include <QVBoxLayout>
#include <QWidget>
#include <QDebug>
#include <QTimer>
#include <QDoubleValidator>
#include <QFile>
#include <QTextStream>
#include <QMessageBox>


MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), server(new Server(this)),turntable(new Turntable(this)), motor(new Motor(this))
{
    //设置主窗体大小
    this->resize(700, 700);

    /***成像部分***/
    // 初始化图像标签
    imageLabel = new QLabel(this);
    imageLabel->setFixedSize(300, 300); //设置图像标签尺寸（要与主窗口大小相适应）
    imageLabel->setStyleSheet("background-color: white;");//改变标签背景颜色
    //初始化“开始成像”与“停止成像”按钮
    startImageButton = new QPushButton("开始成像", this);
    startImageButton->setEnabled(true);
    stopImageButton = new QPushButton("停止成像", this);
    stopImageButton->setEnabled(false);//按钮初始状态不可用
    //初始化“保存数据”按钮
    receiveDataToFileButton = new QPushButton("保存数据", this);
    receiveDataToFileButton->setEnabled(true);

    /***调焦部分***/
    //用于提示调焦功能的标签
    lensAdjustFocusFunctionLabel = new QLabel("镜头调焦", this);
    //用于提示向前调焦功能的标签
    lensForwardAdjustFocusFunctionLabel = new QLabel("前", this);
    //用于控制镜头向前调焦的按钮
    lensForwardAdjustFocusRoughlyButton = new QPushButton("粗调", this);
    lensForwardAdjustFocusRoughlyButton->setFixedSize(100, 30);//设置按钮大小
    lensForwardAdjustFocusFinelyButton = new QPushButton("微调", this);
    lensForwardAdjustFocusFinelyButton->setFixedSize(100, 30);//设置按钮大小
    //用于提示向后调焦功能的标签
    lensBackAdjustFocusFunctionLabel = new QLabel("后", this);
    //用于控制镜头向后调焦的按钮
    lensBackAdjustFocusRoughlyButton = new QPushButton("粗调", this);
    lensBackAdjustFocusRoughlyButton->setFixedSize(100, 30);//设置按钮大小
    lensBackAdjustFocusFinelyButton = new QPushButton("微调", this);
    lensBackAdjustFocusFinelyButton->setFixedSize(100, 30);//设置按钮大小
    //用于提示对焦功能的标签
    lensFocusingFunctionLabel = new QLabel("镜头对焦", this);
    //用于提示向左对焦功能的标签
    lensLeftFocusingFunctionLabel = new QLabel("左", this);
    //用于控制镜头向左对焦的按钮
    lensLeftFocusingRoughlyButton = new QPushButton("粗调", this);
    lensLeftFocusingRoughlyButton->setFixedSize(100, 30);//设置按钮大小
    lensLeftFocusingFinelyButton = new QPushButton("微调", this);
    lensLeftFocusingFinelyButton->setFixedSize(100, 30);//设置按钮大小
    //用于提示向右对焦功能的标签
    lensRightFocusingFunctionLabel = new QLabel("右", this);
    //用于控制镜头向右对焦的按钮
    lensRightFocusingRoughlyButton = new QPushButton("粗调", this);
    lensRightFocusingRoughlyButton->setFixedSize(100, 30);//设置按钮大小
    lensRightFocusingFinelyButton = new QPushButton("微调", this);
    lensRightFocusingFinelyButton->setFixedSize(100, 30);//设置按钮大小

    /***服务器与客户端连接的控件***/
    //初始化客户端连接状态标签
    clientConnectionStatus = new QLabel("客户端未连接", this);
    //客户端连接的按钮
    connectClientButton = new QPushButton("连接客户端", this);
    connectClientButton->setEnabled(true);
    disconnectClientButton = new QPushButton("断开客户端", this);
    disconnectClientButton->setEnabled(false);//按钮初始状态不可用

    /***转台控制部分控件***/
    //云台定位速度设置提示标签
    setTurntablePositionSpeedLabel = new QLabel("定位速度", this);
    //云台定位速度设置控件
    setTurntablePositionSpeedComboBox = new QComboBox(this);
    for(int i = 1; i <= 60; i++)
    {
        setTurntablePositionSpeedComboBox->addItem(QString::number(i));
    }
    setTurntablePositionSpeedComboBox->setCurrentText("32");
    setTurntablePositionSpeedComboBox->setFixedWidth(80); // 设置固定宽度为 80 像素
    //云台定位速度设置确定按钮
    setTurntablePositionSpeedButton = new QPushButton("确定", this);
    //云台控制速度设置提示标签
    setTurntableControlSpeedLabel = new QLabel("控制速度", this);
    //云台控制速度设置控件
    setTurntableControlSpeedComboBox = new QComboBox(this);
    for(int i = 1; i <= 60; i++)
    {
        setTurntableControlSpeedComboBox->addItem(QString::number(i));
    }
    setTurntableControlSpeedComboBox->setCurrentText("32");
    setTurntableControlSpeedComboBox->setFixedWidth(80); // 设置固定宽度为 80 像素
    //云台“上下左右”控制按钮
    upTurntableButton = new QPushButton("上", this);
    upTurntableButton->setFixedSize(70, 30);//设置按钮大小
    downTurntableButton = new QPushButton("下", this);
    downTurntableButton->setFixedSize(70, 30);//设置按钮大小
    leftTurntableButton = new QPushButton("左", this);
    leftTurntableButton->setFixedSize(70, 30);//设置按钮大小
    rightTurntableButton = new QPushButton("右", this);
    rightTurntableButton->setFixedSize(70, 30);//设置按钮大小
    //水平角和俯仰角显示标签
    yawAngleDisplayLabel = new QLabel;
    pitchAngleDisplayLabel = new QLabel;
    yawAngleDisplayLabel->setStyleSheet("background-color: white;");//改变标签背景颜色
    pitchAngleDisplayLabel->setStyleSheet("background-color: white;");
    //水平角和俯仰角提示标签
    yawAngleTipLabel = new QLabel("水平角(0-360)", this);
    pitchAngleTipLabel = new QLabel("俯仰角(-60-60)", this);
    //水平角和俯仰角查询按钮
    queryTurntableYawAngleButton = new QPushButton("水平角查询", this);
    queryTurntableYawAngleButton->setFixedSize(140, 30);//设置按钮大小
    queryTurntablePitchAngleButton = new QPushButton("俯仰角查询", this);
    queryTurntablePitchAngleButton->setFixedSize(140, 30);//设置按钮大小

    //水平角和俯仰角编辑栏
    //水平角（限制输入的只能是0-360之间的保留了小数点后两位的数字，实际使用有问题，能超过360，需要额外判断）
    yawAngleLineEdit = new QLineEdit(this);
    QDoubleValidator *yawValidator = new QDoubleValidator(0.00, 360.00, 2, yawAngleLineEdit);
    yawValidator->setLocale(QLocale::English); // 强制使用点作为小数点
    yawValidator->setNotation(QDoubleValidator::StandardNotation); // 标准数字格式
    yawAngleLineEdit->setValidator(yawValidator); // 应用验证器
    //俯仰角（限制输入的只能是-60-60之间的保留了小数点后两位的数字，实际使用有问题，能超过-60和60，需要额外判断）
    pitchAngleLineEdit = new QLineEdit(this);
    QDoubleValidator *pitchValidator = new QDoubleValidator(-60.00, 60.00, 2, pitchAngleLineEdit);
    pitchValidator->setLocale(QLocale::English); // 强制使用点作为小数点
    pitchValidator->setNotation(QDoubleValidator::StandardNotation); // 标准数字格式
    pitchAngleLineEdit->setValidator(pitchValidator); // 应用验证器

    //水平角和俯仰角设置按钮
    setTurntableYawAngleButton = new QPushButton("水平角设置", this);
    setTurntableYawAngleButton->setFixedSize(140, 30);//设置按钮大小
    setTurntablePitchAngleButton = new QPushButton("俯仰角设置", this);
    setTurntablePitchAngleButton->setFixedSize(140, 30);//设置按钮大小

    /***布局部分***/
    //成像按钮，停止成像，保存数据按钮的水平设置，将三个按钮放到一个水平布局，然后放到一个水平容器
    ImageButtonHorLayout = new QHBoxLayout;
    ImageButtonHorLayout->addWidget(startImageButton);
    ImageButtonHorLayout->addWidget(stopImageButton);
    ImageButtonHorLayout->addWidget(receiveDataToFileButton);
    ImageButtonHorWidget= new QWidget();
    ImageButtonHorWidget->setLayout(ImageButtonHorLayout);

    //图像标签和成像按钮部件的垂直设置，将相关部件放到一个垂直布局，然后放到一个垂直容器
    ImageFunVerLayout = new QVBoxLayout;
    ImageFunVerLayout->addWidget(imageLabel);
    ImageFunVerLayout->addWidget(ImageButtonHorWidget);
    ImageFunVerWidget= new QWidget();
    ImageFunVerWidget->setLayout(ImageFunVerLayout);

    //向前调焦的标签，向前粗调焦按钮，向前微调焦按钮的水平设置
    LensForwardAdjustFocusHorLayout = new QHBoxLayout;
    LensForwardAdjustFocusHorLayout->addWidget(lensForwardAdjustFocusFunctionLabel);
    LensForwardAdjustFocusHorLayout->addWidget(lensForwardAdjustFocusRoughlyButton);
    LensForwardAdjustFocusHorLayout->addWidget(lensForwardAdjustFocusFinelyButton);
    LensForwardAdjustFocusHorWidget = new QWidget();
    LensForwardAdjustFocusHorWidget->setLayout(LensForwardAdjustFocusHorLayout);

    //向后调焦的标签，向后粗调焦按钮，向后微调焦按钮的水平设置
    LensBackAdjustFocusHorLayout = new QHBoxLayout;
    LensBackAdjustFocusHorLayout->addWidget(lensBackAdjustFocusFunctionLabel);
    LensBackAdjustFocusHorLayout->addWidget(lensBackAdjustFocusRoughlyButton);
    LensBackAdjustFocusHorLayout->addWidget(lensBackAdjustFocusFinelyButton);
    LensBackAdjustFocusHorWidget = new QWidget();
    LensBackAdjustFocusHorWidget->setLayout(LensBackAdjustFocusHorLayout);

    //向左对焦的标签，向左粗对焦按钮，向左微对焦按钮的水平设置
    LensLeftFocusingHorLayout = new QHBoxLayout;
    LensLeftFocusingHorLayout->addWidget(lensLeftFocusingFunctionLabel);
    LensLeftFocusingHorLayout->addWidget(lensLeftFocusingRoughlyButton);
    LensLeftFocusingHorLayout->addWidget(lensLeftFocusingFinelyButton);
    LensLeftFocusingHorWidget = new QWidget();
    LensLeftFocusingHorWidget->setLayout(LensLeftFocusingHorLayout);

    //向右对焦的标签，向右粗对焦按钮，向右微对焦按钮的水平设置
    LensRightFocusingHorLayout = new QHBoxLayout;
    LensRightFocusingHorLayout->addWidget(lensRightFocusingFunctionLabel);
    LensRightFocusingHorLayout->addWidget(lensRightFocusingRoughlyButton);
    LensRightFocusingHorLayout->addWidget(lensRightFocusingFinelyButton);
    LensRightFocusingHorWidget = new QWidget();
    LensRightFocusingHorWidget->setLayout(LensRightFocusingHorLayout);

    //调焦功能部分的垂直设置
    LensFocusingFunVerLayout = new QVBoxLayout;
    LensFocusingFunVerLayout->addWidget(lensAdjustFocusFunctionLabel);
    LensFocusingFunVerLayout->addWidget(LensForwardAdjustFocusHorWidget);
    LensFocusingFunVerLayout->addWidget(LensBackAdjustFocusHorWidget);
    LensFocusingFunVerLayout->addWidget(lensFocusingFunctionLabel);
    LensFocusingFunVerLayout->addWidget(LensLeftFocusingHorWidget);
    LensFocusingFunVerLayout->addWidget(LensRightFocusingHorWidget);
    LensFocusingFunVerWidget= new QWidget();
    LensFocusingFunVerWidget->setLayout(LensFocusingFunVerLayout);

    //左侧功能部分的垂直设置
    LeftFunVerLayout = new QVBoxLayout;
    LeftFunVerLayout ->addWidget(ImageFunVerWidget);
    LeftFunVerLayout ->addWidget(LensFocusingFunVerWidget);
    LeftFunVerWidget= new QWidget();
    LeftFunVerWidget->setLayout(LeftFunVerLayout);

    //连接客户端按钮与断开客户端按钮的水平设置，将两个按钮放到一个水平布局，然后放到一个水平容器
    ConnectClientButtonHorLayout = new QHBoxLayout;
    ConnectClientButtonHorLayout->addWidget(connectClientButton);
    ConnectClientButtonHorLayout->addWidget(disconnectClientButton);
    ConnectClientButtonHorWidget= new QWidget();
    ConnectClientButtonHorWidget->setLayout(ConnectClientButtonHorLayout);

    //定位速度标签、控件及确定按钮的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    PositionSpeedComponentHorLayout = new QHBoxLayout;
    PositionSpeedComponentHorLayout->addWidget(setTurntablePositionSpeedLabel);
    PositionSpeedComponentHorLayout->addWidget(setTurntablePositionSpeedComboBox);
    PositionSpeedComponentHorLayout->addWidget(setTurntablePositionSpeedButton);
    PositionSpeedComponentHorWidget= new QWidget();
    PositionSpeedComponentHorWidget->setLayout(PositionSpeedComponentHorLayout);

    //控制速度标签、控件的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    ControlSpeedComponentHorLayout = new QHBoxLayout;
    ControlSpeedComponentHorLayout->addWidget(setTurntableControlSpeedLabel);
    ControlSpeedComponentHorLayout->addWidget(setTurntableControlSpeedComboBox);
    addSpacer(ControlSpeedComponentHorLayout, 160, 0);//设置与右侧屏幕的水平间距
    ControlSpeedComponentHorWidget= new QWidget();
    ControlSpeedComponentHorWidget->setLayout(ControlSpeedComponentHorLayout);

    //云台上按钮的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    ControlUpButtonHorLayout = new QHBoxLayout;
    ControlUpButtonHorLayout->addWidget(upTurntableButton);
    ControlUpButtonHorWidget= new QWidget();
    ControlUpButtonHorWidget->setLayout(ControlUpButtonHorLayout);

    //云台左右按钮的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    ControlLeftAndRightButtonHorLayout = new QHBoxLayout;
    ControlLeftAndRightButtonHorLayout->addWidget(leftTurntableButton);
    ControlLeftAndRightButtonHorLayout->addWidget(rightTurntableButton);
    ControlLeftAndRightButtonHorWidget= new QWidget();
    ControlLeftAndRightButtonHorWidget->setLayout(ControlLeftAndRightButtonHorLayout);

    //云台下按钮的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    ControlDownButtonHorLayout = new QHBoxLayout;
    ControlDownButtonHorLayout->addWidget(downTurntableButton);
    ControlDownButtonHorWidget= new QWidget();
    ControlDownButtonHorWidget->setLayout(ControlDownButtonHorLayout);

    //云台上下左右转动按钮的垂直设置，将相关部件放到一个垂直布局，然后放到一个垂直容器
    ControlRotateButtonVerLayout = new QVBoxLayout;
    ControlRotateButtonVerLayout->addWidget(ControlUpButtonHorWidget);
    ControlRotateButtonVerLayout->addWidget(ControlLeftAndRightButtonHorWidget);
    ControlRotateButtonVerLayout->addWidget(ControlDownButtonHorWidget);
    ControlRotateButtonVerWidget= new QWidget();
    ControlRotateButtonVerWidget->setLayout(ControlRotateButtonVerLayout);

    //云台水平角查询部件的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    YawAngleQueryComponentHorLayout = new QHBoxLayout;
    YawAngleQueryComponentHorLayout->addWidget(yawAngleDisplayLabel);
    YawAngleQueryComponentHorLayout->addWidget(queryTurntableYawAngleButton);
    YawAngleQueryComponentHorWidget= new QWidget();
    YawAngleQueryComponentHorWidget->setLayout(YawAngleQueryComponentHorLayout);

    //云台俯仰角查询部件的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    PitchAngleQueryComponentHorLayout = new QHBoxLayout;
    PitchAngleQueryComponentHorLayout->addWidget(pitchAngleDisplayLabel);
    PitchAngleQueryComponentHorLayout->addWidget(queryTurntablePitchAngleButton);
    PitchAngleQueryComponentHorWidget= new QWidget();
    PitchAngleQueryComponentHorWidget->setLayout(PitchAngleQueryComponentHorLayout);

    //云台水平角设置部件的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    YawAngleSetComponentHorLayout = new QHBoxLayout;
    YawAngleSetComponentHorLayout->addWidget(yawAngleLineEdit);
    YawAngleSetComponentHorLayout->addWidget(setTurntableYawAngleButton);
    YawAngleSetComponentHorWidget= new QWidget();
    YawAngleSetComponentHorWidget->setLayout(YawAngleSetComponentHorLayout);

    //云台俯仰角设置部件的水平设置，将相关部件放到一个水平布局，然后放到一个水平容器
    PitchAngleSetComponentHorLayout = new QHBoxLayout;
    PitchAngleSetComponentHorLayout->addWidget(pitchAngleLineEdit);
    PitchAngleSetComponentHorLayout->addWidget(setTurntablePitchAngleButton);
    PitchAngleSetComponentHorWidget= new QWidget();
    PitchAngleSetComponentHorWidget->setLayout(PitchAngleSetComponentHorLayout);



    //右侧功能部分的垂直设置，将相关部件放到一个垂直布局，然后放到一个垂直容器
    RightFunVerLayout = new QVBoxLayout;
    RightFunVerLayout->addWidget(clientConnectionStatus);
    RightFunVerLayout->addWidget(ConnectClientButtonHorWidget);
    RightFunVerLayout->addWidget(ControlRotateButtonVerWidget);
    RightFunVerLayout->addWidget(ControlSpeedComponentHorWidget);
    RightFunVerLayout->addWidget(yawAngleTipLabel);
    RightFunVerLayout->addWidget(YawAngleSetComponentHorWidget);
    RightFunVerLayout->addWidget(YawAngleQueryComponentHorWidget);
    RightFunVerLayout->addWidget(pitchAngleTipLabel);
    RightFunVerLayout->addWidget(PitchAngleSetComponentHorWidget);
    RightFunVerLayout->addWidget(PitchAngleQueryComponentHorWidget);
    RightFunVerLayout->addWidget(PositionSpeedComponentHorWidget);
    RightFunVerWidget= new QWidget();
    RightFunVerWidget->setLayout(RightFunVerLayout);

    /***整体水平布局设置***/
    MainHorLayout = new QHBoxLayout;
    MainHorLayout->addWidget(LeftFunVerWidget);
    addSpacer(MainHorLayout, 30, 0);//设置与右侧屏幕的水平间距
    MainHorLayout->addWidget(RightFunVerWidget);
    MainHorWidget = new QWidget();
    MainHorWidget->setLayout(MainHorLayout);
    //居中显示
    setCentralWidget(MainHorWidget);

    /***信号与槽连接部分***/
    //成像部分
    connect(startImageButton, &QPushButton::clicked, this, &MainWindow::onStartImagingButtonClicked);
    connect(stopImageButton, &QPushButton::clicked, this, &MainWindow::onStopImagingButtonClicked);
    connect(receiveDataToFileButton, &QPushButton::clicked, this, &MainWindow::onReceiveDataToFileButtonClicked);
    //服务器与客户端连接部分
    connect(connectClientButton, &QPushButton::clicked, this, &MainWindow::onConnectClientClicked);
    connect(disconnectClientButton, &QPushButton::clicked, this, &MainWindow::onDisconnectClientClicked);
    connect(server, &Server::clientDataReceived, this, &MainWindow::onClientDataReceived);
    connect(server, &Server::clientConnectionStatusUpdated, this, &MainWindow::onClientConnectionStatusUpdated);
    //镜头调焦部分
    connect(lensForwardAdjustFocusRoughlyButton, &QPushButton::clicked, this, &MainWindow::onLensForwardAdjustFocusRoughlyButtonClicked);
    connect(lensForwardAdjustFocusFinelyButton, &QPushButton::clicked, this, &MainWindow::onLensForwardAdjustFocusFinelyButtonClicked);
    connect(lensBackAdjustFocusRoughlyButton, &QPushButton::clicked, this, &MainWindow::onLensBackAdjustFocusRoughlyButtonClicked);
    connect(lensBackAdjustFocusFinelyButton, &QPushButton::clicked, this, &MainWindow::onLensBackAdjustFocusFinelyButtonClicked);
    connect(lensLeftFocusingRoughlyButton, &QPushButton::clicked, this, &MainWindow::onLensLeftFocusingRoughlyButtonClicked);
    connect(lensLeftFocusingFinelyButton, &QPushButton::clicked, this, &MainWindow::onLensLeftFocusingFinelyButtonClicked);
    connect(lensRightFocusingRoughlyButton, &QPushButton::clicked, this, &MainWindow::onLensRightFocusingRoughlyButtonClicked);
    connect(lensRightFocusingFinelyButton, &QPushButton::clicked, this, &MainWindow::onLensRightFocusingFinelyButtonClicked);
    //转台操控部分
    connect(setTurntablePositionSpeedButton, &QPushButton::clicked, this, &MainWindow::onSetTurntablePositionSpeedButtonClicked);
    connect(upTurntableButton, &QPushButton::pressed, this, &MainWindow::onUpTurntableControlButtonPressed);
    connect(downTurntableButton, &QPushButton::pressed, this, &MainWindow::onDownTurntableControlButtonPressed);
    connect(leftTurntableButton, &QPushButton::pressed, this, &MainWindow::onLeftTurntableControlButtonPressed);
    connect(rightTurntableButton, &QPushButton::pressed, this, &MainWindow::onRightTurntableControlButtonPressed);
    connect(upTurntableButton, &QPushButton::released, this, &MainWindow::onUpTurntableControlButtonReleased);
    connect(downTurntableButton, &QPushButton::released, this, &MainWindow::onDownTurntableControlButtonReleased);
    connect(leftTurntableButton, &QPushButton::released, this, &MainWindow::onLeftTurntableControlButtonReleased);
    connect(rightTurntableButton, &QPushButton::released, this, &MainWindow::onRightTurntableControlButtonReleased);
    connect(queryTurntableYawAngleButton, &QPushButton::clicked, this, &MainWindow::onQueryTurntableYawAngleButtonClicked);
    connect(queryTurntablePitchAngleButton, &QPushButton::clicked, this, &MainWindow::onQueryTurntablePitchAngleButtonClicked);
    connect(setTurntableYawAngleButton, &QPushButton::clicked, this, &MainWindow::onSetTurntableYawAngleButtonClicked);
    connect(setTurntablePitchAngleButton, &QPushButton::clicked, this, &MainWindow::onSetTurntablePitchAngleButtonClicked);
}

MainWindow::~MainWindow() {}

/***服务器相关的槽函数***/
void MainWindow::onConnectClientClicked()
{
    server->connectToClient();
    connectClientButton->setEnabled(false);
    disconnectClientButton->setEnabled(true);
}

void MainWindow::onDisconnectClientClicked()
{
    server->disconnectFromClient();
    connectClientButton->setEnabled(true);
    disconnectClientButton->setEnabled(false);
}


//处理客户端发送过来的数据（包括了转台数据、PF32数据）（客户端发来的数据都是uint16_t类型，被转换成了字节流）
void MainWindow::onClientDataReceived(const QByteArray &data)
{
    //qDebug() << "从客户端接收的数据:" << data.toHex();//打印从客户端接收到的数据

    //判断数据是否是转台水平角查询或者俯仰角度查询的数据
    // 判断字节个数
    if (data.size() == 14) // 检查是否为14字节
    {
        // 提取有效的七个云台数据的低字节
        QByteArray validData;
        for (int i = 0; i < 14; i += 2)
        {
            validData.append(data[i + 1]); // 取出低字节
        }
        // 判断提取的七个字节数据
        if (validData.size() == 7)
        {
            // 打印出提取的七个字节
            qDebug() << "提取的七个数据:" << validData.toHex();

            // 判断特定条件
            if ((static_cast<unsigned char>(validData[0]) == 0xFF) &&
                (static_cast<unsigned char>(validData[1]) == 0x01) &&
                (static_cast<unsigned char>(validData[2]) == 0x00) &&
                (static_cast<unsigned char>(validData[3]) == 0x59))
            {
                // 合并有效数据的第5个和第6个字节
                uint16_t yawAngleValue = (static_cast<unsigned char>(validData[4]) << 8) | static_cast<unsigned char>(validData[5]);
                // 转换为十进制并除以100
                double result = static_cast<double>(yawAngleValue) / 100.0;
                // 将水平角度结果显示在标签
                yawAngleDisplayLabel->setText(QString::number(result, 'f', 2)); // 保留两位小数
            }
            else if((static_cast<unsigned char>(validData[0]) == 0xFF) &&
                     (static_cast<unsigned char>(validData[1]) == 0x01) &&
                     (static_cast<unsigned char>(validData[2]) == 0x00) &&
                     (static_cast<unsigned char>(validData[3]) == 0x5B))
            {
                // 合并有效数据的第5个和第6个字节
                uint16_t pitchAngleValue = (static_cast<unsigned char>(validData[4]) << 8) | static_cast<unsigned char>(validData[5]);
                // 转换为十进制并除以100
                double result = static_cast<double>(pitchAngleValue) / 100.0;
                // 检查 result 是否大于等于 300，并调整值
                if (result >= 300)
                {
                    result -= 360; // 若 result >= 300，则减去 360
                }
                // 将俯仰角度结果显示在标签
                pitchAngleDisplayLabel->setText(QString::number(result, 'f', 2)); // 保留两位小数
            }
        }
        return;//直接返回
    }

    // 将新接收到的数据追加到缓冲区
    receivedData.append(data);
    // 确保接收到的数据量达到 2048 字节
    const int expectedSize = 32 * 32 * 2; // 2048
    while (receivedData.size() >= expectedSize) // 检查数据是否足够
    {
        // 检查缓冲区数据是否正好是 2048 字节
        if (receivedData.size() == expectedSize)
        {
            // 提取所需的完整数据
            QByteArray completeData = receivedData.left(expectedSize);
            receivedData.clear();//移除缓冲区数据

            // 将数据转存到 receivedData_File 中
            {
                QMutexLocker locker(&receivedData_File_mutex); // 加锁
                receivedData_File = completeData; // 复制数据到 receivedData_File缓冲区
            } // 自动解锁

            // 使用 ImageProcessor 中的 processImage 函数处理图像
            QImage image = imageProcessor->processImage(completeData);
            if (!image.isNull())
            {
                lastProcessedImage = image; // 存储最后处理的图像
                // 只有在成像启用时更新显示图像
                if (isImagingEnabled)
                {
                    qDebug() << "已更新图像";
                    imageLabel->setPixmap(QPixmap::fromImage(image).scaled(300, 300, Qt::KeepAspectRatio)); // 更新显示图像
                }
            }
        }
        else
        {
            // 如果缓冲区数据多于 2048 字节，直接移除数据
            receivedData.clear();
            qDebug() << "缓冲区清零";
        }

    }
}
//服务器与客户端连接状态改变时该函数被调用，将状态显示在标签中
void MainWindow::onClientConnectionStatusUpdated(const QString &status)
{
    clientConnectionStatus->setText(status);
}

/***成像相关的槽函数***/
//点击开始成像按钮后的槽函数
void MainWindow::onStartImagingButtonClicked()
{
    qDebug()<<"开始成像";
    isImagingEnabled = true; // 启用成像
    startImageButton->setEnabled(false);
    stopImageButton->setEnabled(true);
}
//点击停止成像按钮后的槽函数
void MainWindow::onStopImagingButtonClicked()
{
    isImagingEnabled = false; // 停止成像，但保留最后的图像
    startImageButton->setEnabled(true);
    stopImageButton->setEnabled(false);
    //将最后的图像更新到界面上
    if (!lastProcessedImage.isNull())
    {
        qDebug()<<"已停止更新图像";
        imageLabel->setPixmap(QPixmap::fromImage(lastProcessedImage).scaled(300, 300, Qt::KeepAspectRatio));
    }
}
//点击保存数据按钮后的槽函数
void MainWindow::onReceiveDataToFileButtonClicked()
{
    // 获取当前时间
    QString timestamp = QDateTime::currentDateTime().toString("yyyy_MM_dd_HH_mm_ss");
    // 指定完整的保存路径，包括文件名
    QString filePath = QString("/home/tsh/QT_test/test_data/receivedData_%1.dat").arg(timestamp);

    // 创建文件对象，使用指定路径作为目标路径
   QFile file(filePath);

    // 尝试打开文件以进行写入
    if (!file.open(QIODevice::WriteOnly))
    {
        QMessageBox::warning(this, "File Error", "Failed to open file for writing.");
        return;
    }

    // 加锁以保护对 receivedData_File 的访问
    {
        QMutexLocker locker(&receivedData_File_mutex);
        // 创建文本流用于写入数据
        QTextStream out(&file);
        // 验证 receivedData_File 的数量是否是偶数
        if (receivedData_File.size() % 2 != 0) {
            qWarning() << "Warning: receivedData_File size is not a multiple of 2.";
            return;
        }

        // 将 QByteArray 数据按 uint16_t 读取并写入文件
        for (int i = 0; i < receivedData_File.size(); i += 2)
        {
            // 读取 uint16_t 数据（注意字节序）
            uint16_t value = static_cast<uint16_t>((static_cast<uint8_t>(receivedData_File[i+1]) & 0xFF) |
                            (static_cast<uint8_t>(receivedData_File[i]) << 8));

            // 将数据写入文件，使用空格分隔
            out << value << " ";
        }
    } // 解锁

    // 关闭文件
    file.close();

    // 提示用户文件保存成功
    QMessageBox::information(this, "Success", "Data saved to " + filePath);
}

//点击控制镜头向前粗调焦的按钮的槽函数
void MainWindow::onLensForwardAdjustFocusRoughlyButtonClicked()
{
    //获取控制镜头向前粗调焦指令数组的指针
    uint8_t *adjustFocus = reinterpret_cast<uint8_t*>(motor->getSlideForwardRoughlyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(adjustFocus, motor->getSlideForwardRoughlyCommand().size());
}
//点击控制镜头向前微调焦的按钮的槽函数
void MainWindow::onLensForwardAdjustFocusFinelyButtonClicked()
{
    //获取控制镜头向前微调焦指令数组的指针
    uint8_t *adjustFocus = reinterpret_cast<uint8_t*>(motor->getSlideForwardFinelyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(adjustFocus, motor->getSlideForwardFinelyCommand().size());
}
//点击控制镜头向后粗调焦的按钮的槽函数
void MainWindow::onLensBackAdjustFocusRoughlyButtonClicked()
{
    //获取控制镜头向后粗调焦指令数组的指针
    uint8_t *adjustFocus = reinterpret_cast<uint8_t*>(motor->getSlideBackRoughlyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(adjustFocus, motor->getSlideBackRoughlyCommand().size());
}
//点击控制镜头向后微调焦的按钮的槽函数
void MainWindow::onLensBackAdjustFocusFinelyButtonClicked()
{
    //获取控制镜头向后微调焦指令数组的指针
    uint8_t *adjustFocus = reinterpret_cast<uint8_t*>(motor->getSlideBackFinelyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(adjustFocus, motor->getSlideBackFinelyCommand().size());
}
//点击控制镜头向左粗对焦的按钮的槽函数
void MainWindow::onLensLeftFocusingRoughlyButtonClicked()
{
    //获取控制镜头向左粗对焦指令数组的指针
    uint8_t *Focusing = reinterpret_cast<uint8_t*>(motor->getGearClockwiseRoughlyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(Focusing, motor->getGearClockwiseRoughlyCommand().size());
}
//点击控制镜头向左微对焦的按钮的槽函数
void MainWindow::onLensLeftFocusingFinelyButtonClicked()
{
    //获取控制镜头向左微对焦指令数组的指针
    uint8_t *Focusing = reinterpret_cast<uint8_t*>(motor->getGearClockwiseFinelyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(Focusing, motor->getGearClockwiseFinelyCommand().size());
}
//点击控制镜头向右粗对焦的按钮的槽函数
void MainWindow::onLensRightFocusingRoughlyButtonClicked()
{
    //获取控制镜头向右粗对焦指令数组的指针
    uint8_t *Focusing = reinterpret_cast<uint8_t*>(motor->getGearAnticlockwiseRoughlyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(Focusing, motor->getGearAnticlockwiseRoughlyCommand().size());
}
//点击控制镜头向右微对焦的按钮的槽函数
void MainWindow::onLensRightFocusingFinelyButtonClicked()
{
    //获取控制镜头向右微对焦指令数组的指针
    uint8_t *Focusing = reinterpret_cast<uint8_t*>(motor->getGearAnticlockwiseFinelyCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(Focusing, motor->getGearAnticlockwiseFinelyCommand().size());
}

/***操纵云台相关的槽函数***/
//点击确定云台定位速度按钮后的操作（水平和俯仰使用相同速度）
void MainWindow::onSetTurntablePositionSpeedButtonClicked()
{
    QString currentPositionSpeedValue = setTurntablePositionSpeedComboBox->currentText();
    bool ok;
    uint8_t currentPositionSpeedValue_uint8 = static_cast<uint8_t>(currentPositionSpeedValue.toUInt(&ok));
    if(ok)
    {
        //水平定位速度和俯仰定位速度都设置为速度设置控件中的值
        turntable->setTurntablePositionSpeed(currentPositionSpeedValue_uint8,currentPositionSpeedValue_uint8);
        //获取水平定位指令数组的指针
        uint8_t *speedValue = reinterpret_cast<uint8_t*>(turntable->getTurntablePositionSpeedCommand().data());
        //通过网络向客户端发送水平定位指令
        server->serverSendMessage(speedValue, turntable->getTurntablePositionSpeedCommand().size());
    }
}

//按下向上控制云台按钮后的操作
void MainWindow::onUpTurntableControlButtonPressed()
{
    QString currentControlSpeedValue = setTurntableControlSpeedComboBox->currentText();
    bool ok;
    uint8_t currentControlSpeedValue_uint8 = static_cast<uint8_t>(currentControlSpeedValue.toUInt(&ok));
    if(ok)
    {
        turntable->setTurntableControlUp(currentControlSpeedValue_uint8);
        //获取水平定位指令数组的指针
        uint8_t *controlValue = reinterpret_cast<uint8_t*>(turntable->getTurntableControlUpCommand().data());
        //通过网络向客户端发送水平定位指令
        server->serverSendMessage(controlValue, turntable->getTurntableControlUpCommand().size());
    }
}
//按下向下控制云台按钮后的操作
void MainWindow::onDownTurntableControlButtonPressed()
{
    QString currentControlSpeedValue = setTurntableControlSpeedComboBox->currentText();
    bool ok;
    uint8_t currentControlSpeedValue_uint8 = static_cast<uint8_t>(currentControlSpeedValue.toUInt(&ok));
    if(ok)
    {
        turntable->setTurntableControlDown(currentControlSpeedValue_uint8);
        //获取指令数组的指针
        uint8_t *controlValue = reinterpret_cast<uint8_t*>(turntable->getTurntableControlDownCommand().data());
        //通过网络向客户端发送水平定位指令
        server->serverSendMessage(controlValue, turntable->getTurntableControlDownCommand().size());
    }
}
//按下向左控制云台按钮后的操作
void MainWindow::onLeftTurntableControlButtonPressed()
{
    QString currentControlSpeedValue = setTurntableControlSpeedComboBox->currentText();
    bool ok;
    uint8_t currentControlSpeedValue_uint8 = static_cast<uint8_t>(currentControlSpeedValue.toUInt(&ok));
    if(ok)
    {
        turntable->setTurntableControlLeft(currentControlSpeedValue_uint8);
        //获取指令数组的指针
        uint8_t *controlValue = reinterpret_cast<uint8_t*>(turntable->getTurntableControlLeftCommand().data());
        //通过网络向客户端发送水平定位指令
        server->serverSendMessage(controlValue, turntable->getTurntableControlLeftCommand().size());
    }
}
//按下向右控制云台按钮后的操作
void MainWindow::onRightTurntableControlButtonPressed()
{
    QString currentControlSpeedValue = setTurntableControlSpeedComboBox->currentText();
    bool ok;
    uint8_t currentControlSpeedValue_uint8 = static_cast<uint8_t>(currentControlSpeedValue.toUInt(&ok));
    if(ok)
    {
        turntable->setTurntableControlRight(currentControlSpeedValue_uint8);
        //获取指令数组的指针
        uint8_t *controlValue = reinterpret_cast<uint8_t*>(turntable->getTurntableControlRightCommand().data());
        //通过网络向客户端发送水平定位指令
        server->serverSendMessage(controlValue, turntable->getTurntableControlRightCommand().size());
    }
}

//松开向上控制云台按钮后的操作（发送停止移动的指令）
void MainWindow::onUpTurntableControlButtonReleased()
{
    //获取转台停止转动指令数组的指针
    uint8_t *stopValue = reinterpret_cast<uint8_t*>(turntable->getTurntableStopRotateCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(stopValue, turntable->getTurntableStopRotateCommand().size());
}
//松开向下控制云台按钮后的操作（发送停止移动的指令）
void MainWindow::onDownTurntableControlButtonReleased()
{
    //获取转台停止转动指令数组的指针
    uint8_t *stopValue = reinterpret_cast<uint8_t*>(turntable->getTurntableStopRotateCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(stopValue, turntable->getTurntableStopRotateCommand().size());
}
//松开向左控制云台按钮后的操作（发送停止移动的指令）
void MainWindow::onLeftTurntableControlButtonReleased()
{
    //获取转台停止转动指令数组的指针
    uint8_t *stopValue = reinterpret_cast<uint8_t*>(turntable->getTurntableStopRotateCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(stopValue, turntable->getTurntableStopRotateCommand().size());
}
//松开向右控制云台按钮后的操作（发送停止移动的指令）
void MainWindow::onRightTurntableControlButtonReleased()
{
    //获取转台停止转动指令数组的指针
    uint8_t *stopValue = reinterpret_cast<uint8_t*>(turntable->getTurntableStopRotateCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(stopValue, turntable->getTurntableStopRotateCommand().size());
}
//点击查询云台水平角按钮后的槽函数
void MainWindow::onQueryTurntableYawAngleButtonClicked()
{
    //获取转台查询云台水平角指令数组的指针
    uint8_t *queryValue = reinterpret_cast<uint8_t*>(turntable->getTurntableYawAngleQueryCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(queryValue, turntable->getTurntableYawAngleQueryCommand().size());
}
//点击查询云台俯仰角按钮后的槽函数
void MainWindow::onQueryTurntablePitchAngleButtonClicked()
{
    //获取转台查询云台俯仰角指令数组的指针
    uint8_t *queryValue = reinterpret_cast<uint8_t*>(turntable->getTurntablePitchAngleQueryCommand().data());
    //通过网络向客户端发送指令
    server->serverSendMessage(queryValue, turntable->getTurntablePitchAngleQueryCommand().size());
}
//点击设置云台水平角按钮后的槽函数
void MainWindow::onSetTurntableYawAngleButtonClicked()
{
    // 获取yawAngleLineEdit中的文本内容
    QString angleText = yawAngleLineEdit->text();
    // 检查文本是否为空
    if (angleText.isEmpty())
    {
        return;  // 如果为空，直接返回
    }
    // 将字符串转换为双精度浮点数
    bool conversionSuccess;
    double yawAngle = angleText.toDouble(&conversionSuccess);
    // 检查转换是否成功
    if (!conversionSuccess)
    {
        qDebug() << "转换失败";
        yawAngleLineEdit->clear();
        return;
    }
    // 检查数值是否在0.00到360.00之间
    if ((yawAngle < 0.00) || (yawAngle > 360.00))
    {
        // 超出范围，打印错误信息
        qDebug() << "超出范围： 输入的角度必须在0.00到360.00之间。";
        yawAngleLineEdit->clear();
        return;
    }

    // 如果满足条件，进行接下来操作
    double scaledYawAngle = yawAngle * 100; // 将yawAngle乘以100
    // 将scaledYawAngle分成yawDataH和yawDataL
    uint8_t yawDataH = static_cast<int>(scaledYawAngle) >> 8; // 高字节
    uint8_t yawDataL = static_cast<int>(scaledYawAngle) & 0xFF; // 低字节

    qDebug() << "yawDataH:" << yawDataH << ", yawDataL:" << yawDataL;

    //设置水平角
    turntable->setTurntableYawAnglePosition(yawDataH,yawDataL);
    //获取水平定位指令数组的指针
    uint8_t *yawData = reinterpret_cast<uint8_t*>(turntable->getTurntableYawAnglePositionCommand().data());
    //通过网络向客户端发送水平定位指令
    server->serverSendMessage(yawData, turntable->getTurntableYawAnglePositionCommand().size());

}
//点击设置云台俯仰角按钮后的槽函数
void MainWindow::onSetTurntablePitchAngleButtonClicked()
{
    // 获取pitchAngleLineEdit中的文本内容
    QString angleText = pitchAngleLineEdit->text();
    // 检查文本是否为空
    if (angleText.isEmpty())
    {
        return;  // 如果为空，直接返回
    }
    // 将字符串转换为双精度浮点数
    bool conversionSuccess;
    double pitchAngle = angleText.toDouble(&conversionSuccess);
    // 检查转换是否成功
    if (!conversionSuccess)
    {
        qDebug() << "转换失败";
        pitchAngleLineEdit->clear();
        return;
    }
    // 检查数值是否在-60.00到60.00之间
    if ((pitchAngle < -60.00) || (pitchAngle > 60.00))
    {
        // 超出范围，打印错误信息
        qDebug() << "超出范围： 输入的角度必须在-60.00到60.00之间。";
        pitchAngleLineEdit->clear();
        return;
    }
    // 如果满足条件，进行接下来操作
    double scaledPitchAngle = pitchAngle * 100; // 将pitchAngle乘以100
    if((scaledPitchAngle >= -6000.00) && (scaledPitchAngle < 0.00))
    {
        scaledPitchAngle = 36000 + scaledPitchAngle;
    }

    // 将scaledYawAngle分成pitchDataH和pitchDataL
    uint8_t pitchDataH = static_cast<int>(scaledPitchAngle) >> 8; // 高字节
    uint8_t pitchDataL = static_cast<int>(scaledPitchAngle) & 0xFF; // 低字节

    qDebug() << "pitchDataH:" << pitchDataH << ", pitchDataL:" << pitchDataL;

    //设置俯仰角
    turntable->setTurntablePitchAnglePosition(pitchDataH,pitchDataL);
    //获取俯仰定位指令数组的指针
    uint8_t *pitchData = reinterpret_cast<uint8_t*>(turntable->getTurntablePitchAnglePositionCommand().data());
    //通过网络向客户端发送俯仰定位指令
    server->serverSendMessage(pitchData, turntable->getTurntablePitchAnglePositionCommand().size());
}

/*用于添加占位符以改变控件之间的距离*/
QWidget* MainWindow::addSpacer(QLayout *layout, int width, int height)
{
    // 创建一个空的 QWidget 作为占位符
    QWidget *spacer = new QWidget();
    spacer->setFixedSize(width, height); // 设置固定宽度和高度
    layout->addWidget(spacer); // 将它添加到布局中
    return spacer; // 返回占位符指针
}


