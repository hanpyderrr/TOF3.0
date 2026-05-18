#pragma once

#include <cstdint>

#include <QString>

struct DepthFrame {
    uint32_t seq = 0;
    uint16_t validCount = 0;
    uint16_t depths[1024] = {};
    bool valid = false;
    QString error;
};

class DepthParser {
public:
    static DepthFrame parse(const QString &path);
};
