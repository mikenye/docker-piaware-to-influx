FROM telegraf:latest

ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING=False \
    TZ=UTC

COPY rootfs/ /

RUN set -x && \
		apt-get update && \
	  apt-get install -y --no-install-recommends \
      ca-certificates \
      gnupg \
      python3-pip \
      python3 \
      && \
	  pip3 install \
      requests \
      && \
    curl -s https://raw.githubusercontent.com/mikenye/deploy-s6-overlay/master/deploy-s6-overlay.sh | sh && \
    apt-get remove -y \
      gnupg \
      && \
    apt-get autoremove -y && \
	  rm -rf /tmp/* /var/lib/apt/lists/* && \
		telegraf --version >> /VERSIONS && \
		/piaware2influx.py --version >> /VERSIONS && \
		cat /VERSIONS

ENTRYPOINT [ "/init" ]
