#pragma once

#include <QDateTime>
#include <QFile>
#include <QMutex>
#include <QObject>
#include <QString>

#include "depthparser.h"

class DataRecorder : public QObject {
    Q_OBJECT

public:
    explicit DataRecorder(QObject *parent = nullptr);

    bool open(const QString &dataDir);
    void record(const DepthFrame &frame);
    void close();

    bool isRecording() const { return m_file.isOpen(); }
    int frameCount() const { return m_frameCount; }
    qint64 fileSizeBytes() const;
    QString currentPath() const { return m_file.fileName(); }

    void setMaxDiskGB(double gb) { m_maxDiskBytes = static_cast<qint64>(gb * 1e9); }

signals:
    void sessionClosed(const QString &filePath, int frameCount);
    void diskWarning(const QString &msg);

private:
    static constexpr char kMagic[8] = {'T','O','F','R','E','C','1','\0'};

    QFile   m_file;
    QMutex  m_mutex;
    int     m_frameCount = 0;
    qint64  m_maxDiskBytes = 10LL * 1000 * 1000 * 1000;
    QString m_dataDir;
};
