#!/bin/sh

VERSION="2019-09-12"
IMAGE=mikenye/piaware-to-influx

docker build -f Dockerfile.aarch64 -t ${IMAGE}:${VERSION}-arm64v8 .
