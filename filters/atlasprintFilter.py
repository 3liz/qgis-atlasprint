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

import re
import json
import os
import tempfile

from uuid import uuid4
from pathlib import Path
from configparser import ConfigParser

from qgis.server import QgsServerFilter
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import Qgis, QgsProject, QgsMessageLog, QgsExpression, QgsMasterLayoutInterface
from qgis.core import QgsLayoutItemMap, QgsLayoutExporter
from qgis.PyQt.QtCore import QByteArray


class AtlasPrintException(Exception):
    pass


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
        self.handler.setResponseHeader('Status', status)
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
            self.set_json_response('200', body)
            return

        # Check if needed params are set
        required = ['TEMPLATE', 'EXP_FILTER']
        if not all(elem in params for elem in required):
            body = {
                'status': 'fail',
                'message': 'Missing parameters: {} are required.'.format(' '.join(required))
            }
            self.set_json_response('400', body)
            return

        feature_filter = params['EXP_FILTER']

        scale = params.get('SCALE', None)

        # check expression
        expression = QgsExpression(feature_filter)
        if expression.hasParserError():
            body = {
                'status': 'fail',
                'message': 'An error occurred while parsing the given expression: {}'.format(expression.parserErrorString())
                }
            QgsMessageLog.logMessage('ERROR EXPRESSION: {}'.format(expression.parserErrorString()), 'atlasprint', Qgis.Critical)
            self.set_json_response('400', body)
            return

        # noinspection PyBroadException
        try:
            pdf_path = self.print_atlas(
                project_path=self.serverInterface().configFilePath(),
                layout_name=params['TEMPLATE'],
                scale=scale,
                feature_filter=feature_filter
            )
        except AtlasPrintException as e:
            body = {
                'status': 'fail',
                'message': 'ATLAS - Error from the user while generating the PDF: {}'.format(e)
            }
            QgsMessageLog.logMessage('User input error :{}'.format(e), 'atlasprint', Qgis.Info)
            self.set_json_response('400', body)
            return
        except Exception as e:
            body = {
                'status': 'fail',
                'message': 'ATLAS - Error while generating the PDF: {}'.format(e)
            }
            QgsMessageLog.logMessage('No PDF generated :{}'.format(e), 'atlasprint', Qgis.Critical)
            self.set_json_response('500', body)
            return

        # Send PDF
        self.handler.clear()
        self.handler.setResponseHeader('Content-type', 'application/pdf')
        self.handler.setResponseHeader('Status', '200')

        # noinspection PyBroadException
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
            self.set_json_response('500', body)
        finally:
            os.remove(pdf_path)

    @staticmethod
    def print_atlas(project_path, layout_name, feature_filter, scale=None):
        """Generate an atlas.

        :param project_path: Path to project to render as atlas.
        :type project_path: basestring

        :param layout_name: Name of the layout
        :type layout_name: basestring

        :param feature_filter: QGIS Expression to use to select the feature.
        It can return many features, a multiple pages PDF will be returned.
        :type feature_filter: basestring

        :param scale: A scale to force in the atlas context. Default to None.
        :type scale: int

        :return: Path to the PDF.
        :rtype: basestring
        """
        project = QgsProject()
        project.read(project_path)
        canvas = QgsMapCanvas()
        bridge = QgsLayerTreeMapCanvasBridge(
            project.layerTreeRoot(),
            canvas
        )
        bridge.setCanvasLayers()
        manager = project.layoutManager()
        master_layout = manager.layoutByName(layout_name)

        if not master_layout:
            raise AtlasPrintException('Layout not found')

        if master_layout.layoutType() != QgsMasterLayoutInterface.PrintLayout:
            raise AtlasPrintException('The layout is not a print layout')

        for l in manager.printLayouts():
            if l.name() == layout_name:
                layout = l
                break
        else:
            raise AtlasPrintException('The layout is not found')

        atlas = layout.atlas()

        if not atlas.enabled():
            raise AtlasPrintException('The layout is not enabled for an atlas')

        if scale:
            layout.referenceMap().setAtlasScalingMode(QgsLayoutItemMap.Fixed)
            layout.referenceMap().setScale(int(scale))

        # if layout.atlasScalingMode() == QgsLayoutItemMap.Predefined:
        #    QgsMessageLog.logMessage('Using predefined scale in project.', 'atlasprint', Qgis.Info)

        # Filter by FID as QGIS cannot compile expressions with $id or other $ vars
        # which leads to bad performance for big dataset
        use_fid = None
        if '$id' in feature_filter:
            ids = list(map(int, re.findall(r'\d+', feature_filter)))
            if len(ids) > 0:
                use_fid = ids[0]
        # if use_fid:
        #     qReq = QgsFeatureRequest().setFilterFid(use_fid)
        # else:
        #     qReq = QgsFeatureRequest().setFilterExpression(feature_filter)

        # Change feature_filter in order to improve performance
        coverage_layer = atlas.coverageLayer()
        pks = coverage_layer.dataProvider().pkAttributeIndexes()
        if use_fid and len(pks) == 1:
            pk = coverage_layer.dataProvider().fields()[pks[0]].name()
            feature_filter = '"{}" IN ({})'.format(pk, use_fid)
            QgsMessageLog.logMessage('feature_filter changed into: {}'.format(feature_filter), 'atlasprint', Qgis.Info)
            # qReq = QgsFeatureRequest().setFilterExpression(feature_filter)

        atlas.setFilterExpression(feature_filter)
        settings = QgsLayoutExporter.PdfExportSettings()
        export_path = os.path.join(
            tempfile.gettempdir(),
            '{}_{}.pdf'.format(layout_name, uuid4())
        )
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(atlas, export_path, settings)

        if result[0] != QgsLayoutExporter.Success and not os.path.isfile(export_path):
            raise AtlasPrintException('export not generated {}'.format(export_path))

        return export_path
