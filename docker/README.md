# Docker Alignak

## Host / containers shared volume

The *data/alignak* directory is shared between the host system and the running containers. It contains : 
- a default test configuration to show how to configure and use some Alignak features
- some commands used to check hosts and services in the default configuration

The default configuration shows how to build an Alignak configuration split in 3 realms. Each realm owns its hosts and they are all monitored in the same Alignak ystem with one Web UI.

Have a look into the configuration for more information -)


## Using the makefile

A GNU makefile exists to help for the most common operations with Alignak Docker images.

The Makefile includes the *.env* file existing in the current directory.

Note: If the *.env* file does not exist, running make will copy the default *.env.dist* file to a new *.env* file.


```bash

   # View all the available targets + doc
   make

   # Build the images
   make build
   # This will build the images according to the values defined in the .env file

   # Clean extra unused images
   make clean

   # Push an image to your repository
   # Direct
   TAG=0.0.1 DOCKER_USER=username DOCKER_PASS=password make push

   export TAG=0.0.1
   export DOCKER_USER=username
   export DOCKER_PASS=password
   make push
```

## Build and run
You can also use usual docker-compose to build the Alignak images:

```bash
    docker-compose build
```

```bash
    docker-compose up
```

## Some commands

Check the Alignak configuration:
```bash
   docker-compose run arbiter-master
   or
   make check
```

## Metrics and Graphite

 View https://github.com/graphite-project/docker-graphite-statsd

```bash
    docker run -d\
     --name graphite\
     --restart=always\
     -p 80:80\
     -p 2003-2004:2003-2004\
     -p 2023-2024:2023-2024\
     -p 8125:8125/udp\
     -p 8126:8126\
     graphiteapp/graphite-statsd
```
