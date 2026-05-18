#ifndef TURNTABLE_H
#define TURNTABLE_H

#include <QObject>
#include <QByteArray>
#include <QString>

class Turntable : public QObject
{
    Q_OBJECT

public:
    explicit Turntable(QObject *parent = nullptr);

    // 公共方法设置转台相关指令
    void setTurntableYawAnglePosition(uint8_t angle_h, uint8_t angle_l);//设置转台水平定位位置
    void setTurntablePitchAnglePosition(uint8_t angle_h, uint8_t angle_l);//设置转台俯仰定位位置
    void setTurntablePositionSpeed(uint8_t speed_y, uint8_t speed_p);//设置转台定位速度

    void setTurntableControlUp(uint8_t speed);//设置控制转台向上移动（需要设置的只有转台控制速度）
    void setTurntableControlDown(uint8_t speed);//设置控制转台向下移动
    void setTurntableControlLeft(uint8_t speed);//设置控制转台向左移动
    void setTurntableControlRight(uint8_t speed);//设置控制转台向右移动


    // 获取云台指令数组的引用
    QByteArray &getTurntableYawAnglePositionCommand();//获取转台水平定位位置指令
    QByteArray &getTurntablePitchAnglePositionCommand();//获取转台俯仰定位位置指令
    QByteArray &getTurntablePositionSpeedCommand();//获取转台定位速度指令

    QByteArray &getTurntableControlUpCommand();//获取转台控制向上指令
    QByteArray &getTurntableControlDownCommand();//获取转台控制向下指令
    QByteArray &getTurntableControlLeftCommand();//获取转台控制向左指令
    QByteArray &getTurntableControlRightCommand();//获取转台控制向右指令

    QByteArray &getTurntableStopRotateCommand();//获取转台停止转动指令

    QByteArray &getTurntableYawAngleQueryCommand();//获取查询云台水平角的指令
    QByteArray &getTurntablePitchAngleQueryCommand();//获取查询云台水平角的指令

private:
    // 云台指令数组声明
    QByteArray command_y_ang_position; // 水平角度定位
    QByteArray command_p_ang_position; // 俯仰角度定位
    QByteArray command_position_speed;//定位速度设置

    QByteArray command_y_r_control;//水平向右控制
    QByteArray command_y_l_control;//水平向左控制
    QByteArray command_p_u_control;//俯仰向上控制
    QByteArray command_p_d_control;//俯仰向下控制

    QByteArray command_rotate_stop;//云台立即停止转动

    QByteArray command_y_ang_query;//水平角度查询
    QByteArray command_p_ang_query;//俯仰角度查询

    uint8_t updataCommandChecksum(QByteArray &command); // 用于计算指令校验位夫人函数
};

#endif // TURNTABLE_H
