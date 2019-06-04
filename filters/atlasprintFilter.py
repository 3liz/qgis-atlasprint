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

import os, time, tempfile
from qgis.server import QgsServerFilter
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import Qgis, QgsProject, QgsMessageLog, QgsExpression, QgsFeatureRequest
from qgis.core import QgsLayout, QgsPrintLayout, QgsReadWriteContext, QgsLayoutItemMap, QgsLayoutExporter
from qgis.PyQt.QtCore import QFileInfo, QByteArray
from qgis.PyQt.QtXml import QDomDocument
import json, os, sys
import tempfile
import syslog
from uuid import uuid4

from pathlib import Path
from configparser import ConfigParser

class atlasprintFilter(QgsServerFilter):

    metadata = {}

    def __init__(self, serverIface):
        QgsMessageLog.logMessage("atlasprintFilter.init", 'atlasprint', Qgis.Info)
        super(atlasprintFilter, self).__init__(serverIface)

        self.serverIface = serverIface
        self.handler = None
        self.project = None
        self.project_path = None
        self.debug_mode = True
        self.composer_name = None
        self.predefined_scales = [
            500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000,
            2500000, 5000000, 10000000, 25000000, 50000000, 100000000, 250000000
        ]
        self.page_name_expression = None
        self.feature_filter = None

        self.getMetadata()

        #syslog.syslog(syslog.LOG_ERR, "ATLAS - INITIALIZE")

    def getMetadata(self):
        '''
        Get plugin metadata
        '''
        mfile = str(Path(__file__).resolve().parent.parent / 'metadata.txt')
        if os.path.isfile(mfile):
            config = ConfigParser()
            config.read(mfile)
            self.metadata = {
                'name': config.get('general', 'name'),
                'version': config.get('general', 'version')
            }

    def setJsonResponse(self, status, body):
        '''
        Set response with given parameters
        '''
        self.handler.clear()
        self.handler.setResponseHeader('Content-type', 'text/json')
        self.handler.setResponseHeader('Status', status)
        self.handler.appendBody( json.dumps( body ).encode('utf-8') )

    def responseComplete(self):
        '''
        Send new response
        '''
        self.handler = self.serverIface.requestHandler()
        params = self.handler.parameterMap( )

        # Check if needed params are passed
        # If not, do not change QGIS Server response
        if params['SERVICE'].lower() != 'wms':
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
            self.setJsonResponse( '200', body)
            return

        # Check if needed params are set
        if 'TEMPLATE' not in params or 'FORMAT' not in params or 'DPI' not in params or 'MAP' not in params or 'EXP_FILTER' not in params:
            body = {
                'status': 'fail',
                'message': 'Missing parameters: TEMPLATE, FORMAT, DPI, MAP, EXP_FILTER are required '
            }
            self.setJsonResponse( '200', body)
            return


        self.project_path = self.serverInterface().configFilePath()
        self.composer_name = params['TEMPLATE']
        self.feature_filter = params['EXP_FILTER']

        # check expression
        qExp = QgsExpression(self.feature_filter)
        if not qExp.hasParserError():
            qReq = QgsFeatureRequest(qExp)
            qReq.setLimit(1)
            ok = True
        else:
            body = {
                'status': 'fail',
                'message': 'An error occured while parsing the given expression: %s' % qExp.parserErrorString()
            }
            syslog.syslog(syslog.LOG_ERR, "ATLAS - ERROR EXPRESSION: %s" % qExp.parserErrorString())
            self.setJsonResponse( '200', body)
            return

        try:
            pdf = self.print_atlas(
                project_path=self.project_path,
                composer_name=self.composer_name,
                predefined_scales=self.predefined_scales,
                feature_filter=self.feature_filter
            )
        except:
            pdf = None

        if not pdf:
            body = {
                'status': 'fail',
                'message': 'ATLAS - Error while generating the PDF'
            }
            QgsMessageLog.logMessage("ATLAS - No PDF generated in %s" % pdf, 'atlasprint', Qgis.Info)
            self.setJsonResponse( '200', body)
            return

        # Send PDF
        self.handler.clear()
        self.handler.setResponseHeader('Content-type', 'application/pdf')
        self.handler.setResponseHeader('Status', '200')
        try:
            with open(pdf, 'rb') as f:
                loads = f.readlines()
                ba = QByteArray(b''.join(loads))
                self.handler.appendBody(ba)
        except:
            body = {
                'status': 'fail',
                'message': 'Error occured while reading PDF file',
            }
            self.setJsonResponse( '200', body)
        finally:
            os.remove(pdf)

        return




    def print_atlas(self, project_path, composer_name, predefined_scales, feature_filter=None, page_name_expression=None ):
        if not feature_filter:
            QgsMessageLog.logMessage("atlasprint: NO feature_filter provided !", 'atlasprint', Qgis.Info)
            return None

        # Get composer from project
        # in QGIS 2, canno get composers without iface
        # so we reading project xml and extract composer
        # in QGIS 3.0, we will use  project layoutManager()
        from xml.etree import ElementTree as ET
        composer_xml = None
        with open(project_path, 'r') as f:
            tree  = ET.parse(f)
            for elem in tree.findall('.//Composer[@title="%s"]' % composer_name):
                composer_xml = ET.tostring(
                    elem,
                    encoding='utf8',
                    method='xml'
                )
            if not composer_xml:
                for elem in tree.findall('.//Layout[@name="%s"]' % composer_name):
                    composer_xml = ET.tostring(
                        elem,
                        encoding='utf8',
                        method='xml'
                    )

        if not composer_xml:
            QgsMessageLog.logMessage("atlasprint: Composer XML not parsed !", 'atlasprint', Qgis.Info)
            return None

        document = QDomDocument()
        document.setContent(composer_xml)


        # Get canvas, map setting & instantiate composition
        canvas = QgsMapCanvas()
        project = QgsProject()
        project.read(project_path)
        bridge = QgsLayerTreeMapCanvasBridge(
            project.layerTreeRoot(),
            canvas
        )
        bridge.setCanvasLayers()

        layout = QgsPrintLayout(project)

        # Load content from XML
        layout.loadFromTemplate(
            document,
            QgsReadWriteContext(),
        )

        atlas = layout.atlas()
        atlas.setEnabled(True)

        atlas_map = layout.referenceMap()
        atlas_map.setAtlasDriven(True)
        atlas_map.setAtlasScalingMode( QgsLayoutItemMap.Predefined )

        layout.reportContext().setPredefinedScales(predefined_scales)

        if page_name_expression:
            atlas.setPageNameExpression(page_name_expression)

        # Filter feature here to avoid QGIS looping through every feature when doing : composition.setAtlasMode(QgsComposition.ExportAtlas)
        coverageLayer = atlas.coverageLayer()

        # Filter by FID as QGIS cannot compile expressions with $id or other $ vars
        # which leads to bad perfs for big datasets
        useFid = None
        if '$id' in feature_filter:
            import re
            ids = list(map(int, re.findall(r'\d+', feature_filter)))
            if len(ids) > 0:
                useFid = ids[0]
        if useFid:
            qReq = QgsFeatureRequest().setFilterFid(useFid)
        else:
            qReq = QgsFeatureRequest().setFilterExpression(feature_filter)

        # Change feature_filter in order to improve perfs
        pks = coverageLayer.dataProvider().pkAttributeIndexes()
        if useFid and len(pks) == 1:
            pk = coverageLayer.dataProvider().fields()[pks[0]].name()
            feature_filter = '"%s" IN (%s)' % (pk, useFid)
            QgsMessageLog.logMessage("atlasprint: feature_filter changed into: %s" % feature_filter, 'atlasprint', Qgis.Info)
            qReq = QgsFeatureRequest().setFilterExpression(feature_filter)
        atlas.setFilterFeatures(True)
        atlas.setFilterExpression(feature_filter)
        uid = uuid4()
        i = 0

        atlas.beginRender()
        atlas.seekTo(i)

        # setup settings
        settings = QgsLayoutExporter.PdfExportSettings()
        export_path = os.path.join(
                tempfile.gettempdir(),
                '%s_%s.pdf' % (atlas.nameForPage(i), uid)
        )
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToPdf(export_path, settings)

        atlas.endRender()
        if result != QgsLayoutExporter.Success:
            QgsMessageLog.logMessage("atlasprint: export not generated %s" % export_path, 'atlasprint', Qgis.Info)
            return None

        if not os.path.isfile(export_path):
            QgsMessageLog.logMessage("atlasprint: export not generated %s" % export_path, 'atlasprint', Qgis.Info)
            return None

        QgsMessageLog.logMessage("atlasprint: path generated %s" % export_path, 'atlasprint', Qgis.Info)
        return export_path
