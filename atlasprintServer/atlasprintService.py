"""
***************************************************************************
    QGIS Server Plugin Filters: Add a new request to print a specific atlas
    feature
    ---------------------
    Date                 : December 2019
    Copyright            : (C) 2019 by René-Luc D'Hont - 3Liz
    Email                : rldhont at 3liz dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import traceback
import json

from pathlib import Path
from configparser import ConfigParser

from typing import Dict

from qgis.core import (Qgis,
                       QgsMessageLog,
                       QgsExpression,
                       QgsProject)

from qgis.server import (QgsService,
                         QgsServerRequest,
                         QgsServerResponse)

from .core import print_atlas, AtlasPrintException


def write_json_response( data: Dict[str, str], response: QgsServerResponse, code: int = 200) -> None:
    """ Write data as json response
    """
    response.setStatusCode(code)
    response.setHeader("Content-Type", "application/json")
    response.write(json.dumps(data))



class AtlasPrintError(Exception):

    def __init__(self, code: int, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg
        self.code = code
        QgsMessageLog.logMessage("Atlas print request error %s: %s" % (code, msg),"atlasprint", Qgis.Critical)

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.code)


class AtlasPrintService(QgsService):

    def __init__(self, debug: bool = False) -> None:
        super().__init__()

        self.debugMode = debug

        self.metadata = {}
        self.get_plugin_metadata()


    def get_plugin_metadata(self):
        """
        Get plugin metadata.
        """
        metadata_file = Path(__file__).resolve().parent / 'metadata.txt'
        if metadata_file.is_file():
            config = ConfigParser()
            config.read(str(metadata_file))
            self.metadata['name'] = config.get('general', 'name')
            self.metadata['version'] = config.get('general', 'version')

    # QgsService inherited

    def name(self) -> str:
        """ Service name
        """
        return 'ATLAS'

    def version(self) -> str:
        """ Service version
        """
        return "1.0.0"

    def allowMethod(self, method: QgsServerRequest.Method) -> bool:
        """ Check supported HTTP methods
        """
        return method in (
            QgsServerRequest.GetMethod, QgsServerRequest.PostMethod)

    def executeRequest(self, request: QgsServerRequest, response: QgsServerResponse,
                       project: QgsProject) -> None:
        """ Execute a 'ATLAS' request
        """

        params = request.parameters()

        # noinspection PyBroadException
        try:
            reqparam = params.get('REQUEST', '').lower()

            if reqparam == 'getcapabilities':
                self.get_capabilities(params, response, project)
            elif reqparam == 'getprint':
                self.get_print(params, response, project)
            else:
                raise AtlasPrintError(
                    400,
                    "Invalid REQUEST parameter: must be one of GetCapabilities, GetPrint, found '{}'".format(reqparam))

        except AtlasPrintError as err:
            err.formatResponse(response)
        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n%s" % traceback.format_exc(), "atlasprint", Qgis.Critical)
            err = AtlasPrintError(500, "Internal 'atlasprint' service error")
            err.formatResponse(response)

    # Atlas Service request methods

    def get_capabilities(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get atlas capabilities based on metadata file
        """
        body = {
            'status': 'success',
            'metadata': self.metadata
        }
        write_json_response(body, response)
        return

    def get_print(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get print document
        """

        template = params.get('TEMPLATE')
        feature_filter = params.get('EXP_FILTER')
        scale = params.get('SCALE')
        scales = params.get('SCALES')

        try:
            if not template:
                raise AtlasPrintException('TEMPLATE is required')

            if not feature_filter:
                raise AtlasPrintException('EXP_FILTER is required')

            expression = QgsExpression(feature_filter)
            if expression.hasParserError():
                raise AtlasPrintException('Expression is invalid: {}'.format(expression.parserErrorString()))

            if scale and scales:
                raise AtlasPrintException('SCALE and SCALES can not be used together.')

            if scale:
                try:
                    scale = int(scale)
                except ValueError:
                    raise AtlasPrintException('Invalid number in SCALE.')

            if scales:
                try:
                    scales = [int(scale) for scale in scales.split(',')]
                except ValueError:
                    raise AtlasPrintException('Invalid number in SCALES.')

            pdf_path = print_atlas(
                project=project,
                layout_name=params['TEMPLATE'],
                scale=scale,
                scales=scales,
                feature_filter=feature_filter
            )
        except AtlasPrintException as e:
            raise AtlasPrintError(400, 'ATLAS - Error from the user while generating the PDF: {}'.format(e))
        except Exception:
            QgsMessageLog.logMessage("Unhandled exception:\n%s" % traceback.format_exc(), "atlasprint", Qgis.Critical)
            raise AtlasPrintError(500, "Internal 'atlasprint' service error")

        path = Path(pdf_path)
        if not path.exists():
            raise AtlasPrintError(404, "ATLAS PDF not found")

        # Send PDF
        response.setHeader('Content-type', 'application/pdf')
        response.setStatusCode(200)
        try:
            response.write(path.read_bytes())
            path.unlink()
        except Exception:
            QgsMessageLog.logMessage("Error occured while reading PDF file", 'atlasprint', Qgis.Critical)
            raise
