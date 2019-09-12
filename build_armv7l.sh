#!/bin/sh

VERSION="2019-09-12"
IMAGE=mikenye/piaware-to-influx

docker build -f Dockerfile -t ${IMAGE}:${VERSION}-arm32v7 .
