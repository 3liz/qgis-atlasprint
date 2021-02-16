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

import json
import traceback

from pathlib import Path
from typing import Dict

from qgis.core import QgsExpression, QgsProject
from qgis.server import QgsServerRequest, QgsServerResponse, QgsService
from qgis.utils import pluginMetadata

from .core import AtlasPrintException, print_layout
from .logger import Logger

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


def write_json_response(data: Dict[str, str], response: QgsServerResponse, code: int = 200) -> None:
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
        Logger().critical("Atlas print request error {}: {}".format(code, msg))

    def formatResponse(self, response: QgsServerResponse) -> None:
        """ Format error response
        """
        body = {'status': 'fail', 'message': self.msg}
        response.clear()
        write_json_response(body, response, self.code)


class AtlasPrintService(QgsService):

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        _ = debug
        self.logger = Logger()

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
            self.logger.critical("Unhandled exception:\n{}".format(traceback.format_exc()))
            err = AtlasPrintError(500, "Internal 'atlasprint' service error")
            err.formatResponse(response)

    # Atlas Service request methods

    def get_capabilities(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get atlas capabilities based on metadata file
        """
        _ = params, project
        plugin_name = 'atlasprint'
        body = {
            'status': 'success',
            'metadata': {
                'name': plugin_name,
                'version': pluginMetadata(plugin_name, 'version'),
            }
        }
        write_json_response(body, response)
        return

    def get_print(self, params: Dict[str, str], response: QgsServerResponse, project: QgsProject) -> None:
        """ Get print document
        """

        template = params.get('TEMPLATE')
        feature_filter = params.get('EXP_FILTER', None)
        scale = params.get('SCALE')
        scales = params.get('SCALES')

        try:
            if not template:
                raise AtlasPrintException('TEMPLATE is required')

            if feature_filter:
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

            additional_params = {
                k: v for k, v in params.items() if k not in ['TEMPLATE', 'EXP_FILTER', 'SCALE', 'SCALES']
            }

            pdf_path = print_layout(
                project=project,
                layout_name=params['TEMPLATE'],
                scale=scale,
                scales=scales,
                feature_filter=feature_filter,
                **additional_params
            )
        except AtlasPrintException as e:
            raise AtlasPrintError(400, 'ATLAS - Error from the user while generating the PDF: {}'.format(e))
        except Exception:
            self.logger.critical("Unhandled exception:\n{}".format(traceback.format_exc()))
            raise AtlasPrintError(500, "Internal 'atlasprint' service error")

        path = Path(pdf_path)
        if not path.exists():
            raise AtlasPrintError(404, "ATLAS PDF not found")

        # Send PDF
        response.setHeader('Content-Type', 'application/pdf')
        response.setStatusCode(200)
        try:
            response.write(path.read_bytes())
            path.unlink()
        except Exception:
            self.logger.critical("Error occured while reading PDF file")
            raise
