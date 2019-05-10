# Specify a shell
SHELL := /bin/bash

.PHONY: help

ifndef DOCKER_TAG
$(error The image TAG variable (DOCKER_TAG) is missing.)
endif

# Default values for the image
DOCKER_TAG ?= 0.0.0
DOCKER_REPOSITORY ?= alignak
DOCKER_SERVICE ?= alignak
DOCKER_IMAGE ?= $(DOCKER_REPOSITORY)/$(DOCKER_SERVICE)

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
	@echo -e "\x1b[36mImage\x1b[m:$(DOCKER_IMAGE):$(DOCKER_TAG)" | column -c2 -t -s :
	@echo -e "--------------------"

build: banner  ## Build the image
	$(info Building "$(DOCKER_TAG)" tagged images.)
	@docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -f ./Dockerfile .
	@make -s tag
	@make -s clean

tag: banner    ## Tag an image
	$(info Tagging image with "$(DOCKER_TAG)".)
	-docker tag $(DOCKER_IMAGE):latest $(DOCKER_IMAGE):$(DOCKER_TAG)

remove: banner ## Remove image
	$(info Removing "$(DOCKER_IMAGE):$(DOCKER_TAG)" image...)
	@docker rm $(DOCKER_IMAGE):$(DOCKER_TAG)

clean: banner  ## Clean all
	@docker system prune --volumes --force

start: banner  ## Start the services
	$(info Starting "$(DOCKER_IMAGE)"...)
	@docker-compose up -d

stop: banner   ## Stop the services
	$(info Stopping "$(DOCKER_IMAGE)"...)
	@docker-compose down

restart: banner   ## Stop and start
	$(info Restarting "$(DOCKER_IMAGE)"...)
	@make -s stop
	@make -s start

check: banner  ## Check the Alignak configuration
	$(info Check the configuration)
	docker-compose run arbiter-master alignak-arbiter -V -e $(ALIGNAK_CONFIGURATION_FILE)

push: banner login   ## Push the image to the repository
	$(info Pushing "$(DOCKER_IMAGE)":"$(DOCKER_TAG)" tagged image.)
	@docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

pull: banner   ## Pull the image
	$(info Pulling "$(DOCKER_TAG)" tagged image.)
	@docker pull $(DOCKER_IMAGE):$(DOCKER_TAG)

login: banner  ## Login to the repository
	$(info Login to Docker Hub, user $(DOCKER_USER).)
	@docker login -u $(DOCKER_USER) -p $(DOCKER_PASS)
