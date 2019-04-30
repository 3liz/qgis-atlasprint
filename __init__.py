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
 This script initializes the plugin, making it known to QGIS and QGIS Server.
"""

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load atlasprint class from file atlasprint.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .atlasprint import atlasprint
    return atlasprint(iface)


def serverClassFactory(serverIface):  # pylint: disable=invalid-name
    """Load atlasprintServer class from file atlasprint.

    :param iface: A QGIS Server interface instance.
    :type iface: QgsServerInterface
    """
    from .atlasprintServer import atlasprintServer
    return atlasprintServer(serverIface)

