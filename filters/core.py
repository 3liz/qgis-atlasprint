"""Core functions, outside of the QGIS Server context for printing atlas."""

import os
import re
import tempfile

from uuid import uuid4
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import Qgis, QgsProject, QgsMessageLog, QgsMasterLayoutInterface, QgsSettings
from qgis.core import QgsLayoutItemMap, QgsLayoutExporter

__copyright__ = 'Copyright 2019, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
__revision__ = '$Format:%H$'


class AtlasPrintException(Exception):
    """A wrong input from the user."""
    pass


def global_scales():
    """Read the global settings about predefined scales.

    :return: List of scales.
    :rtype: list
    """
    # Copied from QGIS source code
    default_scales = (
        '1:1000000,1:500000,1:250000,1:100000,1:50000,1:25000,'
        '1:10000,1:5000,1:2500,1:1000,1:500')

    settings = QgsSettings()
    scales_string = settings.value('Map/scales', default_scales)
    data = scales_string.split(',')
    scales = []
    for scale in data:
        item = scale.split(':')
        if len(item) != 2:
            continue
        scales.append(float(item[1]))
    return scales


def project_scales(project):
    """Read the project settings about project scales.

    It might be an empty list if the checkbox is not checked.
    Only for QGIS < 3.10.

    :param project: The QGIS project.
    :type project: QgsProject

    :return: Boolean if we use project scales and list of scales.
    :rtype: list
    """
    scales = []

    use_project = project.readBoolEntry('Scales', '/useProjectScales')
    if not use_project:
        return scales

    data = project.readListEntry('Scales', '/ScalesList')
    for scale in data[0]:
        item = scale.split(':')
        if len(item) != 2:
            continue
        scales.append(float(item[1]))

    return scales


def print_atlas(project_path, layout_name, feature_filter, scale=None):
    """Generate an atlas.

    :param project_path: Path to project to render as atlas.
    :type project_path: basestring

    :param layout_name: Name of the layout.
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

    #
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

    if layout.referenceMap().atlasScalingMode() == QgsLayoutItemMap.Predefined:
        if Qgis.QGIS_VERSION_INT >= 30900:
            use_project = project.useProjectScales()
            map_scales = project.mapScales()
        else:
            map_scales = project_scales(project)
            use_project = len(map_scales) == 0

        if not use_project or len(map_scales) == 0:
            QgsMessageLog.logMessage('Map scales not found in project, fetching predefined map scales in global config', 'atlasprint', Qgis.Info)
            map_scales = global_scales()

        if Qgis.QGIS_VERSION_INT >= 30900:
            settings.predefinedMapScales = map_scales
        else:
            layout.reportContext().setPredefinedScales(map_scales)

    export_path = os.path.join(
        tempfile.gettempdir(),
        '{}_{}.pdf'.format(layout_name, uuid4())
    )
    exporter = QgsLayoutExporter(layout)
    result = exporter.exportToPdf(atlas, export_path, settings)

    if result[0] != QgsLayoutExporter.Success and not os.path.isfile(export_path):
        raise Exception('export not generated {}'.format(export_path))

    return export_path
