#pragma once

#include <QWidget>
#include "depthparser.h"

class DepthWidget : public QWidget {
    Q_OBJECT
public:
    explicit DepthWidget(QWidget *parent = nullptr);
    void setFrame(const DepthFrame &frame);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    static QColor depthToColor(uint16_t depth);

    DepthFrame m_frame;
    bool m_hasFrame = false;
};
