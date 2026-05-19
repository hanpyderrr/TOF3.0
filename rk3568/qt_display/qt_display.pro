QT       += core gui widgets
CONFIG   += c++17
TARGET    = qt_display
TEMPLATE  = app

# 仅深度图实时显示。剔除 legacy 的 network/serialport/opengl/zlib
# （裸帧无 CRC32 不需 zlib；云/转台/电机不在本程序）。

SOURCES += \
    main.cpp \
    mainwindow.cpp \
    depthWidget.cpp \
    depthParser.cpp

HEADERS += \
    mainwindow.h \
    depthWidget.h \
    depthParser.h \
    tof_frame_parser_core.h

unix: target.path = /myApp/tof3/qt_display
!isEmpty(target.path): INSTALLS += target
