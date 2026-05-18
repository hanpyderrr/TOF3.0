#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QPushButton>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QImage>
#include <QComboBox>
#include <QLineEdit>
#include <QMutex>
#include <QDateTime>    // 用于获取当前时间
#include "server.h"
#include "image.h"
#include "turntable.h"
#include "motor.h"

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    //服务器与客户端连接部分的槽函数
    void onConnectClientClicked();//点击连接客户端的按钮后的槽函数
    void onDisconnectClientClicked();//点击断开客户端的按钮后的槽函数
    void onClientDataReceived(const QByteArray &data);//接收到客户端数据信号后的槽函数
    void onClientConnectionStatusUpdated(const QString &status);//与客户端的连接状态发生改变后的槽函数

    //成像部分的槽函数
    void onStartImagingButtonClicked(); // 点击开始成像按钮的槽函数
    void onStopImagingButtonClicked();  // 点击停止成像按钮的槽函数
    void onReceiveDataToFileButtonClicked(); // 点击保存数据按钮的槽函数

    //镜头调焦部分的槽函数
    void onLensForwardAdjustFocusRoughlyButtonClicked(); //点击控制镜头向前粗调焦的按钮的槽函数
    void onLensForwardAdjustFocusFinelyButtonClicked(); //点击控制镜头向前微调焦的按钮的槽函数
    void onLensBackAdjustFocusRoughlyButtonClicked(); //点击控制镜头向后粗调焦的按钮的槽函数
    void onLensBackAdjustFocusFinelyButtonClicked(); //点击控制镜头向后微调焦的按钮的槽函数
    void onLensLeftFocusingRoughlyButtonClicked(); //点击控制镜头向左粗对焦的按钮的槽函数
    void onLensLeftFocusingFinelyButtonClicked(); //点击控制镜头向左微对焦的按钮的槽函数
    void onLensRightFocusingRoughlyButtonClicked(); //点击控制镜头向右粗对焦的按钮的槽函数
    void onLensRightFocusingFinelyButtonClicked(); //点击控制镜头向右微对焦的按钮的槽函数

    //云台操控部分的槽函数
    void onSetTurntablePositionSpeedButtonClicked();//确定云台定位速度按钮按下后的槽函数
    void onUpTurntableControlButtonPressed();//点击控制云台向上移动的按钮后的槽函数
    void onDownTurntableControlButtonPressed();//点击控制云台向下移动的按钮后的槽函数
    void onLeftTurntableControlButtonPressed();//点击控制云台向左移动的按钮后的槽函数
    void onRightTurntableControlButtonPressed();//点击控制云台向下移动的按钮后的槽函数
    void onUpTurntableControlButtonReleased();//松开控制云台向上移动的按钮后的槽函数
    void onDownTurntableControlButtonReleased();//松开控制云台向下移动的按钮后的槽函数
    void onLeftTurntableControlButtonReleased();//松开控制云台向左移动的按钮后的槽函数
    void onRightTurntableControlButtonReleased();//松开控制云台向下移动的按钮后的槽函数
    void onQueryTurntableYawAngleButtonClicked();//点击查询云台水平角按钮后的槽函数
    void onQueryTurntablePitchAngleButtonClicked();//点击查询云台俯仰角按钮后的槽函数
    void onSetTurntableYawAngleButtonClicked();//点击设置云台水平角按钮后的槽函数
    void onSetTurntablePitchAngleButtonClicked();//点击设置云台俯仰角按钮后的槽函数


