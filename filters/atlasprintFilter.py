# -*- coding: utf-8 -*-

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
from qgis.server import *
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import QgsApplication, QgsProject, QgsComposition, QgsComposerMap, QgsMessageLog, QgsLogger
from PyQt4.QtCore import QFileInfo
from PyQt4.QtXml import QDomDocument
import os, sys
import tempfile
from uuid import uuid4

class atlasprintFilter(QgsServerFilter):

    def __init__(self, serverIface):
        QgsMessageLog.logMessage("atlasprintFilter.init")
        super(atlasprintFilter, self).__init__(serverIface)

        self.request = None
        self.project = None
        self.project_path = None
        self.debug_mode = True
        self.composer_name = None
        self.predefined_scales = [1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
        self.page_name_expression = None
        self.feature_filter = None

        self.tempdir = os.path.join( tempfile.gettempdir(), 'qgis_atlas_print' )
        if not os.path.exists(self.tempdir):
            os.mkdir( self.tempdir )
        QgsMessageLog.logMessage("atlasprintFilter.tempdir: %s" % self.tempdir)

    def setJsonResponse(self, status, body):
        '''
        Set response with given parameters
        '''
        self.request.clearHeaders()
        self.request.setInfoFormat('text/json')
        self.request.setHeader('Content-type', 'text/json')
        self.request.setHeader('Status', status)
        self.request.clearBody()
        self.request.appendBody( json.dumps( body ) )


    def responseComplete(self):
        self.request = self.serverIface.requestHandler()
        params = self.request.parameterMap( )

        # Check if needed params are passed
        # If not, do not change QGIS Server response
        if params['SERVICE'].lower() != 'wms':
            return

        # Check if getprint request with atlas parameter
        if 'REQUEST' not in params or params['REQUEST'].lower() != 'getprint':
            return

        # Check if atlas has been asked
        if 'ATLAS' not in params or params['ATLAS'] != 'true':
            return

        # Check if needed params are set
        if 'TEMPLATE' not in params or 'FORMAT' not in params or 'DPI' not in params or 'MAP' not in params or 'EXP_FILTER' not in params:
            body = {
                'status': 'fail',
                'message': 'Missing parameters: TEMPLATE, FORMAT, DPI, MAP, EXP_FILTER are required '
            }
            self.setJsonResponse( '200', body)
            return


        self.project_path = params['MAP']
        self.composer_name = params['TEMPLATE']
        self.feature_filter = params['EXP_FILTER']

        # check expression
        # todo

        pdf = self.print_atlas(
            project_path=self.project_path,
            composer_name=self.composer_name,
            predefined_scales=self.predefined_scales,
            feature_filter=self.feature_filter
        )

        # Send PDF
        self.request.clearHeaders()
        self.request.setInfoFormat('application/pdf')
        self.request.setHeader('Content-type', 'application/pdf')
        self.request.setHeader('Status', '200')
        self.request.clearBody()
        try:
            with open(pdf, 'rb') as f:
                loads = f.readlines()
            ba = QByteArray(b''.join(loads))
            self.request.appendBody(ba)
            return
        except:
            body = {
                'status': 'fail',
                'message': 'Error occured while reading PDF file',
            }
            self.setJsonResponse( '200', body)
            return
        finally:
            os.remove(pdf)



    def print_atlas(self, project_path, composer_name, predefined_scales, feature_filter=None, page_name_expression=None, ):

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
            return

        document = QDomDocument()
        document.setContent(composer_xml)


        # Get canvas, map setting & instantiate composition
        canvas = QgsMapCanvas()
        QgsProject.instance().read(QFileInfo(project_path))
        bridge = QgsLayerTreeMapCanvasBridge(
            QgsProject.instance().layerTreeRoot(),
            canvas
        )
        bridge.setCanvasLayers()
        ms = canvas.mapSettings()
        composition = QgsComposition(ms)

        # Load content from XML
        substitution_map = {}
        composition.loadFromTemplate(
            document,
            substitution_map
        )

        # Get atlas for this composition
        atlas = composition.atlasComposition()
        atlas.setEnabled(True)
        atlas_map = composition.getComposerMapById(0)
        atlas_map.setAtlasScalingMode( QgsComposerMap.Predefined )

        # get project scales
        atlas.setPredefinedScales(predefined_scales)
        atlas.setComposerMap(atlas_map)

        #on definit le filtre
        if feature_filter:
            atlas.setFilterFeatures(True)
            atlas.setFeatureFilter(feature_filter)
        if page_name_expression:
            atlas.setPageNameExpression(page_name_expression)

        # Set atlas mode
        composition.setAtlasMode(QgsComposition.ExportAtlas)

        # Generate atlas
        atlas.beginRender()
        uid = uuid4()
        for i in range(0, atlas.numFeatures()):
            atlas.prepareForFeature( i )
            export_path = os.path.join(
                tempfile.gettempdir(),
                '%s_%s.pdf' % (atlas.nameForPage(i), uid)
            )
            composition.exportAsPDF(export_path)

            break
        atlas.endRender()

        return export_path



    def requestReady(self):
        QgsMessageLog.logMessage("atlasprintFilter.requestReady")

    def sendResponse(self):
        QgsMessageLog.logMessage("atlasprintFilter.sendResponse")

    def responseComplete(self):
        QgsMessageLog.logMessage("atlasprintFilter.responseComplete")
