FROM telegraf:latest

ENV VERSION_S6OVERLAY=v1.22.1.0 \
    ARCH_S6OVERLAY=amd64 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2

ADD https://github.com/just-containers/s6-overlay/releases/download/${VERSION_S6OVERLAY}/s6-overlay-${ARCH_S6OVERLAY}.tar.gz /tmp/s6-overlay.tar.gz

RUN apt-get update && \
	apt-get install -y --no-install-recommends python3 python3-pip && \
	pip3 install requests && \
        tar -xzf /tmp/s6-overlay.tar.gz -C / && \
	rm -rf /var/lib/apt/lists/* && \
        rm /tmp/s6-overlay.tar.gz

ADD ./piaware2influx.py /piaware2influx.py
COPY etc/ /etc/

ENTRYPOINT [ "/init" ]

