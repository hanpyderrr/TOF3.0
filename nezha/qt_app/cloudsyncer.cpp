#include "cloudsyncer.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QSqlError>
#include <QSqlQuery>
#include <QUrl>

static constexpr char kMagic[8] = {'T','O','F','R','E','C','1','\0'};
static constexpr int  kRecordBytes = 2062; // seq(4)+ts(8)+valid(2)+depths(2048)

CloudSyncer::CloudSyncer(QObject *parent) : QObject(parent)
{
    m_pollTimer.setInterval(kPollMs);
    connect(&m_pollTimer, &QTimer::timeout, this, &CloudSyncer::onPollTimer);
}

CloudSyncer::~CloudSyncer()
{
    if (m_db.isOpen())
        m_db.close();
}

void CloudSyncer::setEndpoint(const QString &baseUrl)
{
    m_baseUrl = baseUrl;
}

void CloudSyncer::setDataDir(const QString &dir)
{
    m_dataDir = dir;
    if (!dir.isEmpty()) {
        QDir().mkpath(dir);
        initDb();
    }
}

void CloudSyncer::setEnabled(bool enabled)
{
    m_enabled = enabled;
    if (enabled && !m_pollTimer.isActive())
        m_pollTimer.start();
    else if (!enabled)
        m_pollTimer.stop();
}

void CloudSyncer::enqueue(const QString &filePath, int frameCount)
{
    if (!m_db.isOpen())
        return;

    QSqlQuery q(m_db);
    q.prepare("INSERT OR IGNORE INTO queue (file_path, frame_count, created_at) "
              "VALUES (:p, :n, datetime('now'))");
    q.bindValue(":p", filePath);
    q.bindValue(":n", frameCount);
    q.exec();

    if (m_enabled && m_online && !m_uploading)
        startNextUpload();
}

void CloudSyncer::initDb()
{
    const QString dbPath = QDir(m_dataDir).filePath("upload_queue.db");
    m_db = QSqlDatabase::addDatabase("QSQLITE", "cloudsyncer");
    m_db.setDatabaseName(dbPath);
    if (!m_db.open())
        return;

    QSqlQuery q(m_db);
    q.exec("CREATE TABLE IF NOT EXISTS queue ("
           "id          INTEGER PRIMARY KEY AUTOINCREMENT,"
           "file_path   TEXT UNIQUE NOT NULL,"
           "frame_count INTEGER NOT NULL DEFAULT 0,"
           "frames_sent INTEGER NOT NULL DEFAULT 0,"
           "status      TEXT NOT NULL DEFAULT 'pending',"
           "created_at  TEXT NOT NULL,"
           "last_error  TEXT)");
}

void CloudSyncer::onPollTimer()
{
    if (!m_enabled)
        return;
    checkHealth();
}

void CloudSyncer::checkHealth()
{
    if (m_baseUrl.isEmpty())
        return;

    QNetworkRequest req(QUrl(m_baseUrl + "/api/health"));
    req.setAttribute(QNetworkRequest::User, QVariant("health"));
    QNetworkReply *reply = m_nam.get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        onHealthReply(reply);
    });
}

void CloudSyncer::onHealthReply(QNetworkReply *reply)
{
    reply->deleteLater();
    const bool online = (reply->error() == QNetworkReply::NoError &&
                         reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200);

    if (online != m_online) {
        m_online = online;
        emit onlineStatusChanged(online);
    }

    if (m_online && !m_uploading)
        startNextUpload();
}

