import io

from PIL import Image

from qgis.core import QgsLayoutItemMap, QgsMapLayer, QgsMapThemeCollection, QgsProject

from atlasprint.map_layers import (
    MapLayersParameters,
    apply_map_parameters,
    is_map_parameter,
    layers_by_wms_name,
    layout_maps,
    parse_map_parameters,
)

from .core.client import Client

PROJECT_ATLAS_SIMPLE = "atlas_simple.qgs"
LAYOUT = "layout1-atlas"


def _set_short_name(layer: QgsMapLayer, short_name: str):
    if hasattr(layer, "serverProperties") and hasattr(layer.serverProperties(), "setShortName"):
        layer.serverProperties().setShortName(short_name)
    else:
        layer.setShortName(short_name)


def _layer(project: QgsProject, name: str) -> QgsMapLayer:
    return project.mapLayersByName(name)[0]


def _main_map(project: QgsProject) -> QgsLayoutItemMap:
    return layout_maps(project.layoutManager().layoutByName(LAYOUT))[0]


def test_is_map_parameter():
    assert is_map_parameter("MAP0:LAYERS")
    assert is_map_parameter("map0:STYLES")
    assert is_map_parameter("map12:opacities")
    assert not is_map_parameter("MAP0:EXTENT")
    assert not is_map_parameter("LAYERS")
    assert not is_map_parameter("MAP")
    assert not is_map_parameter("simple_label")


def test_parse_map_parameters():
    params = {
        "MAP0:LAYERS": "OpenStreetMap,lines",
        "map0:STYLES": "default,défaut",
        "MAP0:OPACITIES": "204,255",
        # No layers for map1: nothing to apply
        "MAP1:STYLES": "default",
        "MAP2:LAYERS": "lines",
        "TEMPLATE": "layout1-atlas",
    }
    assert parse_map_parameters(params) == {
        0: MapLayersParameters(
            layers=["OpenStreetMap", "lines"],
            styles=["default", "défaut"],
            opacities=["204", "255"],
        ),
        2: MapLayersParameters(layers=["lines"]),
    }
    assert parse_map_parameters({"MAP0:LAYERS": ""}) == {}
    assert parse_map_parameters({}) == {}


def test_layers_by_wms_name(client: Client):
    project = client.get_project(PROJECT_ATLAS_SIMPLE)
    names = layers_by_wms_name(project)
    assert {name: [layer.name() for layer in layers] for name, layers in names.items()} == {
        "OpenStreetMap": ["OpenStreetMap"],
        "lines": ["lines"],
    }

    # The short name replaces the name
    _set_short_name(_layer(project, "OpenStreetMap"), "osm")
    # A group gives its layers, from the bottom to the top
    group = project.layerTreeRoot().addGroup("All layers")
    group.addLayer(_layer(project, "lines"))
    group.addLayer(_layer(project, "OpenStreetMap"))
    group.setCustomProperty("wmsShortName", "all")

    names = layers_by_wms_name(project)
    assert {name: [layer.name() for layer in layers] for name, layers in names.items()} == {
        "all": ["OpenStreetMap", "lines"],
        "osm": ["OpenStreetMap"],
        "lines": ["lines"],
    }


def test_apply_map_parameters(client: Client):
    project = client.get_project(PROJECT_ATLAS_SIMPLE)
    layout = project.layoutManager().layoutByName(LAYOUT)
    main_map = _main_map(project)
    osm = _layer(project, "OpenStreetMap")
    lines = _layer(project, "lines")

    assert not main_map.keepLayerSet()
    assert main_map.layers() == []
    assert osm.opacity() == 1.0

    # Add another style to the lines layer
    lines.styleManager().addStyleFromLayer("other")
    assert lines.styleManager().styles() == ["défaut", "other"]

    restore = apply_map_parameters(
        project,
        layout,
        {
            0: MapLayersParameters(
                # From the bottom to the top
                layers=["OpenStreetMap", "lines"],
                styles=["default", "other"],
                opacities=["204", "255"],
            ),
        },
    )

    # From the top to the bottom in the layout map
    assert main_map.keepLayerSet()
    assert main_map.layers() == [lines, osm]
    # Only existing styles are overridden
    assert list(main_map.layerStyleOverrides().keys()) == [lines.id()]
    assert main_map.keepLayerStyles()
    assert osm.opacity() == 0.8
    assert lines.opacity() == 1.0

    restore()

    assert not main_map.keepLayerSet()
    assert main_map.layers() == []
    assert main_map.layerStyleOverrides() == {}
    assert not main_map.keepLayerStyles()
    assert osm.opacity() == 1.0

    # Restoring twice does nothing
    restore()
    assert osm.opacity() == 1.0