private:
    //布局部分
    /***成像功能部分***/
    //“开始成像”和“停止成像”的按钮水平布局和容器
    QHBoxLayout *ImageButtonHorLayout;
    QWidget *ImageButtonHorWidget;
    //成像功能（包括成像按钮和成像标签）的垂直布局
    QVBoxLayout *ImageFunVerLayout;
    QWidget *ImageFunVerWidget;

    /***调焦功能部分***/
    //向前调焦的标签，向前粗调焦按钮，向前微调焦按钮的水平布局
    QHBoxLayout *LensForwardAdjustFocusHorLayout;
    QWidget *LensForwardAdjustFocusHorWidget;
    //向后调焦的标签，向后粗调焦按钮，向后微调焦按钮的水平布局
    QHBoxLayout *LensBackAdjustFocusHorLayout;
    QWidget *LensBackAdjustFocusHorWidget;
    //向左对焦的标签，向左粗对焦按钮，向左微对焦按钮的水平布局
    QHBoxLayout *LensLeftFocusingHorLayout;
    QWidget *LensLeftFocusingHorWidget;
    //向右对焦的标签，向右粗对焦按钮，向右微对焦按钮的水平布局
    QHBoxLayout *LensRightFocusingHorLayout;
    QWidget *LensRightFocusingHorWidget;
    //调焦功能部分的垂直布局
    QVBoxLayout *LensFocusingFunVerLayout;
    QWidget *LensFocusingFunVerWidget;

    //左侧功能部分的垂直容器和垂直布局
    QVBoxLayout *LeftFunVerLayout;
    QWidget *LeftFunVerWidget;

    /***服务器功能部分***/
    //“连接客户端”和“断开客户端”的按钮水平布局和容器
    QHBoxLayout *ConnectClientButtonHorLayout;
    QWidget *ConnectClientButtonHorWidget;

    /***云台功能部分***/
    //定位速度标签、控件及确定按钮的水平布局和容器
    QHBoxLayout *PositionSpeedComponentHorLayout;
    QWidget *PositionSpeedComponentHorWidget;
    //控制速度标签、控件的水平布局和容器
    QHBoxLayout *ControlSpeedComponentHorLayout;
    QWidget *ControlSpeedComponentHorWidget;
    //云台上按钮的水平布局和容器
    QHBoxLayout *ControlUpButtonHorLayout;
    QWidget *ControlUpButtonHorWidget;
    //云台下按钮的水平布局和容器
    QHBoxLayout *ControlDownButtonHorLayout;
    QWidget *ControlDownButtonHorWidget;
    //云台左右按钮的水平布局和容器
    QHBoxLayout *ControlLeftAndRightButtonHorLayout;
    QWidget *ControlLeftAndRightButtonHorWidget;

    //云台上下左右转动按钮的垂直布局和容器
    QVBoxLayout *ControlRotateButtonVerLayout;
    QWidget *ControlRotateButtonVerWidget;

    //云台水平角查询和显示标签的水平布局和容器
    QHBoxLayout *YawAngleQueryComponentHorLayout;
    QWidget *YawAngleQueryComponentHorWidget;
    //云台俯仰角查询和显示标签的水平布局和容器
    QHBoxLayout *PitchAngleQueryComponentHorLayout;
    QWidget *PitchAngleQueryComponentHorWidget;
    //云台水平角设置的编辑栏和按钮的水平布局和容器
    QHBoxLayout *YawAngleSetComponentHorLayout;
    QWidget *YawAngleSetComponentHorWidget;
    //云台俯仰角设置的编辑栏和按钮的水平布局和容器
    QHBoxLayout *PitchAngleSetComponentHorLayout;
    QWidget *PitchAngleSetComponentHorWidget;

    //右侧功能部分的垂直容器和垂直布局
    QVBoxLayout *RightFunVerLayout;
    QWidget *RightFunVerWidget;


    //整个界面的水平布局和容器
    QHBoxLayout *MainHorLayout;
    QWidget *MainHorWidget;

    //与客户端连接的相关控件
    QLabel *clientConnectionStatus;//与客户端连接状态标签
    QPushButton *connectClientButton; //连接客户端的按钮
    QPushButton *disconnectClientButton;//断开客户端的按钮
    Server *server;//服务器类实例化
    QByteArray receivedData; // 缓存接收到的数据
    QByteArray receivedData_File; // 缓存数据转存到该数组，用于后续存到文件中
    QMutex receivedData_File_mutex; // 该锁用于保护 receivedData_File 的访问

    //成像功能部分控件
    QLabel *imageLabel;//用于显示图像的标签
    QPushButton *startImageButton; //开始成像的按钮
    QPushButton *stopImageButton;//停止成像的按钮
    QPushButton *receiveDataToFileButton;//将数据存成文件的按钮
    ImageProcessor *imageProcessor; // 图像处理器实例
    bool isImagingEnabled = false;//用于判断是否允许更新图像
    QImage lastProcessedImage;//存储最后处理过的图像

    //云台控制部分控件
    QLabel *setTurntableControlSpeedLabel;//用于提示控制速度的标签
    QComboBox *setTurntableControlSpeedComboBox;//该控件用于设置云台控制速度（不需要其他操作就能实现控制速度的设置）
    QPushButton *upTurntableButton;//该按钮用于控制云台俯仰向上移动
    QPushButton *downTurntableButton;//该按钮用于控制云台俯仰向下移动
    QPushButton *leftTurntableButton;//该按钮用于控制云台水平向左移动
    QPushButton *rightTurntableButton;//该按钮用于控制云台水平向右移动

    QLabel *setTurntablePositionSpeedLabel;//用于提示定位速度的标签
    QComboBox *setTurntablePositionSpeedComboBox;//该控件用于设置云台定位速度（设置完之后需要点击确定按钮才能发送速度设置指令）
    QPushButton *setTurntablePositionSpeedButton;//该按钮用于云台定位速度的设置

    QLabel *yawAngleTipLabel;//用于提示云台水平角的标签
    QLabel *pitchAngleTipLabel;//用于提示云台俯仰角的标签
    QLabel *yawAngleDisplayLabel;//用于显示云台水平角的标签
    QLabel *pitchAngleDisplayLabel;//用于显示云台俯仰角的标签
    QPushButton *queryTurntableYawAngleButton;//该按钮用于查询云台水平角度
    QPushButton *queryTurntablePitchAngleButton;//该按钮用于查询云台俯仰角度


    QLineEdit *yawAngleLineEdit;//用于填写水平角度（0-360）
    QLineEdit *pitchAngleLineEdit;//用于填写俯仰角度（-60-60）
    QPushButton *setTurntableYawAngleButton;//该按钮用于设置云台水平定位角度
    QPushButton *setTurntablePitchAngleButton;//该按钮用于设置云台俯仰定位角度

    Turntable *turntable;//转台实例化

    //镜头调焦部分控件
    QLabel *lensAdjustFocusFunctionLabel;//用于提示调焦功能的标签
    QLabel *lensForwardAdjustFocusFunctionLabel;//用于提示向前调焦功能的标签
    QPushButton *lensForwardAdjustFocusRoughlyButton;//该按钮用于控制镜头向前粗调焦距
    QPushButton *lensForwardAdjustFocusFinelyButton;//该按钮用于控制镜头向前微调焦距
    QLabel *lensBackAdjustFocusFunctionLabel;//用于提示向后调焦功能的标签
    QPushButton *lensBackAdjustFocusRoughlyButton;//该按钮用于控制镜头向前粗调焦距
    QPushButton *lensBackAdjustFocusFinelyButton;//该按钮用于控制镜头向前微调焦距

    QLabel *lensFocusingFunctionLabel;//用于提示对焦功能的标签
    QLabel *lensLeftFocusingFunctionLabel;//用于提示向左对焦功能的标签
    QPushButton *lensLeftFocusingRoughlyButton;//该按钮用于控制镜头向左粗对焦
    QPushButton *lensLeftFocusingFinelyButton;//该按钮用于控制镜头向左微对焦
    QLabel *lensRightFocusingFunctionLabel;//用于提示向右对焦功能的标签
    QPushButton *lensRightFocusingRoughlyButton;//该按钮用于控制镜头向右微对焦
    QPushButton *lensRightFocusingFinelyButton;//该按钮用于控制镜头向右微对焦

    Motor *motor;//电机实例化

    QWidget* addSpacer(QLayout *layout, int width, int height);//用于添加占位符以改变控件之间的水平或垂直距离
};
#endif // MAINWINDOW_H
