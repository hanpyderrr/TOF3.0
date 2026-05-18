#include "depthwidget.h"

#include <QPainter>
#include <algorithm>

static constexpr int COLS = 32;
static constexpr int ROWS = 32;
static constexpr uint16_t MAX_DEPTH = 8450; // mm, PF32 max unambiguous range

DepthWidget::DepthWidget(QWidget *parent) : QWidget(parent)
{
    setMinimumSize(256, 256);
}

void DepthWidget::setFrame(const DepthFrame &frame)
{
    m_frame = frame;
    m_hasFrame = true;
    update();
}

// Jet colormap: 0mm=black, near=blue, far=red
QColor DepthWidget::depthToColor(uint16_t depth)
{
    if (depth == 0)
        return Qt::black;

    const float t = std::min(1.0f, static_cast<float>(depth) / MAX_DEPTH);

    float r, g, b;
    if (t < 0.25f) {
        r = 0.0f; g = t * 4.0f; b = 1.0f;
    } else if (t < 0.5f) {
        r = 0.0f; g = 1.0f; b = 1.0f - (t - 0.25f) * 4.0f;
    } else if (t < 0.75f) {
        r = (t - 0.5f) * 4.0f; g = 1.0f; b = 0.0f;
    } else {
        r = 1.0f; g = 1.0f - (t - 0.75f) * 4.0f; b = 0.0f;
    }
    return QColor::fromRgbF(
        static_cast<qreal>(r),
        static_cast<qreal>(g),
        static_cast<qreal>(b));
}

void DepthWidget::paintEvent(QPaintEvent *)
{
    QPainter painter(this);
    painter.fillRect(rect(), Qt::black);

    if (!m_hasFrame)
        return;

    const int cellW = width() / COLS;
    const int cellH = height() / ROWS;

    for (int row = 0; row < ROWS; ++row) {
        for (int col = 0; col < COLS; ++col) {
            const uint16_t depth = m_frame.depths[row * COLS + col];
            painter.fillRect(col * cellW, row * cellH, cellW, cellH,
                             depthToColor(depth));
        }
    }
}
