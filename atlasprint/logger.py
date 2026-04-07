import traceback

from qgis.core import Qgis, QgsMessageLog

PLUGIN = "AtlasPrint"


def info(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.Info)

def warning(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.Warning)

def critical(message: str):
    QgsMessageLog.logMessage(message, PLUGIN, Qgis.Critical)


debug = info
error = critical


def log_exception(e: BaseException):
    """ Log a Python exception. """
    critical(
        "Critical exception:\n{e}\n{traceback}".format(
            e=e,
            traceback=traceback.format_exc(),
        ),
    )
