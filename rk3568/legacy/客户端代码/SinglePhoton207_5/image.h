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
    ImageProcessor();//构造函数
    QImage processImage(const QString& filePath); //处理图像的函数（成一帧图像）

    //成像文件路径
    // QString imageFilePath = "/home/tsh/QT_test/image1/raw2.dat";//成像文件路径
    QString imageFilePath = "/myApp/mytest/spireceive/received.dat";//成像文件路径（文件中存放一帧图像数据）

};

#endif