void CloudSyncer::startNextUpload()
{
    if (!m_db.isOpen())
        return;

    QSqlQuery q(m_db);
    q.exec("SELECT file_path, frame_count, frames_sent FROM queue "
           "WHERE status = 'pending' ORDER BY created_at LIMIT 1");

    if (!q.next())
        return;

    m_current.filePath   = q.value(0).toString();
    m_current.frameTotal = q.value(1).toInt();
    m_current.framesSent = q.value(2).toInt();
    m_current.sessionId  = QFileInfo(m_current.filePath).completeBaseName();

    // Read next batch
    QJsonArray batch;
    int read = 0;
    if (!readFrameBatch(m_current.filePath, m_current.framesSent, kBatchSize, batch, read) ||
        batch.isEmpty()) {
        // File unreadable or exhausted
        updateDbSent(m_current.filePath, m_current.framesSent, true);
        return;
    }

    m_uploading = true;

    QJsonObject body;
    body["session_id"] = m_current.sessionId;
    body["frames"] = batch;

    QNetworkRequest req(QUrl(m_baseUrl + "/api/frames/depth"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    QNetworkReply *reply = m_nam.post(req, QJsonDocument(body).toJson(QJsonDocument::Compact));
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        onUploadReply(reply);
    });
}

void CloudSyncer::onUploadReply(QNetworkReply *reply)
{
    reply->deleteLater();
    m_uploading = false;

    if (reply->error() != QNetworkReply::NoError) {
        const QString err = reply->errorString();
        updateDbSent(m_current.filePath, m_current.framesSent, false);
        QSqlQuery q(m_db);
        q.prepare("UPDATE queue SET last_error = :e WHERE file_path = :p");
        q.bindValue(":e", err);
        q.bindValue(":p", m_current.filePath);
        q.exec();
        emit uploadError(m_current.filePath, err);
        return;
    }

    const QJsonObject resp = QJsonDocument::fromJson(reply->readAll()).object();
    const int accepted = resp["accepted"].toInt();
    m_current.framesSent += accepted;

    emit uploadProgress(m_current.filePath, m_current.framesSent, m_current.frameTotal);

    const bool done = (m_current.framesSent >= m_current.frameTotal);
    updateDbSent(m_current.filePath, m_current.framesSent, done);

    if (done)
        emit uploadDone(m_current.filePath);
    else if (m_online)
        startNextUpload();
}

bool CloudSyncer::readFrameBatch(const QString &filePath, int offset, int count,
                                  QJsonArray &out, int &framesRead)
{
    QFile f(filePath);
    if (!f.open(QIODevice::ReadOnly))
        return false;

    // Verify magic
    char magic[8];
    if (f.read(magic, 8) != 8 || memcmp(magic, kMagic, 8) != 0)
        return false;

    // Seek to offset frame
    const qint64 pos = 8 + static_cast<qint64>(offset) * kRecordBytes;
    if (!f.seek(pos))
        return false;

    framesRead = 0;
    for (int i = 0; i < count; ++i) {
        QByteArray rec = f.read(kRecordBytes);
        if (rec.size() < kRecordBytes)
            break;

        const uint8_t *d = reinterpret_cast<const uint8_t*>(rec.constData());
        uint32_t seq;       memcpy(&seq,       d,      4);
        uint64_t ts_ms;     memcpy(&ts_ms,     d + 4,  8);
        uint16_t valid;     memcpy(&valid,     d + 12, 2);
        QByteArray depths(reinterpret_cast<const char*>(d + 14), 2048);

        QJsonObject frame;
        frame["seq"]        = static_cast<qint64>(seq);
        frame["ts_ms"]      = static_cast<qint64>(ts_ms);
        frame["valid_count"]= static_cast<int>(valid);
        frame["depths_b64"] = QString::fromLatin1(depths.toBase64());
        out.append(frame);
        ++framesRead;
    }
    return true;
}

void CloudSyncer::updateDbSent(const QString &filePath, int sent, bool done)
{
    if (!m_db.isOpen())
        return;
    QSqlQuery q(m_db);
    if (done) {
        q.prepare("UPDATE queue SET frames_sent = :s, status = 'uploaded' WHERE file_path = :p");
    } else {
        q.prepare("UPDATE queue SET frames_sent = :s WHERE file_path = :p");
    }
    q.bindValue(":s", sent);
    q.bindValue(":p", filePath);
    q.exec();
}
