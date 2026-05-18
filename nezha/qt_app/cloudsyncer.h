#pragma once

#include <QNetworkAccessManager>
#include <QObject>
#include <QSqlDatabase>
#include <QString>
#include <QTimer>

class QNetworkReply;

class CloudSyncer : public QObject {
    Q_OBJECT

public:
    explicit CloudSyncer(QObject *parent = nullptr);
    ~CloudSyncer();

    void setEndpoint(const QString &baseUrl);
    void setDataDir(const QString &dir);
    void setEnabled(bool enabled);
    void enqueue(const QString &filePath, int frameCount);

    bool isOnline() const { return m_online; }

signals:
    void onlineStatusChanged(bool online);
    void uploadProgress(const QString &filePath, int sent, int total);
    void uploadDone(const QString &filePath);
    void uploadError(const QString &filePath, const QString &msg);

private slots:
    void onPollTimer();
    void onHealthReply(QNetworkReply *reply);
    void onUploadReply(QNetworkReply *reply);

private:
    struct UploadState {
        QString filePath;
        QString sessionId;
        int     frameTotal = 0;
        int     framesSent = 0;
    };

    void initDb();
    void checkHealth();
    void startNextUpload();
    bool readFrameBatch(const QString &filePath, int offset, int count,
                        QJsonArray &out, int &framesRead);
    void updateDbSent(const QString &filePath, int sent, bool done);

    QString               m_baseUrl;
    QString               m_dataDir;
    bool                  m_enabled = false;
    bool                  m_online  = false;
    bool                  m_uploading = false;

    QNetworkAccessManager m_nam;
    QTimer                m_pollTimer;
    QSqlDatabase          m_db;

    UploadState           m_current;

    static constexpr int kBatchSize = 50;
    static constexpr int kPollMs    = 30000;
};
