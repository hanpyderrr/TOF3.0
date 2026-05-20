#include "mainwindow.h"
#include "depthWidget.h"
#include "depthParser.h"

#include <QDateTime>
#include <QDebug>
#include <QGuiApplication>
#include <QLabel>
#include <QPalette>
#include <QScreen>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>

MainWindow::MainWindow(const QString &framePath, QWidget *parent)
    : QMainWindow(parent)
    , m_framePath(framePath)
{
    auto *central = new QWidget(this);
    QPalette centralPalette = central->palette();
    centralPalette.setColor(QPalette::Window, Qt::black);
    central->setPalette(centralPalette);
    central->setAutoFillBackground(true);

    auto *layout = new QVBoxLayout(central);

    m_depth = new DepthWidget(central);
    m_status = new QLabel(QStringLiteral("waiting for depth frame"), central);
    m_status->setStyleSheet("font-size:16px; color:#ddd; background:#222; padding:4px;");
    m_status->setAlignment(Qt::AlignCenter);

    layout->addWidget(m_depth, 1);
    layout->addWidget(m_status, 0);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    setCentralWidget(central);

    const QList<QScreen *> screens = QGuiApplication::screens();
    if (!screens.isEmpty())
        resize(screens.at(0)->geometry().size());

    qInfo() << "qt_display: MainWindow framePath =" << m_framePath
            << "initial geometry =" << geometry();

    m_fpsT0 = QDateTime::currentMSecsSinceEpoch();
    m_timer = new QTimer(this);
    m_timer->setInterval(50);
    connect(m_timer, &QTimer::timeout, this, &MainWindow::onTimer);
    m_timer->start();
    qInfo() << "qt_display: polling timer started, interval =" << m_timer->interval() << "ms";
}

void MainWindow::onTimer()
{
    const DepthFrame f = DepthParser::parse(m_framePath);
    if (!f.valid) {
        static int failLogCounter = 0;
        if ((failLogCounter++ % 20) == 0)
            qWarning() << "qt_display: failed to read" << m_framePath << ":" << f.errorMsg;
        m_status->setText(QStringLiteral("no valid frame: ") + f.errorMsg);
        return;
    }

    if (m_haveLast && f.seq == m_lastSeq) {
        static int duplicateLogCounter = 0;
        if ((duplicateLogCounter++ % 100) == 0)
            qInfo() << "qt_display: received.dat readable, waiting for new seq =" << f.seq;
        return;
    }

    m_lastSeq = f.seq;
    m_haveLast = true;
    m_depth->updateDepth(f.depths, 1024);
    qInfo() << "qt_display: read frame from received.dat seq =" << f.seq
            << "valid =" << f.validCount;

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