def test_apply_map_parameters_locked_map(client: Client):
    project = client.get_project(PROJECT_ATLAS_SIMPLE)
    layout = project.layoutManager().layoutByName(LAYOUT)
    main_map = _main_map(project)
    osm = _layer(project, "OpenStreetMap")
    lines = _layer(project, "lines")

    # Lock the layers of the map
    main_map.setLayers([lines])
    main_map.setKeepLayerSet(True)

    restore = apply_map_parameters(
        project,
        layout,
        {0: MapLayersParameters(layers=["OpenStreetMap"], opacities=["128"])},
    )
    assert main_map.layers() == [lines]
    assert osm.opacity() == 1.0
    restore()
    assert main_map.layers() == [lines]


def test_apply_map_parameters_map_theme(client: Client):
    project = client.get_project(PROJECT_ATLAS_SIMPLE)
    layout = project.layoutManager().layoutByName(LAYOUT)
    main_map = _main_map(project)
    osm = _layer(project, "OpenStreetMap")

    # The map follows a map theme
    record = QgsMapThemeCollection.MapThemeRecord()
    record.setLayerRecords([QgsMapThemeCollection.MapThemeLayerRecord(_layer(project, "lines"))])
    project.mapThemeCollection().insert("only lines", record)
    main_map.setFollowVisibilityPresetName("only lines")
    main_map.setFollowVisibilityPreset(True)

    restore = apply_map_parameters(project, layout, {0: MapLayersParameters(layers=["OpenStreetMap"])})
    assert not main_map.followVisibilityPreset()
    assert main_map.keepLayerSet()
    assert main_map.layers() == [osm]

    restore()
    assert main_map.followVisibilityPreset()
    assert main_map.followVisibilityPresetName() == "only lines"
    assert not main_map.keepLayerSet()


def test_apply_map_parameters_unknown(client: Client):
    project = client.get_project(PROJECT_ATLAS_SIMPLE)
    layout = project.layoutManager().layoutByName(LAYOUT)
    main_map = _main_map(project)
    lines = _layer(project, "lines")

    # Unknown layers are skipped
    restore = apply_map_parameters(
        project,
        layout,
        {0: MapLayersParameters(layers=["unknown", "lines"], opacities=["255", "not a number"])},
    )
    assert main_map.layers() == [lines]
    assert lines.opacity() == 1.0
    restore()

    # No known layer and no map1 in the layout: the map is not changed
    restore = apply_map_parameters(
        project,
        layout,
        {
            0: MapLayersParameters(layers=["unknown"]),
            1: MapLayersParameters(layers=["lines"]),
        },
    )
    assert not main_map.keepLayerSet()
    assert main_map.layers() == []
    restore()


def _getprint_png(client: Client, map_parameters: str) -> bytes:
    qs = (
        "?SERVICE=ATLAS&"
        "REQUEST=GetPrint&"
        f"MAP={PROJECT_ATLAS_SIMPLE}&"
        f"TEMPLATE={LAYOUT}&"
        "FORMAT=image/png&"
        "EXP_FILTER=id in (1)&"
        f"{map_parameters}"
    )
    rv = client.get(qs, PROJECT_ATLAS_SIMPLE)
    assert rv.status_code == 200
    assert rv.headers.get("Content-Type", "") == "image/png"
    return Image.open(io.BytesIO(rv.content)).convert("RGBA").tobytes()


def test_getprint_atlas_map_layers(client: Client):
    """The map layers parameters change the printed map, only for the current request.

    Only the local lines layer is printed, the OpenStreetMap tiles are not rendered the same way
    from one request to another.
    """
    lines = _getprint_png(client, "map0:LAYERS=lines")
    assert _getprint_png(client, "map0:LAYERS=lines") == lines

    # The opacity is applied: the lines are not visible anymore
    transparent_lines = _getprint_png(client, "map0:LAYERS=lines&map0:OPACITIES=0")
    assert transparent_lines != lines

    # The opacity of the layer is restored for the next request
    assert _getprint_png(client, "map0:LAYERS=lines") == lines
