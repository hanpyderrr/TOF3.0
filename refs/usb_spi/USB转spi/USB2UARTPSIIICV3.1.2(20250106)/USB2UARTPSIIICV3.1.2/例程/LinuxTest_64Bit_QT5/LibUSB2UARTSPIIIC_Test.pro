#-------------------------------------------------
#
# Project created by QtCreator 2020-10-13T08:41:44
#
#-------------------------------------------------

QT       += core gui

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = LibUSB2UARTSPIIIC_Test
TEMPLATE = app


SOURCES += main.cpp\
        mainwindow.cpp

HEADERS  += mainwindow.h \
    USB2UARTSPIIICDLL.h

FORMS    += mainwindow.ui


INCLUDEPATH += $$PWD/.
DEPENDPATH += $$PWD/.

unix:!macx: LIBS += -L$$PWD/./ -lUSB2UARTSPIIIC

INCLUDEPATH += $$PWD/.
DEPENDPATH += $$PWD/.
