FROM debian:stable-slim as builder

COPY rootfs/piaware2influx.py /src/piaware2influx/rootfs/piaware2influx.py

RUN set -x && \
    echo "========== Prerequisites compiling piaware2influx.py ==========" && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
      python3-pip \
      python3-setuptools \
      gcc \
      libpython3-dev \
      && \
    pip3 install \
      wheel \
      nuitka \
      requests \
      && \
    echo "========== Compile piaware2influx.py with nuitka ==========" && \
    cd /src/piaware2influx/rootfs && \
    python3 -m nuitka --standalone --show-progress --show-scons ./piaware2influx.py

FROM debian:stable-slim as final

ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING=False \
    TZ=UTC

COPY rootfs/ /
COPY --from=builder /src/piaware2influx/rootfs/piaware2influx.dist/* /opt/piaware2influx/

RUN set -x && \
    echo "========== Prerequisites ==========" && \
		apt-get update && \
	  apt-get install -y --no-install-recommends \
      apt-transport-https \
      ca-certificates \
      gnupg \
      libc6 \
      wget \
      && \
    echo "========== Install Telegraf ==========" && \
    wget -qO- https://repos.influxdata.com/influxdb.key | apt-key add - && \
    VERSION_CODENAME=$(cat /etc/os-release | grep "VERSION_CODENAME" | cut -d "=" -f 2) && \
    echo "deb https://repos.influxdata.com/debian ${VERSION_CODENAME} stable" | tee /etc/apt/sources.list.d/influxdb.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      telegraf \
      && \
    echo "========== Install s6-overlay ==========" && \
    wget -q -O - https://raw.githubusercontent.com/mikenye/deploy-s6-overlay/master/deploy-s6-overlay.sh | sh && \
    echo "========== Clean-up ==========" && \
    apt-get remove -y \
      apt-transport-https \
      gnupg \
      wget \
      && \
    apt-get autoremove -y && \
	  rm -rf /tmp/* /var/lib/apt/lists/* && \
    echo "========== Versions: ==========" && \
		telegraf --version >> /VERSIONS && \
		/opt/piaware2influx/piaware2influx --version >> /VERSIONS && \
		cat /VERSIONS

ENTRYPOINT [ "/init" ]
