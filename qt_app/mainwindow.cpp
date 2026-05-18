#include "mainwindow.h"

#include <QCheckBox>
#include <QDateTime>
#include <QFont>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QPushButton>
#include <QSpacerItem>
#include <QTabWidget>
#include <QVBoxLayout>
#include <QWidget>

MainWindow::MainWindow(const QString &depthFile,
                       const QString &laserPort,
                       const QString &motorPort,
                       const QString &dataDir,
                       const QString &cloudUrl,
                       QWidget *parent)
    : QMainWindow(parent)
    , m_depthFile(depthFile)
    , m_dataDir(dataDir)
{
    setWindowTitle("TOF 3D Viewer");
    setMinimumSize(960, 640);

    // ── Laser serial ──────────────────────────────────────────
    if (!laserPort.isEmpty()) {
        m_laser = new LaserUart(this);
        if (m_laser->open(laserPort))
            m_laser->setExternalTrigger();
        connect(m_laser, &LaserUart::errorOccurred,
                this, [this](const QString &msg){ m_statusLabel->setText(msg); });
    }

    // ── Motor serial ──────────────────────────────────────────
    if (!motorPort.isEmpty()) {
        m_motor = new MotorUart(this);
        m_motor->open(motorPort);
        connect(m_motor, &MotorUart::errorOccurred,
                this, [this](const QString &msg){ m_statusLabel->setText(msg); });
    }

    // ── Feedback controller ───────────────────────────────────
    m_feedback = new FeedbackController(this);
    m_feedback->setLaserUart(m_laser);
    m_feedback->setMotorUart(m_motor);
    connect(m_feedback, &FeedbackController::laserLevelChanged,
            this, &MainWindow::onLaserLevelChanged);
    connect(m_feedback, &FeedbackController::statusMessage,
            this, &MainWindow::onFeedbackStatus);

    // ── DataRecorder ──────────────────────────────────────────
    m_recorder = new DataRecorder(this);
    connect(m_recorder, &DataRecorder::sessionClosed,
            this, &MainWindow::onRecordSessionClosed);
    connect(m_recorder, &DataRecorder::diskWarning,
            this, [this](const QString &msg){ m_statusLabel->setText(msg); });

    // ── CloudSyncer ───────────────────────────────────────────
    m_syncer = new CloudSyncer(this);
    m_syncer->setEndpoint(cloudUrl);
    m_syncer->setDataDir(dataDir);
    m_syncer->setEnabled(!cloudUrl.isEmpty() && !dataDir.isEmpty());
    connect(m_recorder, &DataRecorder::sessionClosed,
            this, [this](const QString &path, int count){
                m_syncer->enqueue(path, count);
            });
    connect(m_syncer, &CloudSyncer::uploadProgress,
            this, &MainWindow::onUploadProgress);
    connect(m_syncer, &CloudSyncer::uploadDone,
            this, [this](const QString &){ m_uploadLabel->setText("Upload: done"); });
    connect(m_syncer, &CloudSyncer::uploadError,
            this, [this](const QString &, const QString &e){
                m_uploadLabel->setText("Upload err: " + e.left(30));
            });
    connect(m_syncer, &CloudSyncer::onlineStatusChanged,
            this, &MainWindow::onOnlineStatusChanged);

    // ── Central widget ────────────────────────────────────────
    QWidget *central = new QWidget(this);
    QHBoxLayout *hLayout = new QHBoxLayout(central);
    hLayout->setContentsMargins(4, 4, 4, 4);
    hLayout->setSpacing(4);

    // Left: depth view + info
    QWidget *leftWidget = new QWidget(central);
    QVBoxLayout *leftLayout = new QVBoxLayout(leftWidget);
    leftLayout->setContentsMargins(0, 0, 0, 0);
    leftLayout->setSpacing(4);

    QTabWidget *viewTabs = new QTabWidget(leftWidget);
    m_depthWidget = new DepthWidget(viewTabs);
    m_depthWidget->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    m_pointCloudWidget = new PointCloudWidget(viewTabs);
    m_pointCloudWidget->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    viewTabs->addTab(m_depthWidget, "2D Depth");
    viewTabs->addTab(m_pointCloudWidget, "3D Cloud");
    viewTabs->setCurrentWidget(m_pointCloudWidget);
    leftLayout->addWidget(viewTabs);

    m_infoLabel = new QLabel("Initializing...", leftWidget);
    m_infoLabel->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    QFont monoFont;
    monoFont.setFamily("monospace");
    monoFont.setStyleHint(QFont::Monospace);
    monoFont.setPointSize(10);
    m_infoLabel->setFont(monoFont);
    m_infoLabel->setFixedHeight(28);
    leftLayout->addWidget(m_infoLabel);

    hLayout->addWidget(leftWidget);

    // Right: control panel
    QWidget *rightPanel = new QWidget(central);
    rightPanel->setFixedWidth(210);
    QVBoxLayout *rightLayout = new QVBoxLayout(rightPanel);
    rightLayout->setContentsMargins(4, 4, 4, 4);
    rightLayout->setSpacing(8);

    // Laser group
    QGroupBox *laserGroup = new QGroupBox("Laser", rightPanel);
    QVBoxLayout *laserLayout = new QVBoxLayout(laserGroup);
    laserLayout->addWidget(new QLabel(
        laserPort.isEmpty() ? "Port: disabled" : QString("Port: %1").arg(laserPort)));
    QCheckBox *laserAutoBox = new QCheckBox("Auto intensity");
    connect(laserAutoBox, &QCheckBox::toggled, this, &MainWindow::onLaserAutoToggled);
    laserLayout->addWidget(laserAutoBox);
    m_laserLevelLabel = new QLabel("Level: 50");
    laserLayout->addWidget(m_laserLevelLabel);
    QHBoxLayout *levelBtnLayout = new QHBoxLayout;
    QPushButton *btnLevelDown = new QPushButton("-");
    QPushButton *btnLevelUp   = new QPushButton("+");
    connect(btnLevelDown, &QPushButton::clicked, this, [this]() {
        if (!m_laser || !m_laser->isOpen()) return;
        uint8_t lvl = static_cast<uint8_t>(qMax(1, static_cast<int>(m_laser->currentLevel()) - 5));
        m_laser->setLevel(lvl);
        m_laserLevelLabel->setText(QString("Level: %1").arg(lvl));
    });
    connect(btnLevelUp, &QPushButton::clicked, this, [this]() {
        if (!m_laser || !m_laser->isOpen()) return;
        uint8_t lvl = static_cast<uint8_t>(qMin(200, static_cast<int>(m_laser->currentLevel()) + 5));
        m_laser->setLevel(lvl);
        m_laserLevelLabel->setText(QString("Level: %1").arg(lvl));
    });
    levelBtnLayout->addWidget(btnLevelDown);
    levelBtnLayout->addWidget(btnLevelUp);
    laserLayout->addLayout(levelBtnLayout);
    rightLayout->addWidget(laserGroup);

    // Motor group
    QGroupBox *motorGroup = new QGroupBox("Motor", rightPanel);
    QVBoxLayout *motorLayout = new QVBoxLayout(motorGroup);
    motorLayout->addWidget(new QLabel(
        motorPort.isEmpty() ? "Port: disabled" : QString("Port: %1").arg(motorPort)));
    QCheckBox *focusAutoBox = new QCheckBox("Auto focus");
    connect(focusAutoBox, &QCheckBox::toggled, this, &MainWindow::onFocusAutoToggled);
    motorLayout->addWidget(focusAutoBox);
    QGridLayout *motorBtnGrid = new QGridLayout;
    QPushButton *btnSlideFwd  = new QPushButton("Slide +");
    QPushButton *btnSlideBack = new QPushButton("Slide -");
    QPushButton *btnSlideFwdF = new QPushButton("Fine +");
    QPushButton *btnSlideBackF= new QPushButton("Fine -");
    connect(btnSlideFwd,   &QPushButton::clicked, this, [this](){ if (m_motor && m_motor->isOpen()) m_motor->slideForward(true); });
    connect(btnSlideBack,  &QPushButton::clicked, this, [this](){ if (m_motor && m_motor->isOpen()) m_motor->slideBack(true); });
    connect(btnSlideFwdF,  &QPushButton::clicked, this, [this](){ if (m_motor && m_motor->isOpen()) m_motor->slideForward(false); });
    connect(btnSlideBackF, &QPushButton::clicked, this, [this](){ if (m_motor && m_motor->isOpen()) m_motor->slideBack(false); });
    motorBtnGrid->addWidget(btnSlideFwd,   0, 0);
    motorBtnGrid->addWidget(btnSlideBack,  0, 1);
    motorBtnGrid->addWidget(btnSlideFwdF,  1, 0);
    motorBtnGrid->addWidget(btnSlideBackF, 1, 1);
    motorLayout->addLayout(motorBtnGrid);
    rightLayout->addWidget(motorGroup);

    // Record group
    QGroupBox *recordGroup = new QGroupBox("Record", rightPanel);
    QVBoxLayout *recordLayout = new QVBoxLayout(recordGroup);
    QCheckBox *recordBox = new QCheckBox("Record to disk");
    recordBox->setEnabled(!dataDir.isEmpty());
    connect(recordBox, &QCheckBox::toggled, this, &MainWindow::onRecordToggled);
    recordLayout->addWidget(recordBox);
    m_recordLabel = new QLabel("Stopped");
    m_recordLabel->setWordWrap(true);
    recordLayout->addWidget(m_recordLabel);
    m_uploadLabel = new QLabel(cloudUrl.isEmpty() ? "Upload: disabled" : "Upload: offline");
    m_uploadLabel->setWordWrap(true);
    recordLayout->addWidget(m_uploadLabel);
    rightLayout->addWidget(recordGroup);

    // Status group
    QGroupBox *statusGroup = new QGroupBox("Status", rightPanel);
    QVBoxLayout *statusLayout = new QVBoxLayout(statusGroup);
    m_statusLabel = new QLabel("Ready", statusGroup);
    m_statusLabel->setWordWrap(true);
    m_statusLabel->setAlignment(Qt::AlignTop | Qt::AlignLeft);
    statusLayout->addWidget(m_statusLabel);
    rightLayout->addWidget(statusGroup);

    rightLayout->addStretch();
    hLayout->addWidget(rightPanel);

    setCentralWidget(central);

    // ── Timer ─────────────────────────────────────────────────
    m_timer = new QTimer(this);
    m_timer->setInterval(100);
    connect(m_timer, &QTimer::timeout, this, &MainWindow::onTimer);
    m_timer->start();

    m_fpsTimer = QDateTime::currentMSecsSinceEpoch();
}

