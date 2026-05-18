#pragma once
/*
 * depth_proto.h - TOF depth frame protocol shared by Nezha writer and RK3568 reader.
 *
 * v1 wire layout, little-endian, 2070 bytes:
 *   [0..3]    magic       0x50464F54 ("TOFP")
 *   [4]       version     1
 *   [5]       headerSize  16
 *   [6..7]    flags       0
 *   [8..11]   seq         frame counter
 *   [12..13]  width       32
 *   [14..15]  height      32
 *   [16..17]  validCount  non-zero depth pixels
 *   [18..19]  reserved    0
 *   [20..2067] depths     1024 x uint16 mm, 0 = invalid
 *   [2068..2069] crc16    CRC16-Modbus over bytes[4..2067]
 */
#include <stdint.h>
#include <string.h>

#define TOF_SENSOR_W    32
#define TOF_SENSOR_H    32
#define TOF_PIXELS      (TOF_SENSOR_W * TOF_SENSOR_H)
#define TOF_MAX_MM      8450
#define TOF_BIN_MM      8.25f

#ifndef TOF_DEPTH_FILE
#define TOF_DEPTH_FILE  "/tmp/depth.dat"
#endif

#define TOF_FRAME_MAGIC   0x50464F54u
#define TOF_FRAME_VERSION 1u
#define TOF_FRAME_HEADER_SIZE_FIELD 16u
#define TOF_FRAME_SIZE    2070
#define TOF_FRAME_HDR_SZ  20
#define TOF_FRAME_DATA_SZ (TOF_PIXELS * 2)
#define TOF_FRAME_CRC_SZ  2

#pragma pack(push, 1)
typedef struct {
    uint32_t magic;
    uint8_t  version;
    uint8_t  headerSize;
    uint16_t flags;
    uint32_t seq;
    uint16_t width;
    uint16_t height;
    uint16_t validCount;
    uint16_t reserved;
    uint16_t depths[TOF_PIXELS];
    uint16_t crc16;
} TofFrame;
#pragma pack(pop)

typedef char _tof_frame_size_check[sizeof(TofFrame) == TOF_FRAME_SIZE ? 1 : -1];

static inline uint16_t tof_crc16(const uint8_t *data, int len)
{
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < len; ++i) {
        crc ^= (uint8_t)data[i];
        for (int b = 0; b < 8; ++b)
            crc = (crc & 1u) ? (crc >> 1) ^ 0xA001u : (crc >> 1);
    }
    return crc;
}

static inline void tof_frame_seal(TofFrame *f)
{
    f->magic = TOF_FRAME_MAGIC;
    f->version = TOF_FRAME_VERSION;
    f->headerSize = TOF_FRAME_HEADER_SIZE_FIELD;
    f->flags = 0;
    f->width = TOF_SENSOR_W;
    f->height = TOF_SENSOR_H;
    f->reserved = 0;
    f->crc16 = tof_crc16((const uint8_t *)f + 4, TOF_FRAME_SIZE - 4 - TOF_FRAME_CRC_SZ);
}

static inline int tof_frame_verify(const TofFrame *f)
{
    if (f->magic != TOF_FRAME_MAGIC) return -1;
    if (f->version != TOF_FRAME_VERSION) return -2;
    uint16_t calc = tof_crc16((const uint8_t *)f + 4, TOF_FRAME_SIZE - 4 - TOF_FRAME_CRC_SZ);
    return (calc == f->crc16) ? 0 : -3;
}
