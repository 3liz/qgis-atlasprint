atlasprint: QGIS2 Server Plugin to export PDF from composer with atlas capabilities
==========================================================================================

Description
-----------

This plugin adds a new request to QGIS Server `getprintatlas` which allows to export a print composer with an atlas configured, but passing an expression parameter to choose which feature is the current atlas feature.

This version 1.1.1 is for Qgis 2 only. If you are using Qgis 3, consider to use 
version 1.2.0 or higher.

Installation
------------

To install the plugin, go to the [download section](https://github.com/3liz/qgis-atlasprint/releases)
of the plugin web site, retrieve the archive of 1.1.x, and extract the content 
of the archive with `unzip` or an other tool.

Then move the directory of the plugin into the plugins directory of Qgis Server
(it is `/opt/qgis/plugins` most often). You need to restart Qgis Server.

For more details, read [the documention of Qgis Server](https://docs.qgis.org/2.18/en/docs/user_manual/working_with_ogc/server/plugins.html#installation).

