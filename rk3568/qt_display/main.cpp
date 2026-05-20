/*
 * RK3568 MIPI 屏实时深度图显示（本阶段 P-RT，文件桥）
 * 用法：./qt_display [received_dat_path]   默认 /tmp/received.dat
 *       与 spi_receiver 的输出路径须一致。
 * 运行平台沿用 legacy SinglePhoton207_5 启动环境（linuxfb，见 docs/realtime_display_plan.md）。
 */
#include "mainwindow.h"
#include <QApplication>
#include <QDebug>
#include <QGuiApplication>
#include <QScreen>
#include <QTimer>
#include <csignal>

int main(int argc, char *argv[])
{
    // 服务进程：脱离控制台 HUP（生产由 init 启动无 tty）
    signal(SIGHUP, SIG_IGN);
    QApplication app(argc, argv);
    const QString path = (argc > 1) ? QString::fromLocal8Bit(argv[1])
                                     : QStringLiteral("/tmp/received.dat");
    qInfo() << "qt_display: starting";
    qInfo() << "qt_display: frame path =" << path;
    qInfo() << "qt_display: platform =" << QGuiApplication::platformName();
    const QList<QScreen *> screens = QGuiApplication::screens();
    for (int i = 0; i < screens.size(); ++i)
        qInfo() << "qt_display: screen" << i << screens.at(i)->geometry();

    MainWindow w(path);
    w.setWindowFlags(w.windowFlags() | Qt::FramelessWindowHint);
    w.setWindowState(w.windowState() | Qt::WindowFullScreen);
    w.show();
    QTimer::singleShot(0, &w, [&w]() {
        w.setWindowState(w.windowState() | Qt::WindowFullScreen);
        w.showFullScreen();
        qInfo() << "qt_display: fullscreen requested after show, window geometry =" << w.geometry();
    });
    return app.exec();
}
