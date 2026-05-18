#include "image.h"
#include <sys/file.h>
#include <unistd.h>
//构造函数
ImageProcessor::ImageProcessor() {}

QImage ImageProcessor::processImage(const QString& filePath)
{
    QFile dataFile(filePath);
    if (!dataFile.open(QIODevice::ReadOnly))
    {
        qDebug() << "Failed to open data file!";
        return QImage(); // 返回空图像
    }

    // 获取文件描述符并加锁
    int fd = dataFile.handle();
    if (flock(fd, LOCK_SH) != 0)
    {
        qDebug() << "Failed to lock file!";
        dataFile.close();
        return QImage(); // 返回空图像
    }

    // --------------------- 数据解析逻辑 ---------------------
    QTextStream stream(&dataFile);

    // 读取第一行并忽略
    QString frameLine = stream.readLine(); // 读取第一行(Frame=0)
    if (!frameLine.startsWith("Frame=")) // 可选的检查
    {
        qDebug() << "Invalid frame line!" << frameLine;
        flock(fd, LOCK_UN);
        dataFile.close();
        return QImage(); // 返回空图像
    }
    // 读取第二行数据
    QString rawDataLine = stream.readLine(); // 读取第二行包含32*32个数据
    QStringList dataList = rawDataLine.split(" ", Qt::SkipEmptyParts);  // 按空格分割

    // 检查数据数量是否足够
    if (dataList.size() < 1024)
    {
        qDebug() << "Data file has only" << dataList.size() << "numbers, need 1024!";
        flock(fd, LOCK_UN);
        dataFile.close();
        return QImage(); // 返回空图像
    }

    // 将字符串转换为整数
    QVector<int> rawPixelData; // 存储原始数据
    for (int i = 0; i < 1024; ++i)
    {
        bool ok;
        int value = dataList[i].toInt(&ok);
        if (!ok)
        {
            qDebug() << "Invalid data at position" << i << ":" << dataList[i];
            flock(fd, LOCK_UN);
            dataFile.close();
            return QImage(); // 返回空图像
        }
        rawPixelData.append(qBound(0, value, 255)); // 确保像素值在0-255之间
    }

    // 解锁并关闭文件
    flock(fd, LOCK_UN);
    dataFile.close();

    // 生成图像（上下翻转）
    QImage image(32, 32, QImage::Format_Grayscale8);
    for (int i = 0; i < 32; ++i)
    {
        for (int j = 0; j < 32; ++j)
        {
            int index = (31 - i) * 32 + j; // 上下翻转
            quint8 value = static_cast<quint8>(rawPixelData[index]);
            image.setPixel(j, i, qRgb(value, value, value));
        }
    }

    return image; // 返回生成的图像
}
