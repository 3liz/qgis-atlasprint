"""
***************************************************************************
    QGIS Server Plugin Filters: Add a new request to print a specific atlas
    feature
    ---------------------
    Date                 : October 2017
    Copyright            : (C) 2017 by Michaël Douchin - 3Liz
    Email                : mdouchin at 3liz dot com
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
import os

from pathlib import Path
from configparser import ConfigParser

from qgis.server import QgsServerFilter
from qgis.core import Qgis, QgsMessageLog, QgsExpression
from qgis.PyQt.QtCore import QByteArray

from .core import print_atlas, AtlasPrintException


class AtlasPrintFilter(QgsServerFilter):

    def __init__(self, server_iface):
        QgsMessageLog.logMessage('atlasprintFilter.init', 'atlasprint', Qgis.Info)
        super(AtlasPrintFilter, self).__init__(server_iface)

        self.server_iface = server_iface
        self.handler = None
        self.metadata = {}
        self.get_plugin_metadata()

        # QgsMessageLog.logMessage("atlasprintFilter end init", 'atlasprint', Qgis.Info)

    def get_plugin_metadata(self):
        """
        Get plugin metadata.
        """
        metadata_file = Path(__file__).resolve().parent.parent / 'metadata.txt'
        if metadata_file.is_file():
            config = ConfigParser()
            config.read(str(metadata_file))
            self.metadata['name'] = config.get('general', 'name')
            self.metadata['version'] = config.get('general', 'version')

    def set_json_response(self, status, body):
        """
        Set response with given parameters.
        """
        self.handler.clear()
        self.handler.setResponseHeader('Content-type', 'text/json')
        self.handler.setStatusCode(status)
        self.handler.appendBody(json.dumps(body).encode('utf-8'))

    # noinspection PyPep8Naming
    def responseComplete(self):
        """
        Send new response.
        """
        self.handler = self.server_iface.requestHandler()
        params = self.handler.parameterMap()

        # Check if needed params are passed
        # If not, do not change QGIS Server response
        service = params.get('SERVICE')
        if not service:
            return

        if service.lower() != 'wms':
            return

        # Check if getprintatlas request. If not, just send the response
        if 'REQUEST' not in params or params['REQUEST'].lower() not in ['getprintatlas', 'getcapabilitiesatlas']:
            return

        # Get capabilities
        if params['REQUEST'].lower() == 'getcapabilitiesatlas':
            body = {
                'status': 'success',
                'metadata': self.metadata
            }
            self.set_json_response(200, body)
            return

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
                project_path=self.serverInterface().configFilePath(),
                layout_name=params['TEMPLATE'],
                scale=scale,
                scales=scales,
                feature_filter=feature_filter
            )
        except AtlasPrintException as e:
            body = {
                'status': 'fail',
                'message': 'ATLAS - Error from the user while generating the PDF: {}'.format(e)
            }
            QgsMessageLog.logMessage('User input error :{}'.format(e), 'atlasprint', Qgis.Info)
            self.set_json_response(400, body)
            return
        except Exception as e:
            body = {
                'status': 'fail',
                'message': 'ATLAS - Error while generating the PDF: {}'.format(e)
            }
            QgsMessageLog.logMessage('No PDF generated :{}'.format(e), 'atlasprint', Qgis.Critical)
            self.set_json_response(500, body)
            return

        # Send PDF
        self.handler.clear()
        self.handler.setResponseHeader('Content-type', 'application/pdf')
        self.handler.setStatusCode(200)

        try:
            with open(pdf_path, 'rb') as f:
                loads = f.readlines()
                ba = QByteArray(b''.join(loads))
                self.handler.appendBody(ba)
        except Exception as e:
            QgsMessageLog.logMessage('PDF READING ERROR: {}'.format(e), 'atlasprint', Qgis.Critical)
            body = {
                'status': 'fail',
                'message': 'Error occurred while reading PDF file',
            }
            self.set_json_response(500, body)
        finally:
            os.remove(pdf_path)
