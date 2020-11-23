FROM golang:1 AS telegraf_builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN set -x && \
    apt-get update && \
    apt-get install --no-install-recommends -y \
      git \
      ca-certificates \
      make \
      gcc \
      libc-dev \
      && \
    # Build telegraf
    git clone https://github.com/influxdata/telegraf.git /src/telegraf && \
    pushd /src/telegraf && \
    BRANCH_TELEGRAF=$(git tag --sort="-creatordate" | head -1) && \
    git checkout tags/"${BRANCH_TELEGRAF}" && \
    make

FROM debian:stable-slim AS final

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DUMP1090_PORT=30003 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING=False \
    TZ=UTC

COPY --from=telegraf_builder /src/telegraf/telegraf /usr/local/bin/telegraf
COPY rootfs/ /

RUN set -x && \
		apt-get update && \
	  apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      file \
      git \
      gnupg \
      python3 \
      python3-pip \
      && \
	  pip3 install --no-cache-dir \
      python-dateutil \
      requests \
      && \
    mkdir -p /etc/telegraf && \
    # Deploy s6-overlay
    curl -s https://raw.githubusercontent.com/mikenye/deploy-s6-overlay/master/deploy-s6-overlay.sh | sh && \
    # Clean up
    apt-get remove -y \
      curl \
      file \
      git \
      gnupg \
      python3-pip \
      && \
    apt-get autoremove -y && \
    apt-get clean -y && \
	  rm -rf /src /tmp/* /var/lib/apt/lists/* && \
    # Document versions
		telegraf --version >> /VERSIONS && \
		/piaware2influx.py --version >> /VERSIONS && \
		cat /VERSIONS

ENTRYPOINT [ "/init" ]
