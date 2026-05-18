#include "motor.h"
#include <QDebug>

Motor::Motor(QObject *parent)// Motor类的构造函数，接受一个 QObject 指针作为父对象
    : QObject(parent)
{
    // 初始化指令数组
    //直线滑台向前粗调指令
    uint8_t array_slide_forward_roughly[] = {0xff, 0x02, 0x01, 0x20, 0x01, 0x24};
    command_slide_forward_roughly = QByteArray(reinterpret_cast<const char *>(array_slide_forward_roughly), sizeof(array_slide_forward_roughly));
    //直线滑台向后粗调指令
    uint8_t array_slide_back_roughly[] = {0xff, 0x02, 0x01, 0x22, 0x01, 0x26};
    command_slide_back_roughly = QByteArray(reinterpret_cast<const char *>(array_slide_back_roughly), sizeof(array_slide_back_roughly));
    //直线滑台向前细调指令
    uint8_t array_slide_forward_finely[] = {0xff, 0x02, 0x01, 0x20, 0x02, 0x25};
    command_slide_forward_finely = QByteArray(reinterpret_cast<const char *>(array_slide_forward_finely), sizeof(array_slide_forward_finely));
    //直线滑台向后细调指令
    uint8_t array_slide_back_finely[] = {0xff, 0x02, 0x01, 0x22, 0x02, 0x27};
    command_slide_back_finely = QByteArray(reinterpret_cast<const char *>(array_slide_back_finely), sizeof(array_slide_back_finely));
    //齿轮顺时针粗调指令
    uint8_t array_gear_clockwise_roughly[] = {0xff, 0x02, 0x02, 0x40, 0x01, 0x45};
    command_gear_clockwise_roughly = QByteArray(reinterpret_cast<const char *>(array_gear_clockwise_roughly), sizeof(array_gear_clockwise_roughly));
    //齿轮逆时针粗调指令
    uint8_t array_gear_anticlockwise_roughly[] = {0xff, 0x02, 0x02, 0x42, 0x01, 0x47};
    command_gear_anticlockwise_roughly = QByteArray(reinterpret_cast<const char *>(array_gear_anticlockwise_roughly), sizeof(array_gear_anticlockwise_roughly));
    //齿轮顺时针细调指令
    uint8_t array_gear_clockwise_finely[] = {0xff, 0x02, 0x02, 0x40, 0x02, 0x46};
    command_gear_clockwise_finely = QByteArray(reinterpret_cast<const char *>(array_gear_clockwise_finely), sizeof(array_gear_clockwise_finely));
    //齿轮逆时针细调指令
    uint8_t array_gear_anticlockwise_finely[] = {0xff, 0x02, 0x02, 0x42, 0x02, 0x48};
    command_gear_anticlockwise_finely = QByteArray(reinterpret_cast<const char *>(array_gear_anticlockwise_finely), sizeof(array_gear_anticlockwise_finely));

}

//获取直线滑台向前粗调指令
QByteArray &Motor::getSlideForwardRoughlyCommand()
{
    return command_slide_forward_roughly;
}
//获取直线滑台向后粗调指令
QByteArray &Motor::getSlideBackRoughlyCommand()
{
    return command_slide_back_roughly;
}
//获取直线滑台向前细调指令
QByteArray &Motor::getSlideForwardFinelyCommand()
{
    return command_slide_forward_finely;
}
//获取直线滑台向后细调指令
QByteArray &Motor::getSlideBackFinelyCommand()
{
    return command_slide_back_finely;
}
//获取齿轮顺时针粗调指令
QByteArray &Motor::getGearClockwiseRoughlyCommand()
{
    return command_gear_clockwise_roughly;
}
//获取齿轮逆时针粗调指令
QByteArray &Motor::getGearAnticlockwiseRoughlyCommand()
{
    return command_gear_anticlockwise_roughly;
}
//获取齿轮顺时针细调指令
QByteArray &Motor::getGearClockwiseFinelyCommand()
{
    return command_gear_clockwise_finely;
}
//获取齿轮逆时针细调指令
QByteArray &Motor::getGearAnticlockwiseFinelyCommand()
{
    return command_gear_anticlockwise_finely;
}
