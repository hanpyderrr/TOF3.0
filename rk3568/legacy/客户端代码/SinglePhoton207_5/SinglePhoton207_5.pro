QT       += core gui network serialport opengl
LIBS += -lz

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG += c++17

# You can make your code fail to compile if it uses deprecated APIs.
# In order to do so, uncomment the following line.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

SOURCES += \
    ../../../TOF/RK3568端/cloudUploader.cpp \
    ../../../TOF/RK3568端/depthParser.cpp \
    ../../../TOF/RK3568端/depthWidget.cpp \
    ../../../TOF/RK3568端/pointCloudWidget.cpp \
    clientAliyun.cpp \
    clientGroup2.cpp \
    image.cpp \
    main.cpp \
    mainwindow.cpp \
    motorUart.cpp \
    turntableUart.cpp

HEADERS += \
    ../../../TOF/RK3568端/cloudUploader.h \
    ../../../TOF/RK3568端/depthParser.h \
    ../../../TOF/RK3568端/depthWidget.h \
    ../../../TOF/RK3568端/pointCloudWidget.h \
    ../../../TOF/RK3568端/tof_frame_parser_core.h \
    clientAliyun.h \
    clientGroup2.h \
    image.h \
    mainwindow.h \
    motorUart.h \
    turntableUart.h

INCLUDEPATH += ../../../TOF/RK3568端

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target
