#!/bin/sh

VERSION=development
IMAGE=mikenye/piaware-to-influx

docker build -f Dockerfile -t ${IMAGE}:${VERSION}-arm64v8 .
