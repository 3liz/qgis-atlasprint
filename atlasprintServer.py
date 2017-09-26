# -*- coding: utf-8 -*-
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

from qgis.core import QgsMessageLog, QgsLogger
from qgis.server import *

import os.path

class atlasprintServer:
    """Plugin for QGIS server
    this plugin loads atlasprint filter"""

    def __init__(self, serverIface):
        # Save reference to the QGIS server interface
        self.serverIface = serverIface
        QgsMessageLog.logMessage("SUCCESS - atlasprint init", 'plugin', QgsMessageLog.INFO)

        from filters.atlasprintFilter import atlasprintFilter
        try:
            serverIface.registerFilter( atlasprintFilter(serverIface), 50 )
        except Exception, e:
            QgsLogger.debug("atlasprint - Error loading filter atlasprint : %s" % e )

