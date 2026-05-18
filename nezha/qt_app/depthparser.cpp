#include "depthparser.h"

#include "../acquisition/depth_proto.h"

#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

DepthFrame DepthParser::parse(const QString &path)
{
    DepthFrame result;
    uint8_t buffer[TOF_FRAME_SIZE] = {};

    const QByteArray pathBytes = path.toLocal8Bit();
    const int fd = open(pathBytes.constData(), O_RDONLY);
    if (fd < 0) {
        result.error = QString("open failed: %1").arg(path);
        return result;
    }

    if (flock(fd, LOCK_SH) != 0) {
        result.error = QString("flock failed: %1").arg(path);
        close(fd);
        return result;
    }

    const ssize_t bytesRead = read(fd, buffer, TOF_FRAME_SIZE);
    flock(fd, LOCK_UN);
    close(fd);

    if (bytesRead != TOF_FRAME_SIZE) {
        result.error = QString("read size mismatch: %1/%2").arg(bytesRead).arg(TOF_FRAME_SIZE);
        return result;
    }

    const TofFrame *frame = reinterpret_cast<const TofFrame *>(buffer);
    const int verifyResult = tof_frame_verify(frame);
    if (verifyResult != 0) {
        result.error = QString("frame verify failed: %1").arg(verifyResult);
        return result;
    }

    result.seq = frame->seq;
    result.validCount = frame->validCount;
    memcpy(result.depths, frame->depths, sizeof(result.depths));
    result.valid = true;
    return result;
}
