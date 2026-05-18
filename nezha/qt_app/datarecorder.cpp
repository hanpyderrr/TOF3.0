#include "datarecorder.h"

#include <QDataStream>
#include <QDir>
#include <QMutexLocker>
#include <QStorageInfo>

DataRecorder::DataRecorder(QObject *parent) : QObject(parent) {}

bool DataRecorder::open(const QString &dataDir)
{
    QMutexLocker lk(&m_mutex);
    if (m_file.isOpen())
        return false;

    m_dataDir = dataDir;
    QDir().mkpath(dataDir);

    const QString name = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss") + ".tof";
    m_file.setFileName(QDir(dataDir).filePath(name));

    if (!m_file.open(QIODevice::WriteOnly)) {
        return false;
    }

    m_file.write(kMagic, 8);
    m_frameCount = 0;
    return true;
}

void DataRecorder::record(const DepthFrame &frame)
{
    QMutexLocker lk(&m_mutex);
    if (!m_file.isOpen())
        return;

    const qint64 ts = QDateTime::currentMSecsSinceEpoch();

    // Frame record: seq(4) ts_ms(8) valid_count(2) depths(2048) = 2062 bytes, all LE
    auto write16 = [&](uint16_t v) { m_file.write(reinterpret_cast<const char*>(&v), 2); };
    auto write32 = [&](uint32_t v) { m_file.write(reinterpret_cast<const char*>(&v), 4); };
    auto write64 = [&](uint64_t v) { m_file.write(reinterpret_cast<const char*>(&v), 8); };

    write32(frame.seq);
    write64(static_cast<uint64_t>(ts));
    write16(frame.validCount);
    m_file.write(reinterpret_cast<const char*>(frame.depths), 2048);

    ++m_frameCount;
}

void DataRecorder::close()
{
    QMutexLocker lk(&m_mutex);
    if (!m_file.isOpen())
        return;

    m_file.flush();
    const QString path = m_file.fileName();
    const int count = m_frameCount;
    m_file.close();

    // Disk usage check
    if (!m_dataDir.isEmpty()) {
        QStorageInfo si(m_dataDir);
        const qint64 used = si.bytesTotal() - si.bytesFree();
        if (used > m_maxDiskBytes) {
            emit diskWarning(
                QString("Disk usage %1 GB exceeds limit %2 GB")
                    .arg(used / 1e9, 0, 'f', 1)
                    .arg(m_maxDiskBytes / 1e9, 0, 'f', 1));
        }
    }

    emit sessionClosed(path, count);
}

qint64 DataRecorder::fileSizeBytes() const
{
    QMutexLocker lk(const_cast<QMutex*>(&m_mutex));
    return m_file.isOpen() ? m_file.size() : 0;
}
