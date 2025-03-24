__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import traceback

from qgis.core import Qgis, QgsMessageLog

DEBUG = False

class Logger:

    def __init__(self):
        self.plugin = 'AtlasPrint'

    def debug(self, message):
        if not DEBUG:
            return
        QgsMessageLog.logMessage(f'DEBUG : {message}', self.plugin, Qgis.Info)

    def info(self, message):
        QgsMessageLog.logMessage(message, self.plugin, Qgis.Info)

    def warning(self, message):
        QgsMessageLog.logMessage(message, self.plugin, Qgis.Warning)

    def critical(self, message):
        QgsMessageLog.logMessage(message, self.plugin, Qgis.Critical)

    @staticmethod
    def log_exception(e: BaseException):
        """ Log a Python exception. """
        Logger().critical(
            "Critical exception:\n{e}\n{traceback}".format(
                e=e,
                traceback=traceback.format_exc(),
            ),
        )
