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

from typing import TYPE_CHECKING, cast

from qgis.server import QgsServerInterface

from .filter import AtlasPrintFilter
from .plausible import Plausible
from .service import AtlasPrintService
from .tools import version

from . import logger

if TYPE_CHECKING:
    from qgis.server import QgsServiceRegistry


class AtlasPrintServer:
    """Plugin for QGIS server
    this plugin loads AtlasPrint filter"""

    def __init__(self, server_iface: QgsServerInterface) -> None:
        self.server_iface = server_iface
        logger.info(f'Init server version "{version()}"')

        # noinspection PyBroadException
        try:
            self.plausible = Plausible()
            self.plausible.request_stat_event()
        except Exception as e:
            logger.log_exception(e)
            logger.critical("Error while calling the API stats")

        # Register service
        try:
            reg = cast("QgsServiceRegistry", server_iface.serviceRegistry())
            reg.registerService(AtlasPrintService())
        except Exception as e:
            logger.critical(f"Error loading filter AtlasPrint : {e}")
            raise

        # Add filter
        try:
            server_iface.registerFilter(AtlasPrintFilter(self.server_iface), 50)
        except Exception as e:
            logger.critical(f"Error loading filter AtlasPrint : {e}")
            raise
