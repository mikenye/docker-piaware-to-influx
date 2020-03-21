# mikenye/piaware-to-influx

Pull ADS-B data from `dump1090`, `readsb` or another host that can provide BaseStation data, convert to InfluxDB line protocol and send to InfluxDB (v1.x)

For more information on PiAware, see here: [FlightAware-PiAware](https://flightaware.com/adsb/piaware/)

This image works well with:

* [mikenye/piaware](https://hub.docker.com/r/mikenye/piaware)
* [mikenye/readsb](https://hub.docker.com/r/mikenye/readsb)

Credit to [Bones-Aviation-Page](http://woodair.net) for their [Socket-Data-and-BST-files](http://woodair.net/sbs/article/barebones42_socket_data.htm) page. The information on that page made it easy for me to write the code for this container.

## Multi Architecture Support

Currently, this image should pull and run on the following architectures:

* `amd64`: Linux x86-64
* `arm32v7`, `armv7l`: ARMv7 32-bit (Odroid HC1/HC2/XU4, RPi 2/3/4)
* `aarch64`, `arm64v8`: ARMv8 64-bit (RPi 4)

## Supported tags and respective Dockerfiles

* `latest` should always contain the latest released versions of `telegraf` and `piaware2influx.py`. This image is built nightly from the [`master` branch](https://github.com/mikenye/docker-piaware-to-influx/tree/master) [`Dockerfile`](https://github.com/mikenye/docker-piaware-to-influx/blob/master/Dockerfile) for all supported architectures.
* `development` ([`master` branch](https://github.com/mikenye/docker-piaware-to-influx/tree/master), [`Dockerfile`](https://github.com/mikenye/docker-piaware-to-influx/blob/master/Dockerfile), `amd64` architecture only, built on commit, not recommended for production)
* Specific version and architecture tags are available if required, however these are not regularly updated. It is generally recommended to run `latest`.

## Change Log

### 2020-03-22

* Much needed code tidy up & linting
* Fix issue with vessel being added to state database and then rapidly expiring due to timezone mismatch
* Fix issue with log buffering

### 2019-09-12

* Implement s6-overlay
* Logging improvements
* Fixes for [issue #1](https://github.com/mikenye/docker-piaware-to-influx/issues/1)
* Add support for `arm64v8` / `aarch64` architecture

### 2018-07-06

* Original release supporting `amd64` and `arm32v7` architectures

## Up-and-Running with `docker run`

Firstly, make sure all your hosts (`influxdb`, `piaware`/`dump1090`/`readsb` and the docker host that will run this container) have their clocks set correctly and are synchronised with NTP.

Next, you can start the container:

```shell
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

```shell
docker run \
  -d \
  --name=piaware2influx \
  --restart=always \
  -e INFLUXDB_URL="http://192.168.3.84:8086" \
  -e DUMP1090_HOST="192.168.3.85" \
  -e TZ="Australia/Perth" \
  mikenye/piaware-to-influx
```

The container will attempt to connect to the `dump1090` instance on port `30003` to receive ADS-B data.

It will then convert the data to line protocol, and send to InfluxDB, using database `piaware` (which will be created if it doesn't exist).

## Up-and-Running with Docker Compose

Firstly, make sure all your hosts (`influxdb`, `piaware`/`dump1090`/`readsb` and the docker host that will run this container) have their clocks set correctly and are synchronised with NTP.

An example `docker-compose.xml` file is below:

```shell
version: '2.0'

services:
  piaware2influx:
    image: mikenye/piaware-to-influx:latest
    tty: true
    container_name: piaware2influx
    restart: always
    environment:
      - TZ="Australia/Perth"
      - INFLUXDB_URL=http://192.168.3.84:8086
      - DUMP1090_HOST=192.168.3.85
      - VERBOSE_LOGGING=False
```

The container will attempt to connect to the `dump1090` instance on port `30003` to receive ADS-B data.

It will then convert the data to line protocol, and send to InfluxDB, using database `piaware` (which will be created if it doesn't exist).

## Up-and-Running with Docker Compose, including `mikenye/piaware`

```shell
version: '2.0'

services:

  piaware:
    image: mikenye/piaware:latest
    tty: true
    container_name: piaware
    mac_address: de:ad:be:ef:13:37
    restart: always
    devices:
      - /dev/bus/usb/001/004:/dev/bus/usb/001/004
    ports:
      - 8080:8080
      - 30005:30005
    environment:
      - TZ="Australia/Perth"
      - LAT=-33.33333
      - LONG=111.111111

    piaware2influx:
      image: mikenye/piaware-to-influx:latest
      tty: true
      container_name: piaware2influx
      restart: always
      environment:
        - TZ="Australia/Perth"
        - INFLUXDB_URL=http://192.168.3.84:8086
        - DUMP1090_HOST=piaware
        - VERBOSE_LOGGING=False
```

For an explanation of the `mikenye/piaware` image's configuration, see that image's readme.

## Runtime Configuration Options

There are a series of available variables you are required to set:

* `INFLUXDB_URL` - The URL of your InfluxDB instance, eg: `http://192.168.1.10:8086`
* `DUMP1090_HOST` - The IP/hostname of your dump1090 instance, eg: `192.168.1.11`. No port required, it will use 30003 by default.
* `TZ` - Your local timezone, eg `Australia/Perth`
* `VERBOSE_LOGGING` - Whether or not to verbosely log. This can get very noisy, so is `False` by default. Set to `True` if you need more verbosity.

## Ports

Although this container exposes ports (inherited from the telegraf container), none need to be mapped.

It will need to be able to access:

* Port `30003` TCP on the dump1090 host
* The InfluxDB server (however you specify in the `INFLUXDB_URL` environment variable)

## State Tracking

As not all messages received contain sufficient data to send to InfluxDB. This program keeps a small state database in memory so it is able to construct a message to send to InfluxDB if insufficient data is received.  Also, every message contains the vessel's "ident" information, but not all messages contain the callsign. Once a callsign is received, it is kept in the state tracking database.

To keep the state tracking memory footprint small, and to ensure information is up-to-date, if no messages have been received from a vessel for a period of 15 minutes or more, the vessel is ejected from the state tracking database. For this reason, it is important to have your hosts' clocks synchronised with NTP, and to specify your timezone as shown above.

## Telegraf

Telegraf (https://www.influxdata.com/time-series-platform/telegraf/) runs in this container as well. It handles taking the data generated by `piaware2influx.py` and writing it to InfluxDB. Telegraf is used because the clever folks at InfluxData are better at writing software that talks to InfluxDB than I am. It handles buffering, it handles InfluxDB temporarily being unavailable, and lots of other nifty features.

It also means that if you'd like a "piaware2kafka" for example, you could simply fork this project and update the telegraf.conf (which is generated via `etc/cont-init.d/01-piaware2influx` on container start), as telegraf supports several different output plugins. This container just uses `outputs.influxdb`.

## InfluxDB retention policies

By default, when Telegraf creates a database, it uses the default retention policy. At the time of writing, with InfluxDB version 1.7, this means the data is kept for *7 days* (168 hours).

```
InfluxDB shell version: 1.7.10
> use piaware
Using database piaware
> show retention policies
name    duration shardGroupDuration replicaN default
----    -------- ------------------ -------- -------
autogen 0s       168h0m0s           1        true
```

If you need a longer retention than this, you will need to modify the retention policy yourself. For example, if you wanted to keep the last 30 days of data:

```
InfluxDB shell version: 1.7.10
> CREATE RETENTION POLICY "30_days" ON "piaware" DURATION 30d REPLICATION 1 DEFAULT
> use piaware
Using database piaware
> show retention policies
name    duration shardGroupDuration replicaN default
----    -------- ------------------ -------- -------
autogen 0s       168h0m0s           1        false
30_days 720h0m0s 24h0m0s            1        true
```

## Logging

The container logs quite a lot of information.

* It will log each message received
* It has an automatic "back-off" feature, where it will only log a message for a vessel once per minute
* If you have `VERBOSE_LOGGING` set to `True`, the "back-off" feature is disabled

Regardless of the back-off feature, it still logs quite a bit of information, so it is strongly advised to set up container log rotation, if you haven't already (see: [how-to-setup-log-rotation-post-installation](https://success.docker.com/article/how-to-setup-log-rotation-post-installation)).

Log entries look something like this:
```
2019-09-12 19:26:50 [RX: 1629, TX: 930, V: 5] [Ident: 7C146A] Now receiving from this vessel
2019-09-12 19:26:50 [RX: 1632, TX: 930, V: 5] [Ident: 8A017C Callsign: AWQ536] Alt: 100
2019-09-12 19:26:50 [RX: 1635, TX: 931, V: 5] [Ident: 8A017C Callsign: AWQ536] Alt: 100
2019-09-12 19:26:50 [RX: 1636, TX: 932, V: 5] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 137, Track: 194, VerticalRate: -768
2019-09-12 19:26:50 [RX: 1638, TX: 933, V: 5] [Ident: 8A017C Callsign: AWQ536] Alt: 100, Lat: -31.91347, Long: 115.97291
2019-09-12 19:26:50 [RX: 1639, TX: 934, V: 5] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 138, Track: 194, VerticalRate: -768
2019-09-12 19:26:50 [RX: 1644, TX: 935, V: 5] [Ident: 8A017C Callsign: AWQ536] Alt: 50
2019-09-12 19:26:50 [RX: 1644, TX: 936, V: 4] [Ident: C82762]: Expiring inactive vessel from state database
2019-09-12 19:26:50 [RX: 1645, TX: 936, V: 4] [Ident: 8A017C Callsign: AWQ536] Alt: 25
2019-09-12 19:26:50 [RX: 1646, TX: 937, V: 4] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 138, Track: 194, VerticalRate: -640
2019-09-12 19:26:50 [RX: 1648, TX: 938, V: 4] [Ident: 8A017C Callsign: AWQ536] Alt: 25, Lat: -31.91666, Long: 115.97201
2019-09-12 19:26:50 [RX: 1650, TX: 939, V: 4] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 138, Track: 194, VerticalRate: -640
2019-09-12 19:26:50 [RX: 1655, TX: 940, V: 4] [Ident: 8A017C Callsign: AWQ536] Alt: 0, Lat: -31.91850, Long: 115.97146
2019-09-12 19:26:50 [RX: 1657, TX: 941, V: 4] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 138, Track: 194, VerticalRate: -704
2019-09-12 19:26:50 [RX: 1662, TX: 942, V: 4] [Ident: 8A017C Callsign: AWQ536] GroundSpeed: 138, Track: 194, VerticalRate: -704
2019-09-12 19:26:50 [RX: 1664, TX: 943, V: 4] [Ident: 8A017C Callsign: AWQ536] Alt: -100, Lat: -31.92352, Long: 115.97000
2019-09-12 19:26:50 [RX: 1671, TX: 944, V: 5] [Ident: 7C1ABB] Now receiving from this vessel
2019-09-12 19:26:50 [RX: 1671, TX: 944, V: 4] [Ident: 7C8022]: Expiring inactive vessel from state database
2019-09-12 19:26:50 [RX: 1673, TX: 944, V: 4] [Ident: 7C146A] GroundSpeed: 134, Track: 239, VerticalRate: -768
2019-09-12 19:26:50 [RX: 1677, TX: 947, V: 4] [Ident: 7C146A Callsign: QFA777] GroundSpeed: 134, Track: 240, VerticalRate: -768
2019-09-12 19:26:50 [RX: 1686, TX: 948, V: 4] [Ident: 7C146A Callsign: QFA777] Alt: 725, Lat: -31.90593, Long: 116.02734
2019-09-12 19:26:50 [RX: 1687, TX: 949, V: 4] [Ident: 7C146A Callsign: QFA777] Alt: 700, Lat: -31.90622, Long: 116.02667
2019-09-12 19:26:50 [RX: 1690, TX: 950, V: 4] [Ident: 7C146A Callsign: QFA777] Alt: 675, Lat: -31.90658, Long: 116.02605
2019-09-12 19:26:50 [RX: 1696, TX: 951, V: 4] [Ident: 7C146A Callsign: QFA777] GroundSpeed: 134, Track: 240, VerticalRate: -704
2019-09-12 19:26:50 [RX: 1698, TX: 952, V: 4] [Ident: 7C146A Callsign: QFA777] GroundSpeed: 135, Track: 239, VerticalRate: -704
2019-09-12 19:26:50 [RX: 1699, TX: 953, V: 4] [Ident: 7C146A Callsign: QFA777] GroundSpeed: 135, Track: 239, VerticalRate: -704
2019-09-12 19:26:50 [RX: 1700, TX: 954, V: 4] [Ident: 7C146A Callsign: QFA777] GroundSpeed: 135, Track: 239, VerticalRate: -640
```

As you can see from the output above, logging is broken up into several columns:

```
Date Time [RX: <adsb_messages_received>, TX: <points_transmitted_to_influxdb>, V: <number_vessels_in_state_db>] [Vessel Info] Information
```

* `RX:` is the number of BaseStation messages received from `dump1090`/`readsb`/etc
* `TX:` is the number of messages sent to InfluxDB. Note, this figure will always be smaller than `RX:`, as not all messages received contain sufficient data to send to InfluxDB (see State Tracking above). Also some messages don't contain usable (for us) data.
* `V:` is the number of vessels in the program's internal state database.
* `Vessel Info` contains known information about the vessel. Every message contains the vessel's "ident" information, but a callsign will not be displayed until a message is received containing the vessel's call sign (see State Tracking above).
* `Information`: This contains information about the vessel - either data received from the vessel or information from this program regarding the vessel.

Telegraf also logs to the container logs, although it is set to "quiet" so you won't see much unless there's a problem. You will likely notice it when the container starts:

```
2019-09-12 19:08:46.427865500  2019-09-12T11:08:46Z I! Starting Telegraf 1.12.1
```

## Visualising the data

Data can be visualised however you like. Personally, I use Grafana.

As an example, adding a table with the following query:

```shell
SELECT last("current_altitude") AS "Altitude", last("current_latitude") AS "Lat", last("current_longitude") AS "Long", last("current_groundspeed") AS "Speed", last("current_track") AS "Heading", last("current_verticalrate") AS "VerticalRate" FROM "piaware" WHERE $timeFilter GROUP BY time(5m), "callsign", "squawk", "hexident" fill(none)
```

Will give a result such as this:

![example Grafana table showing PiAware data](https://github.com/mikenye/docker-piaware-to-influx/raw/master/example_table_most_recent_squawks.png "Example Grafana table showing PiAware data")

## Getting help

Please feel free to [open an issue on the project's GitHub](https://github.com/mikenye/docker-piaware-to-influx/issues).