void MainWindow::onTimer()
{
    const DepthFrame frame = DepthParser::parse(m_depthFile);
    if (!frame.valid) {
        m_infoLabel->setText(frame.error);
        return;
    }

    if (frame.seq == m_lastSeq)
        return;

    m_lastSeq = frame.seq;
    ++m_frameCount;

    if (m_frameCount >= 20) {
        const qint64 now = QDateTime::currentMSecsSinceEpoch();
        const qint64 elapsed = now - m_fpsTimer;
        if (elapsed > 0)
            m_fps = 20000.0 / static_cast<double>(elapsed);
        m_frameCount = 0;
        m_fpsTimer = now;
    }

    m_depthWidget->setFrame(frame);
    m_pointCloudWidget->setFrame(frame);
    m_feedback->onFrame(frame);

    if (m_recorder->isRecording()) {
        m_recorder->record(frame);
        m_recordLabel->setText(
            QString("Rec: %1 frames\n%2 KB")
                .arg(m_recorder->frameCount())
                .arg(m_recorder->fileSizeBytes() / 1024));
    }

    const QString text = QString("seq:%1  valid:%2/1024  fps:%3")
                             .arg(frame.seq)
                             .arg(frame.validCount)
                             .arg(m_fps, 0, 'f', 1);
    m_infoLabel->setText(text);
}

