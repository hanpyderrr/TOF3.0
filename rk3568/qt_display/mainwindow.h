#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QString>
#include <cstdint>

class QTimer;
class QLabel;
class DepthWidget;

/*
 * RK3568 MIPI 屏实时深度图主窗口（本阶段 P-RT，文件桥）
 * 定时读 spi_receiver 写出的 received.dat（裸 TofFrame 2070B），按 seq 去重，
 * 解析后渲染到 DepthWidget。剔除旧 SinglePhoton207_5 的云/课题2/转台/电机。
 */
class MainWindow : public QMainWindow
{
    Q_OBJECT
public:
    explicit MainWindow(const QString &framePath, QWidget *parent = nullptr);

private slots:
    void onTimer();

private:
    QString      m_framePath;
    DepthWidget *m_depth    = nullptr;
    DepthWidget *m_validity = nullptr;
    QLabel      *m_status   = nullptr;
    QTimer      *m_timer = nullptr;

    uint32_t m_lastSeq = 0;
    bool     m_haveLast = false;
    int      m_frameCount = 0;
    qint64   m_fpsT0 = 0;
    double   m_fps = 0.0;
};

#endif // MAINWINDOW_H
