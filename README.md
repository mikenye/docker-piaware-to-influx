# docker-piaware-to-influx
Pull ADS-B data from dump1090, convert to InfluxDB line protocol, send to InfluxDB

For more information on what PiAware is, see here: https://flightaware.com/adsb/piaware/

## Multi Architecture Support
Currently, this image should pull and run on the following architectures:
 * ```amd64```: Linux x86-64
 * ```arm32v7```, ```armv7l```: ARMv7 32-bit (Odroid HC1/HC2/XU4, RPi 2/3)
 
## Up-and-Running

```
docker run \
 -d \
 --name piaware2influxdb \
 --restart=always \
 -e INFLUXDB_URL="http://<influxdb_host>:<influxdb_port>" \
 -e DUMP1090_HOST="<dump1090_host>" \
 -e TZ="<your_timezone>" \
 mikenye/piaware-to-influx
```

For example:

```
docker run \
  -d \
  --name=piaware2influx \
  --restart=always \
  -e INFLUXDB_URL="http://192.168.3.84:8086" \
  -e DUMP1090_HOST="192.168.3.85" \
  -e TZ="Australia/Perth" \
  mikenye/piaware-to-influx
```

The container will attempt to connect to the dump1090 instance on port 30003 to receive ADS-B data.

It will then convert the data to line protocol, and send to InfluxDB, using database "piaware" (which will be created if it doesn't exist).

## Runtime Configuration Options

There are a series of available variables you are required to set:

* `INFLUXDB_URL` - The URL of your InfluxDB instance, eg: ```http://192.168.1.10:8086```
* `DUMP1090_HOST` - The IP/hostname of your dump1090 instance, eg: ```192.168.1.11```. No port required, it will use 30003 by default.
* `TZ` - Your local timezone (optional)

## Ports

Although this container exposes ports (inherited from the telegraf container), none need to be mapped.

It will need to be able to access:
* Port `30003` TCP on the dump1090 host
* The InfluxDB server (however you specify in the `INFLUXDB_URL` environment variable)

## Visualising

Data can be visualised however you like. Personally, I use Grafana.

As an example, adding a table with the following query:

```SELECT last("current_altitude") AS "Altitude", last("current_latitude") AS "Lat", last("current_longitude") AS "Long", last("current_groundspeed") AS "Speed", last("current_track") AS "Heading", last("current_verticalrate") AS "VerticalRate" FROM "piaware" WHERE $timeFilter GROUP BY time(5m), "callsign", "squawk", "hexident" fill(none)```

Will give a result such as this:

![example Grafana table showing PiAware data](https://github.com/mikenye/docker-piaware-to-influx/raw/master/example_table_most_recent_squawks.png "Example Grafana table showing PiAware data")


