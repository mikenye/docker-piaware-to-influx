FROM telegraf:latest

RUN apt-get update
RUN apt-get install -y --no-install-recommends python3 python3-pip
RUN pip3 install requests

ADD ./init /init
ADD ./piaware2influx.py /piaware2influx.py

CMD [ "/init" ]

