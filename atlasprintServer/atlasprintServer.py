"""
/***************************************************************************
    QGIS Server Plugin Filters: Add a new request to print a specific atlas
    feature
    ---------------------
    Date                 : October 2017
    Copyright            : (C) 2017 by Michaël Douchin - 3Liz
    Email                : mdouchin at 3liz dot com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'DOUCHIN Michaël'
__date__ = 'October 2017'
__copyright__ = '(C) 2017, DOUCHIN Michaël - 3Liz'

import os

from qgis.core import Qgis, QgsMessageLog
from qgis.server import QgsServerInterface

from .atlasprintService import AtlasPrintService
from .atlasprintFilter import AtlasPrintFilter


class AtlasPrintServer:
    """Plugin for QGIS server
    this plugin loads atlasprint filter"""

    def __init__(self, serverIface: 'QgsServerInterface') -> None:
        self.server_iface = serverIface
        QgsMessageLog.logMessage('SUCCESS - init', 'atlasprint', Qgis.Info)

        # debug
        debug = os.getenv('QGIS_SERVER_PRINTATLAS_DEBUG', '').lower() in ('1', 'yes', 'y', 'true')

        # Register service
        try:
            reg = serverIface.serviceRegistry()
            reg.registerService(AtlasPrintService(debug=debug))
        except Exception as e:
            QgsMessageLog.logMessage('Error loading filter atlasprint : {}'.format(e), 'atlasprint', Qgis.Critical)
            raise

        # Add filter
        try:
            serverIface.registerFilter(AtlasPrintFilter(self.server_iface), 50)
        except Exception as e:
            QgsMessageLog.logMessage('Error loading filter atlasprint : {}'.format(e), 'atlasprint', Qgis.Critical)
            raise

    def create_filter(self) -> AtlasPrintFilter:
        """Create a new filter instance - Used for tests
        """
        from .atlasprintFilter import AtlasPrintFilter
        return AtlasPrintFilter(self.server_iface)

    def createService(self, debug: bool = False) -> AtlasPrintService:
        """ Create  a new service instance

            Used for testing
        """
        return AtlasPrintService(debug=debug)
