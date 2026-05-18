#include "pointcloudwidget.h"

#include <QMouseEvent>
#include <QOpenGLFunctions>
#include <QWheelEvent>

#include <algorithm>
#include <cmath>

static constexpr int kCols = 32;
static constexpr int kRows = 32;
static constexpr float kMaxDepth = 8450.0f;

static const char *kVertexShader = R"(
attribute vec3 a_position;
attribute vec3 a_color;
uniform mat4 u_mvp;
varying vec3 v_color;

void main()
{
    v_color = a_color;
    gl_Position = u_mvp * vec4(a_position, 1.0);
    gl_PointSize = 4.0;
}
)";

static const char *kFragmentShader = R"(
varying vec3 v_color;

void main()
{
    gl_FragColor = vec4(v_color, 1.0);
}
)";

PointCloudWidget::PointCloudWidget(QWidget *parent)
    : QOpenGLWidget(parent)
{
    setMinimumSize(256, 256);
}

PointCloudWidget::~PointCloudWidget()
{
    makeCurrent();
    m_vbo.destroy();
    doneCurrent();
}

void PointCloudWidget::setFrame(const DepthFrame &frame)
{
    rebuildVertices(frame);
    if (!m_ready)
        return;

    makeCurrent();
    m_vbo.bind();
    m_vbo.allocate(m_vertices.data(), static_cast<int>(m_vertices.size() * sizeof(Vertex)));
    m_vbo.release();
    doneCurrent();
    update();
}

void PointCloudWidget::initializeGL()
{
    QOpenGLFunctions *f = context()->functions();
    f->initializeOpenGLFunctions();
    f->glClearColor(0.02f, 0.025f, 0.035f, 1.0f);
    f->glEnable(GL_DEPTH_TEST);

    m_program.addShaderFromSourceCode(QOpenGLShader::Vertex, kVertexShader);
    m_program.addShaderFromSourceCode(QOpenGLShader::Fragment, kFragmentShader);
    m_program.bindAttributeLocation("a_position", 0);
    m_program.bindAttributeLocation("a_color", 1);
    m_program.link();

    m_vbo.create();
    m_vbo.setUsagePattern(QOpenGLBuffer::DynamicDraw);
    m_vbo.bind();
    m_vbo.allocate(nullptr, 0);
    m_vbo.release();

    m_ready = true;
}

void PointCloudWidget::resizeGL(int w, int h)
{
    m_projection.setToIdentity();
    m_projection.perspective(45.0f, h > 0 ? static_cast<float>(w) / static_cast<float>(h) : 1.0f, 0.01f, 20.0f);
}

void PointCloudWidget::paintGL()
{
    QOpenGLFunctions *f = context()->functions();
    f->glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    if (m_vertices.empty() || !m_program.bind())
        return;

    QMatrix4x4 view;
    view.translate(0.0f, 0.0f, -m_zoom);
    view.rotate(m_rotX, 1.0f, 0.0f, 0.0f);
    view.rotate(m_rotY, 0.0f, 1.0f, 0.0f);

    const QMatrix4x4 mvp = m_projection * view;
    m_program.setUniformValue("u_mvp", mvp);

    m_vbo.bind();
    m_program.enableAttributeArray(0);
    m_program.enableAttributeArray(1);
    m_program.setAttributeBuffer(0, GL_FLOAT, offsetof(Vertex, x), 3, sizeof(Vertex));
    m_program.setAttributeBuffer(1, GL_FLOAT, offsetof(Vertex, r), 3, sizeof(Vertex));
    f->glDrawArrays(GL_POINTS, 0, static_cast<GLsizei>(m_vertices.size()));
    m_program.disableAttributeArray(0);
    m_program.disableAttributeArray(1);
    m_vbo.release();
    m_program.release();
}

void PointCloudWidget::mousePressEvent(QMouseEvent *event)
{
    m_lastMouse = event->pos();
}

void PointCloudWidget::mouseMoveEvent(QMouseEvent *event)
{
    const QPoint delta = event->pos() - m_lastMouse;
    m_lastMouse = event->pos();
    m_rotY += delta.x() * 0.5f;
    m_rotX += delta.y() * 0.5f;
    m_rotX = std::max(-85.0f, std::min(85.0f, m_rotX));
    update();
}

void PointCloudWidget::wheelEvent(QWheelEvent *event)
{
    m_zoom *= event->angleDelta().y() > 0 ? 0.9f : 1.1f;
    m_zoom = std::max(0.8f, std::min(8.0f, m_zoom));
    update();
}

void PointCloudWidget::rebuildVertices(const DepthFrame &frame)
{
    m_vertices.clear();
    m_vertices.reserve(frame.validCount);

    for (int row = 0; row < kRows; ++row) {
        for (int col = 0; col < kCols; ++col) {
            const uint16_t depth = frame.depths[row * kCols + col];
            if (depth == 0)
                continue;

            const float z = -static_cast<float>(depth) / kMaxDepth;
            const float spread = 0.75f * -z;
            const float x = ((static_cast<float>(col) / (kCols - 1)) * 2.0f - 1.0f) * spread;
            const float y = (1.0f - (static_cast<float>(row) / (kRows - 1)) * 2.0f) * spread;

            Vertex v{};
            v.x = x;
            v.y = y;
            v.z = z;
            depthColor(depth, v.r, v.g, v.b);
            m_vertices.push_back(v);
        }
    }
}

void PointCloudWidget::depthColor(uint16_t depth, float &r, float &g, float &b)
{
    const float t = std::min(1.0f, static_cast<float>(depth) / kMaxDepth);
    const float nearT = 1.0f - t;

    if (nearT < 0.25f) {
        r = 0.0f; g = nearT * 4.0f; b = 1.0f;
    } else if (nearT < 0.5f) {
        r = 0.0f; g = 1.0f; b = 1.0f - (nearT - 0.25f) * 4.0f;
    } else if (nearT < 0.75f) {
        r = (nearT - 0.5f) * 4.0f; g = 1.0f; b = 0.0f;
    } else {
        r = 1.0f; g = 1.0f - (nearT - 0.75f) * 4.0f; b = 0.0f;
    }
}
