#!/usr/bin/env sh
#shellcheck shell=sh

set -ex

REPO=mikenye
IMAGE=piaware-to-influx
PLATFORMS="linux/amd64,linux/arm/v7,linux/arm64"

docker context use x86_64
export DOCKER_CLI_EXPERIMENTAL="enabled"
docker buildx use homecluster

# Build the latest image using buildx
docker buildx build -t "${REPO}/${IMAGE}:latest" --compress --push --platform "${PLATFORMS}" .

# Get version of the latest image
docker pull "${REPO}/${IMAGE}:latest"
VERSION=$(docker run --rm --entrypoint /piaware2influx.py ${REPO}/${IMAGE}:latest --version | cut -d " " -f 2)

# Build version-specific tagged image
docker buildx build -t "${REPO}/${IMAGE}:${VERSION}" --compress --push --platform "${PLATFORMS}" .
