#include <QApplication>
#include <QString>

#include "mainwindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    QString depthFile = "/tmp/depth.dat";
    QString laserPort;
    QString motorPort;
    QString dataDir;
    QString cloudUrl;

    for (int i = 1; i < argc; ++i) {
        const QString arg = argv[i];
        if (arg == "--depth-file" && i + 1 < argc)
            depthFile = argv[++i];
        else if (arg == "--laser-port" && i + 1 < argc)
            laserPort = argv[++i];
        else if (arg == "--motor-port" && i + 1 < argc)
            motorPort = argv[++i];
        else if (arg == "--data-dir" && i + 1 < argc)
            dataDir = argv[++i];
        else if (arg == "--cloud-url" && i + 1 < argc)
            cloudUrl = argv[++i];
    }

    MainWindow window(depthFile, laserPort, motorPort, dataDir, cloudUrl);
    window.show();
    return app.exec();
}
