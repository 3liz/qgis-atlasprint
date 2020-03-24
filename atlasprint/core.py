"""Core functions, outside of the QGIS Server context for printing atlas."""

import os
import tempfile

from uuid import uuid4

from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge
from qgis.core import (
    Qgis,
    QgsProject,
    QgsMessageLog,
    QgsMasterLayoutInterface,
    QgsSettings,
    QgsLayoutItemMap,
    QgsLayoutExporter,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
)
from qgis.PyQt.QtCore import QVariant


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


def print_atlas(project, layout_name, feature_filter, scales=None, scale=None, **kwargs):
    """Generate an atlas.

    :param project: The project to render as atlas.
    :type project: QgsProject

    :param layout_name: Name of the layout.
    :type layout_name: basestring

    :param feature_filter: QGIS Expression to use to select the feature.
    It can return many features, a multiple pages PDF will be returned.
    :type feature_filter: basestring

    :param scale: A scale to force in the atlas context. Default to None.
    :type scale: int

    :param scales: A list of predefined list of scales to force in the atlas context.
    Default to None.
    :type scales: list

    :return: Path to the PDF.
    :rtype: basestring
    """
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

    settings = QgsLayoutExporter.PdfExportSettings()

    if scale:
        layout.referenceMap().setAtlasScalingMode(QgsLayoutItemMap.Fixed)
        layout.referenceMap().setScale(scale)

    if scales:
        layout.referenceMap().setAtlasScalingMode(QgsLayoutItemMap.Predefined)
        if Qgis.QGIS_VERSION_INT >= 30900:
            settings.predefinedMapScales = scales
        else:
            layout.reportContext().setPredefinedScales(scales)
    
    for key, value in kwargs.items():
        QgsMessageLog.logMessage('Additional parameters: %s = %s' % (key, value), 'atlasprint', Qgis.Info)
        if layout.itemById(key.lower()):
            item = layout.itemById(key.lower())
            item.setText(value)

    layer = atlas.coverageLayer()
    feature_filter = optimize_expression(layer, feature_filter)

    expression = QgsExpression(feature_filter)
    if expression.hasParserError():
        raise AtlasPrintException('Expression is invalid, parser error: {}'.format(expression.parserErrorString()))

    context = QgsExpressionContext()
    context.appendScope(QgsExpressionContextUtils.globalScope())
    context.appendScope(QgsExpressionContextUtils.projectScope(project))
    context.appendScope(QgsExpressionContextUtils.layoutScope(layout))
    context.appendScope(QgsExpressionContextUtils.atlasScope(atlas))
    context.appendScope(QgsExpressionContextUtils.layerScope(layer))

    expression.prepare(context)
    if expression.hasEvalError():
        raise AtlasPrintException('Expression is invalid, eval error: {}'.format(expression.evalErrorString()))

    atlas.setFilterFeatures(True)
    atlas.setFilterExpression(feature_filter)

    if not scales and layout.referenceMap().atlasScalingMode() == QgsLayoutItemMap.Predefined:
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


def optimize_expression(layer, expression):
    """Check if we can optimize the expression.

    https://github.com/3liz/qgis-atlasprint/issues/23
    """
    if expression.find('$id') < 0:
        return expression

    primary_keys = layer.primaryKeyAttributes()
    if len(primary_keys) != 1:
        return expression

    field = layer.fields().at(0)
    if field.type() != QVariant.Int:
        return expression

    expression = expression.replace('$id', '"{}"'.format(field.name()))
    # noinspection PyTypeChecker,PyCallByClass
    QgsMessageLog.logMessage('$id has been replaced by "{}"'.format(field.name()), 'atlasprint', Qgis.Info)

    return expression
