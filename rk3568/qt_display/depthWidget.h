#ifndef DEPTHWIDGET_H
#define DEPTHWIDGET_H

#include <QWidget>
#include <QImage>
#include <cstdint>

// 32×32 深度图显示 Widget（伪彩色）
// 颜色映射：近 → 暖色（红/黄），远 → 冷色（蓝），无效(0) → 黑
class DepthWidget : public QWidget
{
    Q_OBJECT
public:
    explicit DepthWidget(QWidget *parent = nullptr);

    // 更新深度图（伪彩色），depths 为 1024 个距离值（mm），count 须为 1024
    void updateDepth(const uint16_t *depths, int count);

    // 更新有效像素图（灰度）：有返回→亮，无返回→黑
    void updateValidity(const uint16_t *depths, int count);

    // 设置伪彩色映射的最大量程（mm），默认 8450mm（PF32 极限）
    void setMaxRange(uint16_t mm);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    static QRgb depthToColor(float norm); // norm ∈ [0,1]

    QImage   m_image;
    uint16_t m_maxRange;
};

#endif // DEPTHWIDGET_H
