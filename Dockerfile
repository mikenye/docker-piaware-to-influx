FROM debian:stable-slim

ENV DUMP1090_PORT=30003 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING=False \
    TZ=UTC \
    URL_GO_BOOTSTRAP="https://dl.google.com/go/go1.4-bootstrap-20171003.tar.gz" \
    URL_GO_SRC="https://dl.google.com/go/go1.14.4.src.tar.gz"

COPY rootfs/ /

RUN set -x && \
		apt-get update && \
	  apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gcc \
      git \
      gnupg \
      libc-dev \
      make \
      netbase \
      python3 \
      python3-pip \
      wget \
      && \
	  pip3 install \
      python-dateutil \
      requests \
      && \
    # Build go-bootstrap
    mkdir -p /src/go-bootstrap && \
    cd /src && \
    wget "${URL_GO_BOOTSTRAP}" && \
    tar xzf go1.4-bootstrap-20171003.tar.gz -C /src/go-bootstrap && \
    cd /src/go-bootstrap/go/src && \
    ./all.bash || true && \
    # Build go
    cd /src && \
    wget "${URL_GO_SRC}" && \
    tar xvf go1.14.4.src.tar.gz -C /usr/local && \
    cd /usr/local/go/src && \
    GOROOT_BOOTSTRAP=/src/go-bootstrap/go GOOS=linux GOARCH=$(uname -m) ./bootstrap.bash || true && \
    GOROOT_BOOTSTRAP=/src/go-bootstrap/go ./all.bash && \
    ln -s /usr/local/go/bin/go /usr/local/bin/go && \
    ln -s /usr/local/go/bin/gofmt /usr/local/bin/gofmt && \
    # Build & install telegraf
    git clone https://github.com/influxdata/telegraf.git /src/telegraf && \
    cd /src/telegraf && \
    export BRANCH_TELEGRAF=$(git tag --sort="-creatordate" | head -1) && \
    git checkout tags/${BRANCH_TELEGRAF} && \
    make && \
    make install && \
    mkdir -p /etc/telegraf && \
    # Deploy s6-overlay
    curl -s https://raw.githubusercontent.com/mikenye/deploy-s6-overlay/master/deploy-s6-overlay.sh | sh && \
    # Clean up
    apt-get remove -y \
      curl \
      gcc \
      git \
      gnupg \
      libc-dev \
      make \
      netbase \
      wget \
      && \
    apt-get autoremove -y && \
    apt-get clean -y && \
	  rm -rf /src /tmp/* /var/lib/apt/lists/* && \
    # Document versions
		telegraf --version >> /VERSIONS && \
		/piaware2influx.py --version >> /VERSIONS && \
		cat /VERSIONS

ENTRYPOINT [ "/init" ]
