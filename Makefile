ARTIFACTS_DIR := objs
ENV_DIR := $(ARTIFACTS_DIR)/.env
DIST_DIR := $(ARTIFACTS_DIR)/dist
VERSION := $(shell grep -Po '(?<=^version = ")[^"]*' pyproject.toml)
DIST_WHL := $(DIST_DIR)/coppercomm-$(VERSION)-py3-none-any.whl

.PHONY: all test build clean requirements

all: test build

test: requirements
	hatch run test

build: requirements $(DIST_WHL)

$(DIST_WHL):
	rm -rf $(DIST_DIR)
	hatch build

requirements: $(ENV_DIR)

$(ENV_DIR):
	pip install hatch pytest
	hatch env create

clean:
	rm -rf $(ARTIFACTS_DIR)