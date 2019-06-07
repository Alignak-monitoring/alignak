#!make
# Specify a shell
SHELL := /bin/bash

.PHONY: help

# Create the .env file if it does not exist
ifeq (,$(wildcard .env))
   $(shell cp .env.dist .env)
endif
# Get the environment variables
include .env

ifndef ALIGNAK_IMAGE_TAG
$(error The image TAG variable (ALIGNAK_IMAGE_TAG) is missing.)
endif

# Default values for the image
PYTHON_BASE_VERSION ?= 3.6
DOCKER_REPOSITORY ?= alignak
DOCKER_ALIGNAK_DAEMON ?= alignak
DOCKER_ALIGNAK_WEBUI ?= alignak-ui
DOCKER_IMAGE_DAEMON ?= $(DOCKER_REPOSITORY)/$(DOCKER_ALIGNAK_DAEMON)
DOCKER_IMAGE_WEBUI ?= $(DOCKER_REPOSITORY)/$(DOCKER_ALIGNAK_WEBUI)

# User credentials from environment
DOCKER_USER := ${DOCKER_USER}
DOCKER_PASS := ${DOCKER_PASS}

# Alignak configuration
ALIGNAK_CONFIGURATION_FILE ?= /alignak/etc/alignak.ini

# --------------------
help: banner
	@echo -e "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)"


# --------------------
banner: ## This help message
	@echo -e "--------------------"
	@echo -e "\x1b[36mImage\x1b[m:$(DOCKER_IMAGE):$(ALIGNAK_IMAGE_TAG)" | column -c2 -t -s :
	@echo -e "--------------------"

build: banner  ## Build the image
	$(info Building Alignak $(ALIGNAK_IMAGE_TAG) tagged images.)
	@docker-compose build
	@make -s clean

remove: banner ## Remove image
	$(info Removing "$(DOCKER_IMAGE_DAEMON):$(ALIGNAK_IMAGE_TAG)" image...)
	@docker rm $(DOCKER_IMAGE_DAEMON):$(ALIGNAK_IMAGE_TAG)
	@docker rm $(DOCKER_IMAGE_WEBUI):$(ALIGNAK_IMAGE_TAG)

clean: banner  ## Clean all
	@docker system prune --volumes --force

start: banner  ## Start the services
	$(info Starting Alignak...)
	@docker-compose up -d

stop: banner   ## Stop the services
	$(info Stopping Alignak...)
	@docker-compose down

restart:       ## Stop and start
	$(info Restarting Alignak...)
	@make -s stop
	@make -s start

check: banner  ## Check the Alignak configuration
	$(info Check the configuration)
	docker-compose run arbiter-master alignak-arbiter -V -e $(ALIGNAK_CONFIGURATION_FILE)

push: banner login   ## Push the image to the repository
	$(info Pushing "$(DOCKER_IMAGE)":"$(ALIGNAK_IMAGE_TAG)" tagged image.)
	@docker push $(DOCKER_IMAGE):$(ALIGNAK_IMAGE_TAG)

pull: banner   ## Pull the image
	$(info Pulling "$(ALIGNAK_IMAGE_TAG)" tagged image.)
	@docker pull $(DOCKER_IMAGE):$(ALIGNAK_IMAGE_TAG)

login: banner  ## Login to the repository
	$(info Login to Docker Hub, user $(DOCKER_USER).)
	@docker login -u $(DOCKER_USER) -p $(DOCKER_PASS)