void MainWindow::onLaserAutoToggled(bool checked)
{
    m_feedback->setLaserAutoEnabled(checked);
}

void MainWindow::onFocusAutoToggled(bool checked)
{
    m_feedback->setFocusAutoEnabled(checked);
}

void MainWindow::onLaserLevelChanged(int level)
{
    m_laserLevelLabel->setText(QString("Level: %1").arg(level));
}

void MainWindow::onFeedbackStatus(const QString &msg)
{
    m_statusLabel->setText(msg);
}

void MainWindow::onRecordToggled(bool checked)
{
    if (checked) {
        if (!m_recorder->open(m_dataDir)) {
            m_recordLabel->setText("Error: cannot open file");
        } else {
            m_recordLabel->setText("Recording...");
        }
    } else {
        m_recorder->close();
        m_recordLabel->setText("Stopped");
    }
}

void MainWindow::onRecordSessionClosed(const QString &path, int count)
{
    m_recordLabel->setText(
        QString("Saved: %1 frames\n%2")
            .arg(count)
            .arg(path.section('/', -1)));
}

void MainWindow::onUploadProgress(const QString &, int sent, int total)
{
    m_uploadLabel->setText(
        QString("Uploading: %1/%2").arg(sent).arg(total));
}

void MainWindow::onOnlineStatusChanged(bool online)
{
    if (!online)
        m_uploadLabel->setText("Upload: offline");
    else if (m_uploadLabel->text().startsWith("Upload: offline"))
        m_uploadLabel->setText("Upload: online");
}
