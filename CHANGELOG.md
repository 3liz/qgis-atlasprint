# Changelog

## Unreleased

* Fix Python exception about PDF rasterized

## 3.4.0 - 2024-05-27

* Bump QGIS minimum version to QGIS 3.22
* Fix PDF not being rasterized

## 3.3.2 - 2022-10-19

* Fix an issue when the layout does not have a map, fix #59 (contribution from @benoitblanc)

## 3.3.1 - 2022-03-04

* Improve logs about additional parameters and current login

## 3.3.0 - 2022-03-03

* Add expression for `@lizmap_user` and `@lizmap_user_groups` related to the current logged user in Lizmap Web Client
* Add `FORMAT` option in the GET request to export as JPEG, PDF, PNG or SVG.
  Values are from the QGIS Server documentation : https://docs.qgis.org/latest/en/docs/server_manual/services.html#wms-getprint-format
* Display the version number in the logs when starting the plugin
* Set file permission to 744 in the ZIP by default
* Some code refactoring and cleaning
* Remove the `v` prefix in a git tag

## v3.2.2 - 2021-04-29

* Fix the feature expression if the primary key is numeric
* Fix the name of the plugin in the logs
* Raise the minimum version to 3.10
* Some code cleanup to follow the QGIS API

## v3.2.1 - 2021-01-06

* Sanitize filename when exporting to PDF
* Improve debug when there is an error while exporting to PDF
* Add some tests

## v3.2.0 - 2020-08-31

* Add QGIS report support, contribution from OpenGIS.ch

## v3.1.0 - 2020-04-28

* Add warning on QGIS Desktop
* Add additional params in the URL, contribution from ThomasG77
