"""Apply the map layers parameters of a request to the maps of a layout.

Like the WMS GetPrint request of QGIS Server, the request can provide for each map
of the layout `mapN:LAYERS`, `mapN:STYLES` and `mapN:OPACITIES`, where `N` is the
index of the map in the layout. Lizmap Web Client uses them to print the base layer
and the layers displayed in the web map.

As in QGIS Server, a map with a locked layer set keeps its own layers.

The project and its layouts are kept in the QGIS Server cache between requests,
so every change is reverted once the layout has been exported.
"""

import re

from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    List,
)

from qgis.core import (
    QgsLayerTreeGroup,
    QgsLayoutItemMap,
    QgsMapLayer,
    QgsProject,
)
from qgis.server import QgsServerProjectUtils

from . import logger

if TYPE_CHECKING:
    from qgis.core import QgsLayout

MAP_PARAMETER_REGEX = re.compile(r"^MAP(\d+):(LAYERS|STYLES|OPACITIES)$", re.IGNORECASE)


@dataclass
class MapLayersParameters:
    """Layers parameters for one map of the layout."""

    layers: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    opacities: List[str] = field(default_factory=list)


def is_map_parameter(key: str) -> bool:
    """Check if the request parameter is a map layers parameter."""
    return MAP_PARAMETER_REGEX.match(key) is not None


def parse_map_parameters(params: Dict[str, str]) -> Dict[int, MapLayersParameters]:
    """Read the `mapN:LAYERS`, `mapN:STYLES` and `mapN:OPACITIES` request parameters.

    :return: The layers parameters by map index, only for maps with layers.
    """
    map_parameters: Dict[int, MapLayersParameters] = {}
    for key, value in params.items():
        match = MAP_PARAMETER_REGEX.match(key)
        if not match:
            continue

        values = value.split(",") if value else []
        parameters = map_parameters.setdefault(int(match.group(1)), MapLayersParameters())
        setattr(parameters, match.group(2).lower(), values)

    return {index: parameters for index, parameters in map_parameters.items() if parameters.layers}


def _layer_short_name(layer: QgsMapLayer) -> str:
    """The layer short name, from the server properties since QGIS 3.38."""
    if hasattr(layer, "serverProperties") and hasattr(layer.serverProperties(), "shortName"):
        return layer.serverProperties().shortName()
    return layer.shortName()


def layers_by_wms_name(project: QgsProject) -> Dict[str, List[QgsMapLayer]]:
    """The project layers by WMS name, the same way as QGIS Server.

    A layer is named by its ID if the project uses layer IDs as WMS names, otherwise by its
    short name or its name. A group is named by its short name or its name, and gives its
    layers from the bottom to the top.
    """
    names: Dict[str, List[QgsMapLayer]] = {}

    root = project.layerTreeRoot()
    if root:
        for group in root.findGroups(True):
            if not isinstance(group, QgsLayerTreeGroup):
                continue
            short_name = group.customProperty("wmsShortName")
            group_layers = [node.layer() for node in group.findLayers() if node.layer()]
            # From the bottom to the top, as the layers in the LAYERS parameter
            names[short_name if short_name else group.name()] = list(reversed(group_layers))

    use_layer_ids = QgsServerProjectUtils.wmsUseLayerIds(project)
    for layer in project.mapLayers().values():
        if use_layer_ids:
            names[layer.id()] = [layer]
            continue
        short_name = _layer_short_name(layer)
        names[short_name if short_name else layer.name()] = [layer]

    return names


def layout_maps(layout: "QgsLayout") -> List[QgsLayoutItemMap]:
    """The maps of the layout, in the same order as QGIS Server for the mapN parameters."""
    return [item for item in layout.items() if isinstance(item, QgsLayoutItemMap)]


