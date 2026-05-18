QT += core gui widgets serialport opengl network sql

CONFIG += c++17

TARGET = tof_viewer
TEMPLATE = app

INCLUDEPATH += ../acquisition

SOURCES += \
    main.cpp \
    mainwindow.cpp \
    depthparser.cpp \
    depthwidget.cpp \
    pointcloudwidget.cpp \
    laseruart.cpp \
    motoruart.cpp \
    feedbackcontroller.cpp \
    datarecorder.cpp \
    cloudsyncer.cpp

HEADERS += \
    mainwindow.h \
    depthparser.h \
    depthwidget.h \
    pointcloudwidget.h \
    laseruart.h \
    motoruart.h \
    feedbackcontroller.h \
    datarecorder.h \
    cloudsyncer.h
