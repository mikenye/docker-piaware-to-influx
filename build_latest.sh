#
# Docker architectures
# https://github.com/docker-library/official-images/blob/a7ad3081aa5f51584653073424217e461b72670a/bashbrew/go/vendor/src/github.com/docker-library/go-dockerlibrary/architecture/oci-platform.go#L14-L25
#

VERSION="2019-09-12"
IMAGE=mikenye/piaware-to-influx

# Pull all current versions
docker pull ${IMAGE}:${VERSION}-amd64
docker pull ${IMAGE}:${VERSION}-arm32v7
docker pull ${IMAGE}:${VERSION}-arm64v8

# Push them so they are top of the list
docker push ${IMAGE}:${VERSION}-amd64
docker push ${IMAGE}:${VERSION}-arm32v7
docker push ${IMAGE}:${VERSION}-arm64v8

# Create and push multi archtecture release for current version
docker manifest create --amend ${IMAGE}:${VERSION} ${IMAGE}:${VERSION}-amd64 ${IMAGE}:${VERSION}-arm32v7 ${IMAGE}:${VERSION}-arm64v8
docker manifest annotate ${IMAGE}:${VERSION} ${IMAGE}:${VERSION}-amd64 --os linux --arch amd64
docker manifest annotate ${IMAGE}:${VERSION} ${IMAGE}:${VERSION}-arm32v7 --os linux --arch arm --variant v7
docker manifest annotate ${IMAGE}:${VERSION} ${IMAGE}:${VERSION}-arm64v8 --os linux --arch arm64 --variant v8
docker manifest push --purge ${IMAGE}:${VERSION}

# Tag current version individual architecture releases as latest individual arch releases
docker tag ${IMAGE}:${VERSION}-amd64 ${IMAGE}:latest-amd64
docker tag ${IMAGE}:${VERSION}-arm32v7 ${IMAGE}:latest-arm32v7
docker tag ${IMAGE}:${VERSION}-arm64v8 ${IMAGE}:latest-arm64v8

# Push latest individual arch releases
docker push ${IMAGE}:latest-amd64
docker push ${IMAGE}:latest-arm32v7
docker push ${IMAGE}:latest-arm64v8

# Create and push multi architecture latest
docker manifest create --amend ${IMAGE}:latest ${IMAGE}:latest-amd64 ${IMAGE}:latest-arm32v7 ${IMAGE}:latest-arm64v8
docker manifest annotate ${IMAGE}:latest ${IMAGE}:latest-amd64 --os linux --arch amd64
docker manifest annotate ${IMAGE}:latest ${IMAGE}:latest-arm32v7 --os linux --arch arm --variant v7
docker manifest annotate ${IMAGE}:latest ${IMAGE}:latest-arm64v8 --os linux --arch arm64 --variant v8
docker manifest push --purge ${IMAGE}:latest

