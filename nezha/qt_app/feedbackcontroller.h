#pragma once

#include <QObject>
#include "depthparser.h"

class LaserUart;
class MotorUart;

class FeedbackController : public QObject {
    Q_OBJECT
public:
    explicit FeedbackController(QObject *parent = nullptr);

    void setLaserUart(LaserUart *laser);
    void setMotorUart(MotorUart *motor);

    void setLaserAutoEnabled(bool enabled);
    void setFocusAutoEnabled(bool enabled);
    bool laserAutoEnabled() const { return m_laserAuto; }
    bool focusAutoEnabled() const { return m_focusAuto; }

    // Called on every new frame from MainWindow
    void onFrame(const DepthFrame &frame);

signals:
    void laserLevelChanged(int level);
    void statusMessage(const QString &msg);

private:
    void evaluateLaser(const DepthFrame &frame);
    void evaluateFocus(const DepthFrame &frame);
    static uint16_t computeAvgDepth(const DepthFrame &frame);

    LaserUart *m_laser = nullptr;
    MotorUart *m_motor = nullptr;

    bool m_laserAuto = false;
    bool m_focusAuto = false;

    int m_framesSinceEval = 0;

    // Laser control state
    uint8_t m_laserLevel = 50;

    // Focus control state (stub until calibration table added)
    uint16_t m_lastAvgDepth = 0;

    // Tuning constants
    static constexpr int   EVAL_INTERVAL   = 10;   // frames between evaluations
    static constexpr float TARGET_LOW      = 0.55f; // min acceptable valid ratio
    static constexpr float TARGET_HIGH     = 0.90f; // max acceptable valid ratio
    static constexpr float DEADBAND        = 0.05f;
    static constexpr uint8_t LEVEL_STEP    = 5;
    static constexpr uint8_t LEVEL_MIN     = 10;
    static constexpr uint8_t LEVEL_MAX     = 150;
    static constexpr uint16_t FOCUS_THRESHOLD_MM = 300; // depth change to trigger focus move
};
