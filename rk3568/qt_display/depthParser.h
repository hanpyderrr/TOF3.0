#ifndef DEPTHPARSER_H
#define DEPTHPARSER_H
/*
 * depthParser.h — TOF 二进制帧解析器（RK3568端）
 *
 * 负责从 received.dat 读取一帧 TofFrame 二进制数据，
 * 校验魔数、协议版本、尺寸、CRC16、validCount 和深度范围，返回解析结果。
 *
 * 协议格式见 depth_proto.h（哪吒/RK3568 共用）
 */
#include <cstdint>
#include <QString>

/* ── 解析结果 ─────────────────────────────────────────────── */
struct DepthFrame {
    uint32_t seq;              /* 帧序号（来自 TofFrame.seq）*/
    uint16_t validCount;       /* 非零深度像素数 */
    uint16_t depths[1024];     /* 深度值（mm/像素），0 = 无效 */
    bool     valid;            /* true = 解析成功且 CRC 通过 */
    QString  errorMsg;         /* valid==false 时的错误描述 */
};

/* ── 解析器 ───────────────────────────────────────────────── */
class DepthParser
{
public:
    /*
     * parse() — 读取并解析 filePath 处的二进制 TOF 帧
     *
     * 输入：filePath   received.dat 的完整路径
     * 返回：DepthFrame
     *         .valid == true   解析成功，seq/validCount/depths 有效
     *         .valid == false  失败原因在 .errorMsg：
     *                          "open failed"      文件不存在或无权限
     *                          "short read: N"    文件不足 2070 字节
     *                          "bad magic"        不是 TOF 帧
     *                          "CRC mismatch"     数据损坏
     *                          "validCount mismatch" 非零像素数不一致
     *                          "depth out of range" 深度超出协议范围
     *
     * 线程安全：使用 flock(LOCK_SH) 与写端互斥
     */
    static DepthFrame parse(const QString &filePath);

private:
    static QString statusToString(int status);
};

#endif // DEPTHPARSER_H
