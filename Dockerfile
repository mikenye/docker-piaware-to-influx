FROM telegraf:latest

RUN apt-get update && \
	apt-get install -y --no-install-recommends python3 python3-pip && \
	pip3 install requests && \
	rm -rf /var/lib/apt/lists/*

ADD ./init /init
ADD ./piaware2influx.py /piaware2influx.py

ENTRYPOINT [ "/init" ]

