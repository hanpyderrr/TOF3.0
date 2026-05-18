#include "image.h"
#include <sys/file.h>
#include <unistd.h>
#include <QtEndian>
#include <QImage>
#include <QVector>
#include <QColor>
#include <QDebug>
#include <algorithm>
#include <cmath>
//构造函数
ImageProcessor::ImageProcessor() {}

// QImage ImageProcessor::processImage(const QByteArray &data)
// {
//     const int expectedSize = 32 * 32 * 2;
//     if (data.size() != expectedSize)
//     {
//         qDebug() << "数据长度错误 收到:" << data.size() << "字节，需要:" << expectedSize << "字节";
//         return QImage();
//     }

//     // 1. 原始数据解析
//     QVector<int> rawPixelData(1024);
//     const uint16_t *pixelArray = reinterpret_cast<const uint16_t*>(data.constData());

//     for (int i = 0; i < 1024; ++i)
//     {
//         uint16_t value = qFromBigEndian(pixelArray[i]);
//         rawPixelData[i] = static_cast<int>(value);
//     }

//     // 2. 创建32x32灰度图像（增加亮度）
//     QImage image(32, 32, QImage::Format_Grayscale8);
//     for (int y = 0; y < 32; ++y)
//     {
//         for (int x = 0; x < 32; ++x)
//         {
//             // 增加亮度：将原始值乘以1.5倍（但不超过255）
//             int adjustedValue = qMin(static_cast<int>(rawPixelData[(31 - y) * 32 + x] * 1.5), 255);
//             quint8 gray = static_cast<quint8>(qBound(0, adjustedValue, 255));
//             image.setPixelColor(x, y, QColor(gray, gray, gray));
//         }
//     }

//     // 3. 计算图像统计信息
//     int minValue = 255, maxValue = 0;
//     int brightPixelCount = 0;
//     const double localLightThreshold = 50.0; // 局部亮度阈值
//     const int minBrightPixels = 5;          // 视为有效亮区的最小亮像素数

//     for (int y = 0; y < 32; ++y)
//     {
//         for (int x = 0; x < 32; ++x)
//         {
//             quint8 pixel = image.pixelColor(x, y).red();
//             minValue = std::min(minValue, static_cast<int>(pixel));
//             maxValue = std::max(maxValue, static_cast<int>(pixel));
//             if (pixel > localLightThreshold) brightPixelCount++;
//         }
//     }

//     // 4. 判断处理模式
//     bool hasBrightArea = brightPixelCount >= minBrightPixels;
//     bool needsEnhancement = hasBrightArea && (maxValue - minValue) > 15; // 最小对比度阈值

//     // 5. 图像处理流程
//     QImage processedImage = image;

//     // 只在需要时应用中值滤波和对比度增强
//     if (needsEnhancement)
//     {
//         // 中值滤波去噪
//         QImage denoisedImage(32, 32, QImage::Format_Grayscale8);
//         for (int y = 0; y < 32; ++y) {
//             for (int x = 0; x < 32; ++x) {
//                 QVector<quint8> neighbors;
//                 for (int dy = -1; dy <= 1; ++dy) {
//                     for (int dx = -1; dx <= 1; ++dx) {
//                         int neighborX = qBound(0, x + dx, 31);
//                         int neighborY = qBound(0, y + dy, 31);
//                         neighbors.append(image.pixelColor(neighborX, neighborY).red());
//                     }
//                 }
//                 std::sort(neighbors.begin(), neighbors.end());
//                 quint8 medianValue = neighbors[4];
//                 denoisedImage.setPixelColor(x, y, QColor(medianValue, medianValue, medianValue));
//             }
//         }

//         // 对比度增强（增加亮度偏移）
//         // 在对比度拉伸前先增加基础亮度
//         int brightnessBoost = static_cast<int>((255 - maxValue) * 0.3); // 动态亮度提升
//         for (int y = 0; y < 32; ++y) {
//             for (int x = 0; x < 32; ++x) {
//                 quint8 pixel = denoisedImage.pixelColor(x, y).red();
//                 // 先增加基础亮度
//                 int boostedValue = qMin(pixel + brightnessBoost, 255);
//                 // 然后进行对比度拉伸
//                 int newValue = static_cast<int>((static_cast<float>(boostedValue - minValue) / (maxValue - minValue)) * 255);
//                 newValue = qBound(0, newValue, 255);
//                 denoisedImage.setPixelColor(x, y, QColor(newValue, newValue, newValue));
//             }
//         }
//         processedImage = denoisedImage;
//     }

//     // 6. 双线性插值扩展到64x64（保持亮度）
//     QImage enlargedImage(64, 64, QImage::Format_Grayscale8);
//     for (int y = 0; y < 64; ++y)
//     {
//         for (int x = 0; x < 64; ++x)
//         {
//             float srcX = x * 31.0f / 63.0f;
//             float srcY = y * 31.0f / 63.0f;

