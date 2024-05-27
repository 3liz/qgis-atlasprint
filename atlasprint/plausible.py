__copyright__ = 'Copyright 2024, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import json
import os
import platform

from qgis.core import Qgis, QgsNetworkAccessManager
from qgis.PyQt.QtCore import QByteArray, QDateTime, QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from atlasprint.logger import Logger
from atlasprint.tools import to_bool, version

MIN_SECONDS = 3600
ENV_SKIP_STATS = "3LIZ_SKIP_STATS"

PLAUSIBLE_DOMAIN_LIZCLOUD = "plugin.server.lizcloud"
PLAUSIBLE_DOMAIN_PROD = "plugin.server.lizmap.com"
PLAUSIBLE_URL_PROD = "https://bourbon.3liz.com/api/event"

PLAUSIBLE_DOMAIN_TEST = PLAUSIBLE_DOMAIN_PROD
PLAUSIBLE_URL_TEST = "https://plausible.snap.3liz.net/api/event"


# For testing purpose, to test.
# Similar to QGIS dashboard https://feed.qgis.org/metabase/public/dashboard/df81071d-4c75-45b8-a698-97b8649d7228
# We only collect data listed in the list below
# and the country according to IP address.
# The IP is not stored by Plausible Community Edition https://github.com/plausible/analytics
# Plausible is GDPR friendly https://plausible.io/data-policy
# The User-Agent is set by QGIS Desktop itself

class Plausible:

    def __init__(self):
        """ Constructor. """
        self.previous_date = None

    def request_stat_event(self) -> bool:
        """ Request to send an event to the API. """
        if to_bool(os.getenv(ENV_SKIP_STATS), default_value=False):
            # Disabled by environment variable
            return False

        if to_bool(os.getenv("CI"), default_value=False):
            # If running on CI, do not send stats
            return False

        current = QDateTime().currentDateTimeUtc()
        if self.previous_date and self.previous_date.secsTo(current) < MIN_SECONDS:
            # Not more than one request per hour
            # It's done at plugin startup anyway
            return False

        if self._send_stat_event():
            self.previous_date = current
            return True

        return False

    @staticmethod
    def _send_stat_event() -> bool:
        """ Send stats event to the API. """
        # Only turn ON for debug purpose, temporary !
        debug = False
        extra_debug = False

        atlas_plugin_version = version()
        if atlas_plugin_version in ('master', 'dev'):
            # Dev versions of the plugin, it's a kind of debug
            debug = True

        plausible_url = PLAUSIBLE_URL_TEST if debug else PLAUSIBLE_URL_PROD

        is_lizcloud = "lizcloud" in os.getenv("QGIS_SERVER_APPLICATION_NAME", "").lower()
        if is_lizcloud:
            plausible_domain = PLAUSIBLE_DOMAIN_LIZCLOUD
        else:
            plausible_domain = PLAUSIBLE_DOMAIN_TEST if debug else PLAUSIBLE_DOMAIN_PROD

        request = QNetworkRequest()
        # noinspection PyArgumentList
        request.setUrl(QUrl(plausible_url))
        if extra_debug:
            request.setRawHeader(b"X-Debug-Request", b"true")
            request.setRawHeader(b"X-Forwarded-For", b"127.0.0.1")
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        # Qgis.QGIS_VERSION → 3.34.6-Prizren
        # noinspection PyUnresolvedReferences
        qgis_version_full = Qgis.QGIS_VERSION.split('-')[0]
        # qgis_version_full → 3.34.6
        qgis_version_branch = '.'.join(qgis_version_full.split('.')[0:2])
        # qgis_version_branch → 3.34

        python_version_full = platform.python_version()
        # python_version_full → 3.10.12
        python_version_branch = '.'.join(python_version_full.split('.')[0:2])
        # python_version_branch → 3.10

        data = {
            "name": "atlasPrint-server",
            "props": {
                # Plugin version
                "plugin-version": atlas_plugin_version,
                # QGIS
                "qgis-version-full": qgis_version_full,
                "qgis-version-branch": qgis_version_branch,
                # Python
                "python-version-full": python_version_full,
                "python-version-branch": python_version_branch,
                # OS
                "os-name": platform.system(),
            },
            "url": plausible_url,
            "domain": plausible_domain,
        }

        # noinspection PyArgumentList
        r: QNetworkReply = QgsNetworkAccessManager.instance().post(request, QByteArray(str.encode(json.dumps(data))))
        if not is_lizcloud:
            return True

        logger = Logger()
        message = (
            f"Request HTTP OS process '{os.getpid()}' sent to '{plausible_url}' with domain '{plausible_domain} : ")
        if r.error() == QNetworkReply.NoError:
            logger.info(message + "OK")
        else:
            logger.warning(message + r.error())

        return True
