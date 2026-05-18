#include "turntable.h"
#include <QDebug>

Turntable::Turntable(QObject *parent)
    : QObject(parent)
{
    // 初始化指令数组
    //水平定位指令
    uint8_t array_y_ang_position[] = {0xff, 0x01, 0x00, 0x4b, 0x00, 0x00, 0x00}; // 校验位初始化为0
    command_y_ang_position = QByteArray(reinterpret_cast<const char *>(array_y_ang_position), sizeof(array_y_ang_position));
    //俯仰定位指令
    uint8_t array_p_ang_position[] = {0xff, 0x01, 0x00, 0x4d, 0x00, 0x00, 0x00}; // 校验位初始化为0
    command_p_ang_position = QByteArray(reinterpret_cast<const char *>(array_p_ang_position), sizeof(array_p_ang_position));
    //定位速度指令
    uint8_t array_position_speed[] = {0xff, 0x01, 0x00, 0x5f, 0x1e, 0x1e, 0x9c};//初始速度设置为30（水平和俯仰速度设置为一样的）
    command_position_speed = QByteArray(reinterpret_cast<const char *>(array_position_speed), sizeof(array_position_speed));
    //控制水平向右指令
    uint8_t array_y_r_control[] = {0xff, 0x01, 0x00, 0x02, 0x07, 0x00, 0x0a};//初始速度设置为7
    command_y_r_control = QByteArray(reinterpret_cast<const char *>(array_y_r_control), sizeof(array_y_r_control));
    //控制水平向左指令
    uint8_t array_y_l_control[] = {0xff, 0x01, 0x00, 0x04, 0x07, 0x00, 0x0c};//初始速度设置为7
    command_y_l_control = QByteArray(reinterpret_cast<const char *>(array_y_l_control), sizeof(array_y_l_control));
    //控制俯仰向上指令
    uint8_t array_p_u_control[] = {0xff, 0x01, 0x00, 0x08, 0x00, 0x07, 0x10};//初始速度设置为7
    command_p_u_control = QByteArray(reinterpret_cast<const char *>(array_p_u_control), sizeof(array_p_u_control));
    //控制俯仰向下指令
    uint8_t array_p_d_control[] = {0xff, 0x01, 0x00, 0x10, 0x00, 0x07, 0x18};//初始速度设置为7
    command_p_d_control = QByteArray(reinterpret_cast<const char *>(array_p_d_control), sizeof(array_p_d_control));
    //转台停止转动指令
    uint8_t array_rotate_stop[] = {0xff, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01};//该指令不用改变
    command_rotate_stop = QByteArray(reinterpret_cast<const char *>(array_rotate_stop), sizeof(array_rotate_stop));
    //查询转台水平角度的指令
    uint8_t array_y_ang_query[] = {0xff, 0x01, 0x00, 0x51, 0x00, 0x00, 0x52};//该指令不用改变
    command_y_ang_query = QByteArray(reinterpret_cast<const char *>(array_y_ang_query), sizeof(array_y_ang_query));
    //查询转台俯仰角度的指令
    uint8_t array_p_ang_query[] = {0xff, 0x01, 0x00, 0x53, 0x00, 0x00, 0x54};//该指令不用改变
    command_p_ang_query = QByteArray(reinterpret_cast<const char *>(array_p_ang_query), sizeof(array_p_ang_query));
}

//设置转台水平定位位置的指令
void Turntable::setTurntableYawAnglePosition(uint8_t angle_h, uint8_t angle_l)
{
    command_y_ang_position[4] = angle_h;
    command_y_ang_position[5] = angle_l;
    command_y_ang_position[6] = updataCommandChecksum(command_y_ang_position);
}
//设置转台俯仰定位位置的指令
void Turntable::setTurntablePitchAnglePosition(uint8_t angle_h, uint8_t angle_l)
{
    command_p_ang_position[4] = angle_h;
    command_p_ang_position[5] = angle_l;
    command_p_ang_position[6] = updataCommandChecksum(command_p_ang_position);
}
//设置转台定位速度的指令
void Turntable::setTurntablePositionSpeed(uint8_t speed_y, uint8_t speed_p)
{
    command_position_speed[4] = speed_y;
    command_position_speed[5] = speed_p;
    command_position_speed[6] = updataCommandChecksum(command_position_speed);
}
//设置转台水平向右的指令
void Turntable::setTurntableControlRight(uint8_t speed)
{
    command_y_r_control[4] = speed;
    command_y_r_control[6] = updataCommandChecksum(command_y_r_control);
}
//设置转台水平向左的指令
void Turntable::setTurntableControlLeft(uint8_t speed)
{
    command_y_l_control[4] = speed;
    command_y_l_control[6] = updataCommandChecksum(command_y_l_control);
}
//设置转台俯仰向上的指令
void Turntable::setTurntableControlUp(uint8_t speed)
{
    command_p_u_control[5] = speed;
    command_p_u_control[6] = updataCommandChecksum(command_p_u_control);
}
//设置转台俯仰向下的指令
void Turntable::setTurntableControlDown(uint8_t speed)
{
    command_p_d_control[5] = speed;
    command_p_d_control[6] = updataCommandChecksum(command_p_d_control);
}

//获取转台水平定位指令
QByteArray &Turntable::getTurntableYawAnglePositionCommand()
{
    return command_y_ang_position;
}
//获取转台俯仰定位指令
QByteArray &Turntable::getTurntablePitchAnglePositionCommand()
{
    return command_p_ang_position;
}
//获取转台定位速度指令
QByteArray &Turntable::getTurntablePositionSpeedCommand()
{
    return command_position_speed;
}
//获取转台控制向右指令
QByteArray &Turntable::getTurntableControlRightCommand()
{
    return command_y_r_control;
}
//获取转台控制向右指令
QByteArray &Turntable::getTurntableControlLeftCommand()
{
    return command_y_l_control;
}
//获取转台控制向上指令
QByteArray &Turntable::getTurntableControlUpCommand()
{
    return command_p_u_control;
}
//获取转台控制向下指令
QByteArray &Turntable::getTurntableControlDownCommand()
{
    return command_p_d_control;
}

//获取转台停止转动指令
QByteArray &Turntable::getTurntableStopRotateCommand()
{
    return command_rotate_stop;
}

//获取查询云台水平角的指令
QByteArray &Turntable::getTurntableYawAngleQueryCommand()
{
    return command_y_ang_query;
}

//获取查询云台俯仰角的指令
QByteArray &Turntable::getTurntablePitchAngleQueryCommand()
{
    return command_p_ang_query;
}

//转台指令校验
uint8_t Turntable::updataCommandChecksum(QByteArray &command)
{
    uint8_t sum = 0;
    for(int i = 1; i < 6; i++)
    {
        sum += static_cast<uint8_t>(command[i]);
    }
    return sum;
}
