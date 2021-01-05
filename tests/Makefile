SHELL:=bash
#
# wmts plugin makefile
#

COMMITID=$(shell git rev-parse --short HEAD)

ifdef REGISTRY_URL
	REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

# Qgis version flavor
FLAVOR:=3.16

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

SRCDIR=$(shell realpath ..)

test:
	mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	docker run --rm --name qgis-atlasprint-test-$(FLAVOR)-$(COMMITID) -w /src/tests \
		-u $(BECOME_USER) \
		-v $(SRCDIR):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./run-tests.sh

