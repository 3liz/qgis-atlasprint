atlasprint: QGIS3 Server Plugin to export PDF from composer with atlas capabilities
==========================================================================================

Description
-----------

This plugin adds a new request to QGIS 3 Server `getprintatlas` which allows to export a print composer with an atlas configured, but passing an expression parameter to choose which feature is the current atlas feature.

Installation
------------

We assume you have a fully functionnal QGIS Server. See [the QGIS3 documentation](https://docs.qgis.org/3.4/en/docs/user_manual/working_with_ogc/server/index.html).

We need to download the plugin, and tell QGIS Server where the plugins are stored, then reload the web server.
For example on Debian:

```
# Create needed directory to store plugins
mkdir -p /srv/qgis/plugins

# Get last version
cd /srv/qgis/plugins
wget "https://github.com/3liz/qgis-atlasprint/archive/master.zip"
unzip master.zip
mv qgis-atlasprint-master atlasprint

# Make sure correct environment variables are set in your web server configuration
# for example in Apache2 with mod_fcgid
nano /etc/apache2/mods-available/fcgid.conf
FcgidInitialEnv QGIS_PLUGINPATH "/srv/qgis/plugins/"

# Reload server, for example with Apache2
service apache2 reload
```

You can now test your installation
