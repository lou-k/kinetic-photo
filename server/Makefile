SHELL=/bin/bash
GIT_HASH := $(shell git rev-parse --short HEAD)
GIT_COUNT := $(shell git rev-list --count main)
VERSION ?= dev-$(shell printf "%05d" $(GIT_COUNT))-$(GIT_HASH)
IMG=kinetic-photo-server:$(VERSION)

.PHONY: .check-version
.check-version:
	@echo "Version is $(VERSION)"
	@if [ "$(findstring dev-, $(VERSION))" ] ; then\
		git diff-index --quiet HEAD || ( >&2 echo "❗️❗️ There are unsaved commits -- please commit your changes before building"; exit 1);\
	fi

build: .check-version Dockerfile Pipfile setup.cfg pyproject.toml src
	docker build -t $(IMG) .

setup.cfg: setup.cfg.template Pipfile Pipfile.lock
	cp setup.cfg.template setup.cfg
	pipenv requirements  | awk -F\; '{print $$1}' | grep = | sed 's/==/>=/g' | sed 's/^/\t/' >> setup.cfg
