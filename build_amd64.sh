#!/bin/sh

VERSION=gitcommit_9825ca7
IMAGE=mikenye/piaware-to-influx

docker build -f Dockerfile -t ${IMAGE}:${VERSION}
