#include "mainwindow.h"
#include "depthWidget.h"
#include "depthParser.h"

#include <QWidget>
#include <QVBoxLayout>
#include <QLabel>
#include <QTimer>
#include <QDateTime>
#include <QGuiApplication>
#include <QScreen>

MainWindow::MainWindow(const QString &framePath, QWidget *parent)
    : QMainWindow(parent)
    , m_framePath(framePath)
{
    auto *central = new QWidget(this);
    auto *layout = new QVBoxLayout(central);

    m_depth = new DepthWidget(central);
    m_status = new QLabel(QStringLiteral("等待深度帧…"), central);
    m_status->setStyleSheet("font-size:16px; color:#ddd; background:#222; padding:4px;");
    m_status->setAlignment(Qt::AlignCenter);

    layout->addWidget(m_depth, 1);
    layout->addWidget(m_status, 0);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    setCentralWidget(central);
    setStyleSheet("background:#000;");

    // 适配 MIPI 屏：按屏幕几何铺满（板子 800×1280 竖屏）
    const QList<QScreen *> screens = QGuiApplication::screens();
    if (!screens.isEmpty())
        resize(screens.at(0)->geometry().size());

    m_fpsT0 = QDateTime::currentMSecsSinceEpoch();
    m_timer = new QTimer(this);
    m_timer->setInterval(50);   // 20Hz 轮询 received.dat；sim 2fps，余量大
    connect(m_timer, &QTimer::timeout, this, &MainWindow::onTimer);
    m_timer->start();
}

void MainWindow::onTimer()
{
    const DepthFrame f = DepthParser::parse(m_framePath);
    if (!f.valid) {
        m_status->setText(QStringLiteral("无有效帧: ") + f.errorMsg);
        return;
    }
    if (m_haveLast && f.seq == m_lastSeq)
        return;   // 无新帧

    m_lastSeq = f.seq;
    m_haveLast = true;
    m_depth->updateDepth(f.depths, 1024);

    if (++m_frameCount >= 20) {
        const qint64 now = QDateTime::currentMSecsSinceEpoch();
        const qint64 dt = now - m_fpsT0;
        if (dt > 0)
            m_fps = 20000.0 / static_cast<double>(dt);
        m_frameCount = 0;
        m_fpsT0 = now;
    }
    m_status->setText(QString("seq:%1  valid:%2/1024  fps:%3")
                          .arg(f.seq)
                          .arg(f.validCount)
                          .arg(m_fps, 0, 'f', 1));
}
