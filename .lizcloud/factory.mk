#
# Makefile for building/packaging qgis for 3Liz
#

VERSION=$(shell ./metadata_key ../metadata.txt version)

main:
	echo "Makefile for packaging infra components: select a task"

PACKAGE=qgis_atlasplugin
FILES = ../filters ../i18n ../scripts ../*.py ../*.qrc ../icon.png ../metadata.txt ../README.md
PACKAGEDIR=atlasplugin

build3/$(PACKAGEDIR):
	@rm -rf build3/$(PACKAGEDIR)
	@mkdir -p build3/$(PACKAGEDIR)


.PHONY: package
package: build3/$(PACKAGEDIR)
	@echo "Building package $(PACKAGE)"
	@cp -rLp $(FILES) build3/$(PACKAGEDIR)/
	$(FACTORY_SCRIPTS)/make-package $(PACKAGE) $(VERSION) $(PACKAGEDIR) ./build3