//             int x1 = static_cast<int>(std::floor(srcX));
//             int y1 = static_cast<int>(std::floor(srcY));
//             int x2 = std::min(x1 + 1, 31);
//             int y2 = std::min(y1 + 1, 31);

//             float xDiff = srcX - x1;
//             float yDiff = srcY - y1;

//             quint8 topLeft = processedImage.pixelColor(x1, y1).red();
//             quint8 topRight = processedImage.pixelColor(x2, y1).red();
//             quint8 bottomLeft = processedImage.pixelColor(x1, y2).red();
//             quint8 bottomRight = processedImage.pixelColor(x2, y2).red();

//             double interpolatedValue = topLeft * (1 - xDiff) * (1 - yDiff) +
//                                        topRight * xDiff * (1 - yDiff) +
//                                        bottomLeft * (1 - xDiff) * yDiff +
//                                        bottomRight * xDiff * yDiff;
//             // 轻微提升插值后的亮度
//             interpolatedValue = qMin(interpolatedValue * 1.1, 255.0);
//             quint8 newValue = static_cast<quint8>(qBound(0.0, interpolatedValue, 255.0));
//             enlargedImage.setPixelColor(x, y, QColor(newValue, newValue, newValue));
//         }
//     }

//     return enlargedImage;
// }

QImage ImageProcessor::processImage(const QByteArray &data)
{
    const double GAMMA = 0.9; // 伽马值，控制亮部分的增强程度
    const int expectedSize = 32 * 32 * 2;
    if (data.size() != expectedSize)
    {
        qDebug() << "数据长度错误 收到:" << data.size() << "字节，需要:" << expectedSize << "字节";
        return QImage();
    }

    // 1. 原始数据解析
    QVector<int> rawPixelData(1024);
    const uint16_t *pixelArray = reinterpret_cast<const uint16_t*>(data.constData());

    for (int i = 0; i < 1024; ++i)
    {
        uint16_t value = qFromBigEndian(pixelArray[i]);
        rawPixelData[i] = static_cast<int>(value);
    }

    // 2. 创建32x32灰度图像并应用伽马校正
    QImage image(32, 32, QImage::Format_ARGB32);
    for (int y = 0; y < 32; ++y)
    {
        for (int x = 0; x < 32; ++x)
        {
            // 读取原始值，并确保在合理范围内
            int grayValue = qBound(0, rawPixelData[(31 - y) * 32 + x], 255);

            // 应用伽马校正
            double normalized = grayValue / 255.0; // 归一化到 [0, 1]
            double corrected = pow(normalized, GAMMA) * 255; // 应用伽马转换
            grayValue = qBound(0, static_cast<int>(corrected), 255); // 限制在 [0, 255] 的范围内

            // 将校正后的值设置为RGBA值，透明度为255
            image.setPixel(x, y, qRgba(grayValue, grayValue, grayValue, 255));
        }
    }

    // 3. 双线性插值扩展到64x64（保持亮度）
    QImage enlargedImage(64, 64, QImage::Format_ARGB32);
    for (int y = 0; y < 64; ++y)
    {
        for (int x = 0; x < 64; ++x)
        {
            float srcX = x * 31.0f / 63.0f;
            float srcY = y * 31.0f / 63.0f;

            int x1 = static_cast<int>(std::floor(srcX));
            int y1 = static_cast<int>(std::floor(srcY));
            int x2 = std::min(x1 + 1, 31);
            int y2 = std::min(y1 + 1, 31);

            float xDiff = srcX - x1;
            float yDiff = srcY - y1;

            // 获取四个邻居像素的红色通道值
            quint8 topLeft = qRed(image.pixel(x1, y1));
            quint8 topRight = qRed(image.pixel(x2, y1));
            quint8 bottomLeft = qRed(image.pixel(x1, y2));
            quint8 bottomRight = qRed(image.pixel(x2, y2));

            // 进行双线性插值
            double interpolatedValue = topLeft * (1 - xDiff) * (1 - yDiff) +
                                       topRight * xDiff * (1 - yDiff) +
                                       bottomLeft * (1 - xDiff) * yDiff +
                                       bottomRight * xDiff * yDiff;

            // 轻微提升插值后的亮度
            interpolatedValue = qMin(interpolatedValue * 1.1, 255.0);
            quint8 newValue = static_cast<quint8>(qBound(0.0, interpolatedValue, 255.0));

            // 将新值设置为RGBA值，透明度为255
            enlargedImage.setPixel(x, y, qRgba(newValue, newValue, newValue, 255));
        }
    }

    return enlargedImage;
}
