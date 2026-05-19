#include "depthParser.h"
#include "tof_frame_parser_core.h"
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>

QString DepthParser::statusToString(int status)
{
    return QString::fromLatin1(tof::parseStatusMessage(static_cast<tof::ParseStatus>(status)));
}

/* ── 帧解析 ──────────────────────────────────────────────── */
DepthFrame DepthParser::parse(const QString &filePath)
{
    DepthFrame frame{};
    frame.valid = false;

    /* 打开文件，flock 共享锁（与写端 LOCK_EX 互斥）*/
    int fd = open(filePath.toLocal8Bit().constData(), O_RDONLY);
    if (fd < 0) {
        frame.errorMsg = QStringLiteral("open failed: ") + filePath;
        return frame;
    }
    flock(fd, LOCK_SH);

    /* 读取固定长度帧 */
    uint8_t  buf[tof::kFrameSize];
    ssize_t  n = read(fd, buf, sizeof(buf));
    flock(fd, LOCK_UN);
    close(fd);

    if (n != static_cast<ssize_t>(tof::kFrameSize)) {
        frame.errorMsg = QString("short read: %1 bytes").arg((int)n);
        return frame;
    }

    tof::ParsedFrame parsed{};
    const tof::ParseStatus status = tof::parseFrameBuffer(buf, sizeof(buf), &parsed);
    if (status != tof::ParseStatus::Ok) {
        frame.errorMsg = statusToString(static_cast<int>(status));
        return frame;
    }

    frame.seq = parsed.seq;
    frame.validCount = parsed.validCount;
    for (int i = 0; i < 1024; ++i)
        frame.depths[i] = parsed.depths[i];

    frame.valid = true;
    return frame;
}
