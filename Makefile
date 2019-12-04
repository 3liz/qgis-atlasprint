PLUGINNAME = atlasprint


.PHONY: tests

tests:
	$(MAKE) -C tests

release_zip:
	@echo
	@echo -------------------------------
	@echo Exporting plugin to zip package
	@echo -------------------------------
	@rm -f $(PLUGINNAME).zip
	@git archive -o $(PLUGINNAME).zip HEAD
	@echo "Created package: $(PLUGINNAME).zip"

release_upload:
	@echo
	@echo -----------------------------------------
	@echo Uploading the plugin on plugins.qgis.org.
	@echo -----------------------------------------
	@/home/etienne/dev/python/qgis_plugin_tools/infrastructure/plugin_upload.py $(PLUGINNAME).zip
