#ifndef TOF_FRAME_PARSER_CORE_H
#define TOF_FRAME_PARSER_CORE_H

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace tof {

static const uint32_t kFrameMagic = 0x50464F54u;
static const uint8_t kFrameVersion = 1;
static const uint8_t kHeaderSize = 16;
static const uint16_t kWidth = 32;
static const uint16_t kHeight = 32;
static const uint16_t kPixels = kWidth * kHeight;
static const uint16_t kMaxDepthMm = 8450;
static const size_t kFrameSize = 2070;

enum class ParseStatus {
    Ok,
    ShortRead,
    BadMagic,
    UnsupportedVersion,
    BadHeaderSize,
    BadDimensions,
    CrcMismatch,
    ValidCountMismatch,
    DepthOutOfRange,
};

struct ParsedFrame {
    uint32_t seq;
    uint16_t validCount;
    uint16_t depths[kPixels];
};

inline uint16_t readLe16(const uint8_t *p)
{
    return static_cast<uint16_t>(p[0]) | static_cast<uint16_t>(p[1] << 8);
}

inline uint32_t readLe32(const uint8_t *p)
{
    return static_cast<uint32_t>(p[0])
        | (static_cast<uint32_t>(p[1]) << 8)
        | (static_cast<uint32_t>(p[2]) << 16)
        | (static_cast<uint32_t>(p[3]) << 24);
}

inline uint16_t crc16Modbus(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit)
            crc = (crc & 1u) ? static_cast<uint16_t>((crc >> 1) ^ 0xA001u)
                             : static_cast<uint16_t>(crc >> 1);
    }
    return crc;
}

inline ParseStatus parseFrameBuffer(const uint8_t *buf, size_t len, ParsedFrame *out)
{
    if (len != kFrameSize)
        return ParseStatus::ShortRead;

    if (readLe32(buf) != kFrameMagic)
        return ParseStatus::BadMagic;

    if (buf[4] != kFrameVersion)
        return ParseStatus::UnsupportedVersion;

    if (buf[5] != kHeaderSize)
        return ParseStatus::BadHeaderSize;

    if (readLe16(buf + 12) != kWidth || readLe16(buf + 14) != kHeight)
        return ParseStatus::BadDimensions;

    const uint16_t expectedCrc = readLe16(buf + kFrameSize - 2);
    const uint16_t actualCrc = crc16Modbus(buf + 4, kFrameSize - 6);
    if (actualCrc != expectedCrc)
        return ParseStatus::CrcMismatch;

    ParsedFrame tmp;
    tmp.seq = readLe32(buf + 8);
    tmp.validCount = readLe16(buf + 16);

    uint16_t actualValid = 0;
    for (uint16_t i = 0; i < kPixels; ++i) {
        const uint16_t depth = readLe16(buf + 20 + i * 2);
        if (depth > kMaxDepthMm)
            return ParseStatus::DepthOutOfRange;
        if (depth != 0)
            ++actualValid;
        tmp.depths[i] = depth;
    }

    if (actualValid != tmp.validCount)
        return ParseStatus::ValidCountMismatch;

    if (out)
        std::memcpy(out, &tmp, sizeof(tmp));
    return ParseStatus::Ok;
}

inline const char *parseStatusMessage(ParseStatus status)
{
    switch (status) {
    case ParseStatus::Ok: return "ok";
    case ParseStatus::ShortRead: return "short read";
    case ParseStatus::BadMagic: return "bad magic";
    case ParseStatus::UnsupportedVersion: return "unsupported version";
    case ParseStatus::BadHeaderSize: return "bad header size";
    case ParseStatus::BadDimensions: return "bad dimensions";
    case ParseStatus::CrcMismatch: return "CRC mismatch";
    case ParseStatus::ValidCountMismatch: return "validCount mismatch";
    case ParseStatus::DepthOutOfRange: return "depth out of range";
    }
    return "unknown parse status";
}

} // namespace tof

#endif // TOF_FRAME_PARSER_CORE_H

