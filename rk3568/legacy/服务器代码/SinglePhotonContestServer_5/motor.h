#ifndef MOTOR_H
#define MOTOR_H

#include <QObject>
#include <QByteArray>
#include <QString>

class Motor : public QObject
{
    Q_OBJECT

public:
    explicit Motor(QObject *parent = nullptr);

    // 获取镜头调焦指令数组的引用
    QByteArray &getSlideForwardRoughlyCommand();//获取直线滑台向前粗调指令
    QByteArray &getSlideBackRoughlyCommand();//获取直线滑台向后粗调指令
    QByteArray &getSlideForwardFinelyCommand();//获取直线滑台向前细调指令
    QByteArray &getSlideBackFinelyCommand();//获取直线滑台向后细调指令

    QByteArray &getGearClockwiseRoughlyCommand();//获取齿轮顺时针粗调指令
    QByteArray &getGearAnticlockwiseRoughlyCommand();//获取齿轮逆时针粗调指令
    QByteArray &getGearClockwiseFinelyCommand();//获取齿轮顺时针细调指令
    QByteArray &getGearAnticlockwiseFinelyCommand();//获取齿轮逆时针细调指令

private:
    // 镜头调焦指令数组声明
    QByteArray command_slide_forward_roughly; // 直线滑台向前粗调
    QByteArray command_slide_back_roughly; // 直线滑台向后粗调
    QByteArray command_slide_forward_finely; // 直线滑台向前细调
    QByteArray command_slide_back_finely; // 直线滑台向后细调

    QByteArray command_gear_clockwise_roughly; // 齿轮顺时针粗转
    QByteArray command_gear_anticlockwise_roughly; // 齿轮逆时针粗转
    QByteArray command_gear_clockwise_finely; // 齿轮顺时针精转
    QByteArray command_gear_anticlockwise_finely; // 齿轮逆时针精转

};

#endif // MOTOR_H
