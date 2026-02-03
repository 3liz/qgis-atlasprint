SHELL:=bash

PYTHON_PKG=atlasprint

-include .localconfig.mk

#
# Configure
#

# Check if uv is available
$(eval UV_PATH=$(shell which uv))
ifdef UV_PATH
ifdef VIRTUAL_ENV
# Always prefer active environment
ACTIVE_VENV=--active
endif
RUN=uv run $(ACTIVE_VENV)
endif


REQUIREMENT_GROUPS= \
	dev \
	tests \
	lint \
	packaging \
	$(NULL)

.PHONY: update-requirements

REQUIREMENTS=$(patsubst %, requirements/%.txt, $(REQUIREMENT_GROUPS))

update-requirements: $(REQUIREMENTS)

# Require uv (https://docs.astral.sh/uv/) for extracting
# infos from project's dependency-groups
requirements/%.txt: uv.lock
	@echo "Updating requirements for '$*'";\
	uv export --format requirements.txt \
		--no-annotate \
		--no-editable \
		--no-hashes \
		--only-group $* \
		-q -o requirements/$*.txt

#
# Static analysis
#

LINT_TARGETS=$(PYTHON_PKG) $(EXTRA_LINT_TARGETS)

lint::
	@ $(RUN) ruff check --preview --output-format=concise $(LINT_TARGETS)

lint::
	@ $(RUN) ruff check --preview \
		--output-format=concise \
		--target-version=py310 \
		tests

lint-fix::
	@ $(RUN) ruff check --preview --fix $(LINT_TARGETS)

lint-fix::
	@ $(RUN) ruff check --preview --fix --target-version=py310 tests

format::
	@ $(RUN) ruff format $(LINT_TARGETS)

format::
	@ $(RUN) ruff format --target-version=py310 tests

typecheck::
	@ $(RUN) mypy $(LINT_TARGETS)

typecheck::
	@ $(RUN) mypy --python-version=3.10 tests

scan:
	@ $(RUN) bandit -r $(PYTHON_PKG) $(SCAN_OPTS)

#
# Tests
#

test:
	@rm  -rf tests/__output__
	$(RUN) pytest -v tests/

##
## Test using docker image
##
QGIS_VERSION ?= 3.40
QGIS_IMAGE_REPOSITORY ?= 3liz/qgis-platform
QGIS_IMAGE_TAG ?= $(QGIS_IMAGE_REPOSITORY):$(QGIS_VERSION)
docker-test:
	docker run --quiet --rm --name qgis-$(PYTHON_PKG)-tests \
		--network host \
		--user $$(id -u):$$(id -g) \
		--mount type=bind,source=$$(pwd),target=/src \
		--workdir /src \
		--env QGIS_VERSION=$(QGIS_VERSION) \
		$(QGIS_IMAGE_TAG) .docker/run-tests.sh