def apply_map_parameters(
    project: QgsProject,
    layout: "QgsLayout",
    map_parameters: Dict[int, MapLayersParameters],
    request_id: str = "",
) -> Callable[[], None]:
    """Apply the layers parameters to the maps of the layout.

    A map with a locked layer set is not changed. A map following a map theme
    does not follow it anymore, as in QGIS Server.

    :return: A function restoring the maps and the layers as they were before.
    """
    restore_functions: List[Callable[[], None]] = []

    def restore() -> None:
        while restore_functions:
            restore_functions.pop()()

    if not map_parameters:
        return restore

    names = layers_by_wms_name(project)
    maps = layout_maps(layout)

    for index, parameters in sorted(map_parameters.items()):
        if index >= len(maps):
            logger.info(f"Request-ID {request_id}, no map{index} in the layout, skipping its layers")
            continue

        layout_map = maps[index]
        if layout_map.keepLayerSet():
            logger.info(
                f"Request-ID {request_id}, the layers of map{index} `{layout_map.displayName()}` are locked, "
                f"keeping them"
            )
            continue

        # Layers from the bottom to the top, with their style and opacity
        layers: List[QgsMapLayer] = []
        style_overrides: Dict[str, str] = {}
        opacities: Dict[QgsMapLayer, float] = {}
        for position, name in enumerate(parameters.layers):
            if name not in names:
                logger.info(f"Request-ID {request_id}, layer `{name}` not found in the project, skipping")
                continue

            for layer in names[name]:
                if layer in layers:
                    continue
                layers.append(layer)

                style = parameters.styles[position] if position < len(parameters.styles) else ""
                style_manager = layer.styleManager()
                if style and style_manager and style in style_manager.styles():
                    style_overrides[layer.id()] = style_manager.style(style).xmlData()

                if position < len(parameters.opacities):
                    try:
                        opacities[layer] = int(parameters.opacities[position]) / 255
                    except ValueError:
                        logger.info(
                            f"Request-ID {request_id}, invalid opacity "
                            f"`{parameters.opacities[position]}` for layer `{name}`, skipping it"
                        )

        if not layers:
            logger.info(f"Request-ID {request_id}, no known layer for map{index}, keeping its layers")
            continue

        logger.info(
            f"Request-ID {request_id}, map{index} `{layout_map.displayName()}` uses the layers "
            f"{', '.join(parameters.layers)}"
        )

        # Save the map state to restore it after the export
        restore_functions.append(_map_restore_function(layout_map))

        layout_map.setFollowVisibilityPreset(False)
        # The layout map expects the layers from the top to the bottom
        layout_map.setLayers(list(reversed(layers)))
        layout_map.setKeepLayerSet(True)
        layout_map.setLayerStyleOverrides(style_overrides)
        layout_map.setKeepLayerStyles(bool(style_overrides))

        for layer, opacity in opacities.items():
            old_opacity = layer.opacity()
            if old_opacity == opacity:
                continue
            restore_functions.append(_opacity_restore_function(layer, old_opacity))
            layer.setOpacity(opacity)

        layout_map.invalidateCache()

    return restore


def _opacity_restore_function(layer: QgsMapLayer, opacity: float) -> Callable[[], None]:
    """Keep the opacity of a layer, to restore it later."""

    def restore() -> None:
        layer.setOpacity(opacity)

    return restore


def _map_restore_function(layout_map: QgsLayoutItemMap) -> Callable[[], None]:
    """Save the layers state of a layout map, to restore it later."""
    follow_preset = layout_map.followVisibilityPreset()
    follow_preset_name = layout_map.followVisibilityPresetName()
    keep_layer_set = layout_map.keepLayerSet()
    layers = layout_map.layers()
    keep_layer_styles = layout_map.keepLayerStyles()
    style_overrides = layout_map.layerStyleOverrides()

    def restore() -> None:
        layout_map.setLayers(layers)
        layout_map.setKeepLayerSet(keep_layer_set)
        layout_map.setLayerStyleOverrides(style_overrides)
        layout_map.setKeepLayerStyles(keep_layer_styles)
        layout_map.setFollowVisibilityPresetName(follow_preset_name)
        layout_map.setFollowVisibilityPreset(follow_preset)
        layout_map.invalidateCache()

    return restore
