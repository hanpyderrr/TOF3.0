#include "feedbackcontroller.h"
#include "laseruart.h"
#include "motoruart.h"

FeedbackController::FeedbackController(QObject *parent) : QObject(parent) {}

void FeedbackController::setLaserUart(LaserUart *laser) { m_laser = laser; }
void FeedbackController::setMotorUart(MotorUart *motor) { m_motor = motor; }

void FeedbackController::setLaserAutoEnabled(bool enabled)
{
    m_laserAuto = enabled;
    if (!enabled)
        emit statusMessage("Laser auto: OFF");
}

void FeedbackController::setFocusAutoEnabled(bool enabled)
{
    m_focusAuto = enabled;
    if (!enabled)
        emit statusMessage("Focus auto: OFF");
}

void FeedbackController::onFrame(const DepthFrame &frame)
{
    ++m_framesSinceEval;
    if (m_framesSinceEval < EVAL_INTERVAL)
        return;
    m_framesSinceEval = 0;

    if (m_laserAuto && m_laser && m_laser->isOpen())
        evaluateLaser(frame);

    if (m_focusAuto && m_motor && m_motor->isOpen())
        evaluateFocus(frame);
}

void FeedbackController::evaluateLaser(const DepthFrame &frame)
{
    const float ratio = static_cast<float>(frame.validCount) / 1024.0f;

    if (ratio < TARGET_LOW - DEADBAND) {
        const uint8_t newLevel = static_cast<uint8_t>(
            qMin(static_cast<int>(m_laserLevel) + LEVEL_STEP, static_cast<int>(LEVEL_MAX)));
        if (newLevel != m_laserLevel) {
            m_laserLevel = newLevel;
            m_laser->setLevel(m_laserLevel);
            emit laserLevelChanged(m_laserLevel);
            emit statusMessage(QString("Laser level -> %1 (valid %2%)")
                                   .arg(m_laserLevel)
                                   .arg(static_cast<int>(ratio * 100)));
        }
    } else if (ratio > TARGET_HIGH + DEADBAND) {
        const uint8_t newLevel = static_cast<uint8_t>(
            qMax(static_cast<int>(m_laserLevel) - LEVEL_STEP, static_cast<int>(LEVEL_MIN)));
        if (newLevel != m_laserLevel) {
            m_laserLevel = newLevel;
            m_laser->setLevel(m_laserLevel);
            emit laserLevelChanged(m_laserLevel);
            emit statusMessage(QString("Laser level -> %1 (valid %2%)")
                                   .arg(m_laserLevel)
                                   .arg(static_cast<int>(ratio * 100)));
        }
    }
}

void FeedbackController::evaluateFocus(const DepthFrame &frame)
{
    const uint16_t avgDepth = computeAvgDepth(frame);
    if (avgDepth == 0) return;

    const int delta = static_cast<int>(avgDepth) - static_cast<int>(m_lastAvgDepth);

    // Stub: calibration table not yet available.
    // When |delta| exceeds threshold, report depth change.
    // Actual motor commands will be added after focus calibration.
    if (qAbs(delta) > static_cast<int>(FOCUS_THRESHOLD_MM)) {
        m_lastAvgDepth = avgDepth;
        emit statusMessage(QString("Focus: avg depth %1 mm (motor control pending calibration)")
                               .arg(avgDepth));
    }
}

uint16_t FeedbackController::computeAvgDepth(const DepthFrame &frame)
{
    if (frame.validCount == 0) return 0;

    uint64_t sum = 0;
    int count = 0;
    for (int i = 0; i < 1024; ++i) {
        if (frame.depths[i] > 0) {
            sum += frame.depths[i];
            ++count;
        }
    }
    return count > 0 ? static_cast<uint16_t>(sum / count) : 0;
}
