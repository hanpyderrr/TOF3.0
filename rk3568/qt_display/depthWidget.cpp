#include "depthWidget.h"
#include <QDebug>
#include <QPainter>
#include <QSizePolicy>
#include <cmath>

static const int SENSOR_W = 32;
static const int SENSOR_H = 32;

namespace {
bool g_hasDepthFrame = false;
int g_paintCount = 0;
}

DepthWidget::DepthWidget(QWidget *parent)
    : QWidget(parent)
    , m_image(SENSOR_W, SENSOR_H, QImage::Format_RGB32)
    , m_maxRange(8450) // 8.45m = PF32 最大量程
{
    m_image.fill(Qt::black);
    setMinimumSize(SENSOR_W * 6, SENSOR_H * 6);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    setAutoFillBackground(false);
    setAttribute(Qt::WA_OpaquePaintEvent, true);
    setAttribute(Qt::WA_NoSystemBackground, true);
}

void DepthWidget::setMaxRange(uint16_t mm)
{
    m_maxRange = (mm == 0) ? 1 : mm;
}

// Jet 色图：norm=0(近)→红，norm=1(远)→蓝
QRgb DepthWidget::depthToColor(float norm)
{
    // Jet: 0→蓝, 0.25→青, 0.5→绿, 0.75→黄, 1→红
    // 我们把近距离映射到热色，远距离映射到冷色，反过来让"近=热"更直觉
    float v = 1.0f - norm; // 翻转：近 v→1, 远 v→0

    float r = 0.f, g = 0.f, b = 0.f;
    if      (v < 0.25f) { b = 1.f;          g = v * 4.f;                   }
    else if (v < 0.50f) { b = 1.f-(v-0.25f)*4.f; g = 1.f;                  }
    else if (v < 0.75f) { g = 1.f;          r = (v - 0.50f) * 4.f;         }
    else                { g = 1.f-(v-0.75f)*4.f; r = 1.f;                   }

    return qRgb(static_cast<int>(r * 255),
                static_cast<int>(g * 255),
                static_cast<int>(b * 255));
}

void DepthWidget::updateValidity(const uint16_t *depths, int count)
{
    if (count != SENSOR_W * SENSOR_H) return;
    g_hasDepthFrame = true;

    for (int row = 0; row < SENSOR_H; ++row) {
        for (int col = 0; col < SENSOR_W; ++col) {
            int pixIdx = (SENSOR_H - 1 - row) * SENSOR_W + col;
            // 近距离亮（白），远距离暗，无效黑——让用户一眼看到反射强弱
            // 有效像素（有光子返回）= 白，无返回 = 黑
            uint16_t d = depths[pixIdx];
            int v = (d > 0) ? 255 : 0;
            m_image.setPixel(col, row, qRgb(v, v, v));
        }
    }
    update();
}

void DepthWidget::updateDepth(const uint16_t *depths, int count)
{
    if (count != SENSOR_W * SENSOR_H) return;
    g_hasDepthFrame = true;

    for (int row = 0; row < SENSOR_H; ++row) {
        for (int col = 0; col < SENSOR_W; ++col) {
            // 与现有 2D 代码保持一致：垂直翻转显示
            int pixIdx = (SENSOR_H - 1 - row) * SENSOR_W + col;
            uint16_t d = depths[pixIdx];
            QRgb color;
            if (d == 0) {
                color = qRgb(40, 40, 40); // 无效像素：深灰
            } else {
                float norm = static_cast<float>(d) / m_maxRange;
                if (norm > 1.f) norm = 1.f;
                color = depthToColor(norm);
            }
            m_image.setPixel(col, row, color);
        }
    }
    update();
}

void DepthWidget::paintEvent(QPaintEvent *)
{
    if ((g_paintCount++ % 60) == 0)
        qInfo() << "qt_display: DepthWidget paintEvent"
                << "count =" << g_paintCount
                << "hasDepthFrame =" << g_hasDepthFrame
                << "rect =" << rect();

    QPainter painter(this);
    if (!g_hasDepthFrame) {
        painter.fillRect(rect(), QColor(24, 72, 128));
        const QRect proofRect(width() / 4, height() / 4, width() / 2, height() / 2);
        painter.fillRect(proofRect, QColor(0, 220, 80));
        return;
    }
    painter.drawImage(rect(), m_image);
}
