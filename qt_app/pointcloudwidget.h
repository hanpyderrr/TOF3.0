#pragma once

#include <QMatrix4x4>
#include <QOpenGLBuffer>
#include <QOpenGLShaderProgram>
#include <QOpenGLWidget>
#include <QPoint>

#include <vector>

#include "depthparser.h"

class PointCloudWidget : public QOpenGLWidget {
    Q_OBJECT

public:
    explicit PointCloudWidget(QWidget *parent = nullptr);
    ~PointCloudWidget() override;

    void setFrame(const DepthFrame &frame);

protected:
    void initializeGL() override;
    void resizeGL(int w, int h) override;
    void paintGL() override;
    void mousePressEvent(QMouseEvent *event) override;
    void mouseMoveEvent(QMouseEvent *event) override;
    void wheelEvent(QWheelEvent *event) override;

private:
    struct Vertex {
        float x;
        float y;
        float z;
        float r;
        float g;
        float b;
    };

    void rebuildVertices(const DepthFrame &frame);
    static void depthColor(uint16_t depth, float &r, float &g, float &b);

    QOpenGLShaderProgram m_program;
    QOpenGLBuffer m_vbo{QOpenGLBuffer::VertexBuffer};
    std::vector<Vertex> m_vertices;

    QMatrix4x4 m_projection;
    QPoint m_lastMouse;
    float m_rotX = -25.0f;
    float m_rotY = 35.0f;
    float m_zoom = 2.2f;
    bool m_ready = false;
};
