#pragma once

#include <QLabel>
#include <QMainWindow>
#include <QTimer>

#include "depthparser.h"
#include "depthwidget.h"
#include "laseruart.h"
#include "motoruart.h"
#include "feedbackcontroller.h"
#include "pointcloudwidget.h"
#include "datarecorder.h"
#include "cloudsyncer.h"

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(const QString &depthFile,
                        const QString &laserPort = QString(),
                        const QString &motorPort = QString(),
                        const QString &dataDir   = QString(),
                        const QString &cloudUrl  = QString(),
                        QWidget *parent = nullptr);

private slots:
    void onTimer();
    void onLaserAutoToggled(bool checked);
    void onFocusAutoToggled(bool checked);
    void onLaserLevelChanged(int level);
    void onFeedbackStatus(const QString &msg);
    void onRecordToggled(bool checked);
    void onRecordSessionClosed(const QString &path, int count);
    void onUploadProgress(const QString &path, int sent, int total);
    void onOnlineStatusChanged(bool online);

private:
    QString m_depthFile;
    QString m_dataDir;

    QTimer *m_timer = nullptr;
    DepthWidget *m_depthWidget = nullptr;
    PointCloudWidget *m_pointCloudWidget = nullptr;
    QLabel *m_infoLabel = nullptr;
    QLabel *m_laserLevelLabel = nullptr;
    QLabel *m_statusLabel = nullptr;
    QLabel *m_recordLabel = nullptr;
    QLabel *m_uploadLabel = nullptr;

    LaserUart *m_laser = nullptr;
    MotorUart *m_motor = nullptr;
    FeedbackController *m_feedback = nullptr;
    DataRecorder *m_recorder = nullptr;
    CloudSyncer  *m_syncer  = nullptr;

    uint32_t m_lastSeq = UINT32_MAX;
    int m_frameCount = 0;
    qint64 m_fpsTimer = 0;
    double m_fps = 0;
};
