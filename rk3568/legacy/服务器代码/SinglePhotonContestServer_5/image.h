#ifndef IMAGE_H
#define IMAGE_H

#include <QImage>
#include <QVector>
#include <QString>
#include <QFile>
#include <QTextStream>
#include <QDebug>
#include <algorithm>

class ImageProcessor {
public:
    explicit ImageProcessor();
    QImage processImage(const QByteArray &data); //处理图像的函数（成一帧图像）

};

#endif
