#!/usr/bin/env python3

__version__ = "2020-05-12"

# Protocol data from this URL:
# http://woodair.net/sbs/article/barebones42_socket_data.htm

import sys
import os
import socket
import datetime
import time
import argparse
import requests
import inspect


class ADSB_Processor():
    """
    Receives ADSB information, converts to InfluxDB line protocol.

    Sends line protocol data to InfluxDB via Telegraf.

    As not all messages received contain sufficient data to send to InfluxDB,
    this class keeps a small state database in memory so it is able to
    construct a message to send to InfluxDB if insufficient data is received.

    Also, every message contains the vessel's "ident" information,
    but not all messages contain the callsign.

    Once a callsign is received, it is kept in the state tracking database.

    To keep the state tracking memory footprint small,
    and to ensure information is up-to-date,
    if no messages have been received from a vessel for a period of 15 minutes
    or more, the vessel is ejected from the state tracking database.

    For this reason, it is important to have your hosts'
    clocks synchronised with NTP, and to have the correct timezone set.
    """

    def __init__(self, telegraf_url, verbose_logging=False):
        """
        Instantiate instance of ADSB_Processor.

        Parameters:
        telegraf_url (str): URL of Telegraf's inputs.http_listener
        verbose_logging (bool): Enable verbose logging
        """
        self.buffer = str()
        self.database = {}
        self.messages_processed = 0
        self.points_sent = 0
        self.telegraf_url = telegraf_url
        self.verbose_logging = verbose_logging
        self._clear_buffer()

    def send_line_protocol(self, line_protocol):
        """
        Send line protocol data to Telegraf.

        Parameters:
        line_protocol (str): Line protocol to be sent
        """

        if self.verbose_logging:
            self.log("Sending line protocol: '%s'" % (repr(line_protocol)))

        # url = "%s?precision=s"
        try:
            telegraf_request = \
                requests.post(self.telegraf_url, data=line_protocol)
            self.points_sent += 1
        except:
            errormsg = "ERROR: could not submit line protocol! "
            errormsg += repr(line_protocol)
            self.log(errormsg)
        if telegraf_request.status_code != 204:
            errormsg = "ERROR: telegraf status code was '"
            errormsg += telegraf_request.status_code
            errormsg += "' expected '204'!"
            self.log(errormsg)

    def log(self, text):
        """
        Log handler.

        Parameters:
        text (str): Log message
        """
        logmsg = "%s [RX: %s, TX: %s, V: %s] %s" % (
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(self.messages_processed),
            str(self.points_sent),
            str(len(self.database.keys())),
            text)
        print(logmsg)
        sys.stdout.flush()

    def log_aircraft(self, hexident, text, no_backoff=False):
        """
        Log a message relating to vessel.

        Will only log an individual vessel once per minute.

        Parameters:
        hexident (str): hexident of vessel
        text (str): log message
        no_backoff (bool): if true, ignore the once per minute rule
        """

        logstuff = self.verbose_logging

        # if this vessel hasn't been logged, set up 'lastlogged' info
        if 'lastlogged' not in self.database[hexident].keys():
            logstuff = True
            self.database[hexident]['lastlogged'] = datetime.datetime.now()
            if self.verbose_logging:
                self.log("<%s> Setting lastlogged for '%s' to '%s'" % (inspect.currentframe().f_code.co_name, hexident, self.database[hexident]['lastlogged']))

        # if the vessel has been logged
        else:

            # if we need to back off (ie: log once per minute)
            if not no_backoff:
                cutoff = datetime.datetime.now()
                cutoff -= datetime.timedelta(seconds=60)
                if self.database[hexident]['lastlogged'] > cutoff:
                    logstuff = False

        # log the message if required
        if logstuff or self.verbose_logging or no_backoff:
            logtext = "[Ident: "
            logtext += hexident
            if self.database[hexident]['callsign'] != "":
                logtext += " Callsign: %s" % (
                    self.database[hexident]['callsign'])
            logtext += "] "
            logtext += text
            self.log(logtext)

    def _clear_buffer(self):
        self.buffer = str()

    def add_data_to_buffer(self, datareceived):
        """
        Add raw ADSB data received to internal buffer.

        Parameters:
        datareceived (str): raw data received
        """
        self.buffer = self.buffer + datareceived
        self.process_buffer()

    def process_buffer(self):
        """
        Process the data buffer.

        Checks to see if a full ADSB message has been received.
        If so, process it.
        """
        new_message = str()
        last_two = "  "
        count = 0

        # Read buffer up to end of message.
        # If any data is left in the buffer, leave it there
        #   so when we receive the remainder of the data we can
        #   assemble the message.
        for character_received in self.buffer:
            if character_received not in ("\r", "\n"):
                new_message += character_received

            # maintain a record of the last two chars
            # used to detect end of message '\r\n'
            last_two += character_received
            last_two = last_two[1:]

            # count number of characters read, so we can
            #   remove this many chars from the start of
            #   the buffer.
            count += 1

            # if we get to an end of message, then we process
            #   the message, and reset our counters & stuff
            if last_two == '\r\n':
                if self.verbose_logging:
                    self.log("========== START PROCESSING MESSAGE ==========")
                self.current_message_datetime = None
                self.process_message(new_message)
                self.current_message_datetime = None
                if self.verbose_logging:
                    self.log("========== FINISH PROCESSING MESSAGE ==========")
                self.buffer = self.buffer[count:]
                self.messages_processed += 1
                count = 0
                new_message = ""

    def clean_database(self, minutes_inactivity=15):
        """
        Remove stale entries from vessel database.

        If a message hasn't been received from a vessel for
        'minutes_inactivity', remove it from the state database.

        Parameters:
        minutes_older_than (int): Expire vessel after this many minutes
                                  of inactivity
        """
        hexidents_to_remove = set()
        for hexident in self.database:
            # work out what was 15 mins ago,
            # and clean out entries older than 15 minutes
            cutoff = datetime.datetime.now() - \
                datetime.timedelta(minutes=minutes_inactivity)

            if self.database[hexident]['lastseen'] < cutoff:
                if self.verbose_logging:
                    self.log("<%s> Vessel '%s' lastseen: '%s', and cutoff: '%s'" % (inspect.currentframe().f_code.co_name, hexident, self.database[hexident]['lastseen'], cutoff))
                self.log_aircraft(
                    hexident,
                    "Expiring inactive vessel from state database",
                    no_backoff=True)
                hexidents_to_remove.add(hexident)

        for hexident in hexidents_to_remove:
            del self.database[hexident]

    def datetime_msg_generated(self, message):
        """
        Generate a datetime from ADSB message.

        Uses data from 'Date message generated' and 'Time message generated'
        fields from the ADSB message and returns a datetime.

        Parameters:
        message (list): ADSB Message (split)
        """
        # Note, the [0:15] below is to prevent issues where timestamps
        # have a higher resolution than what python can handle.
        # The %f accepts from 1 to 6 digits.
        # Some platforms are sending more than 6 digits, so this sets a limit.
        msgdtstring = "%sT%s" % (message[6], message[7][0:15])
        msgdt = datetime.datetime.strptime(
            msgdtstring,
            '%Y/%m/%dT%H:%M:%S.%f'
            )
        if self.verbose_logging:
            self.log("<%s> Datetime '%s' generated from string '%s'." % \
                (inspect.currentframe().f_code.co_name,
                msgdt, 
                msgdtstring))
        return msgdt

    def add_vessel_to_db(self, message):
        """
        Add a vessel to the state database.

        Parameters:
        message (list): ADSB Message (split)
        """
        self.database[message[4]] = dict()
        self.database[message[4]]['hexident'] = \
            message[4].strip()
        self.database[message[4]]['data_to_send'] = \
            list()
        
        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)
        
        self.database[message[4]]['lastseen'] = \
            self.current_message_datetime

        if self.verbose_logging:
            self.log("<%s> Setting lastseen for '%s' to '%s'" % \
                (inspect.currentframe().f_code.co_name,
                self.database[message[4]]['hexident'], 
                self.database[message[4]]['lastseen']))
        
        self.database[message[4]]['callsign'] = \
            message[10].strip()
        self.database[message[4]]['current_altitude'] = \
            message[11].strip()
        self.database[message[4]]['current_groundspeed'] = \
            message[12].strip()
        self.database[message[4]]['current_track'] = \
            message[13].strip()
        self.database[message[4]]['current_latitude'] = \
            message[14].strip()
        self.database[message[4]]['current_longitude'] = \
            message[15].strip()
        self.database[message[4]]['current_verticalrate'] = \
            message[16].strip()
        self.database[message[4]]['squawk'] = \
            message[17].strip()
        self.database[message[4]]['alert_squawk_change'] = \
            message[18].strip()
        self.database[message[4]]['emergency'] = \
            message[19].strip()
        self.database[message[4]]['spi_ident'] = \
            message[20].strip()
        self.database[message[4]]['is_on_ground'] = \
            message[21].strip()
        self.log_aircraft(message[4], "Now receiving from this vessel", True)

    def update_vessel_in_db(self, message):
        """
        Update a vessel in the state database.

        Parameters:
        message (list): ADSB Message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)
        
        self.database[message[4]]['lastseen'] = \
            self.current_message_datetime

        if self.verbose_logging:
            self.log("<%s> Updating lastseen for '%s' to '%s'" % \
                (inspect.currentframe().f_code.co_name,
                message[4], 
                self.database[message[4]]['lastseen']))

        if message[10] != '':
            self.database[message[4]]['callsign'] = \
                message[10].strip()

        if message[11] != '':
            # altitude is in ft
            self.database[message[4]]['current_altitude'] = \
                message[11].strip()

        if message[12] != '':
            self.database[message[4]]['current_groundspeed'] = \
                message[12].strip()

        if message[13] != '':
            self.database[message[4]]['current_track'] = \
                message[13].strip()

        if message[14] != '':
            self.database[message[4]]['current_latitude'] = \
                message[14].strip()

        if message[15] != '':
            self.database[message[4]]['current_longitude'] = \
                message[15].strip()

        if message[16] != '':
            self.database[message[4]]['current_verticalrate'] = \
                message[16].strip()

        if message[17] != '':
            self.database[message[4]]['squawk'] = \
                message[17].strip()

        if message[18] != '':
            self.database[message[4]]['alert_squawk_change'] = \
                message[18].strip()

        if message[19] != '':
            self.database[message[4]]['emergency'] = \
                message[19].strip()

        if message[20] != '':
            self.database[message[4]]['spi_ident'] = \
                message[20].strip()

        if message[21] != '':
            self.database[message[4]]['is_on_ground'] = \
                message[21].strip()

    def handle_msg_type_3(self, message):
        """
        Handle ADSB message type 3 (ES Airborne Position Message).

        Parameters:
        message (list): ADSB message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)
        
        self.database[message[4]]['data_to_send'].append(
            {'current_altitude': message[11],
            'current_latitude': message[14],
            'current_longitude': message[15],
            'datetime': self.current_message_datetime,
            })              
        
        self.log_aircraft(message[4], "Alt: %s, Lat: %s, Long: %s" % (
            message[11],
            message[14],
            message[15],
            ))

    def handle_msg_type_4(self, message):
        """
        Handle ADSB message type 3 (ES Airborne Velocity Message).

        Parameters:
        message (list): ADSB message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)

        self.database[message[4]]['data_to_send'].append(
            {'current_groundspeed': message[12],
            'current_track': message[13],
            'current_verticalrate': message[16],
            'datetime': self.current_message_datetime,
            })
        
        self.log_aircraft(
            message[4],
            "GroundSpeed: %s, Track: %s, VerticalRate: %s" % (
                message[12],
                message[13],
                message[16]
                ))

    def handle_msg_type_5(self, message):
        """
        Handle ADSB message type 5 (Surveillance Alt Message).

        Parameters:
        message (list): ADSB message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)

        self.database[message[4]]['data_to_send'].append(
            {'current_altitude': message[11],
            'datetime': self.current_message_datetime,
            })

        self.log_aircraft(message[4], "Alt: %s" % (message[11]))

    def handle_msg_type_6(self, message):
        """
        Handle ADSB message type 6 (Surveillance ID Message).

        Parameters:
        message (list): ADSB message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)

        self.database[message[4]]['data_to_send'].append(
            {'current_altitude': message[11],
            'datetime': self.current_message_datetime,
            })

        self.log_aircraft(message[4], "Alt: %s" % (message[11]))

    def handle_msg_type_7(self, message):
        """
        Handle ADSB message type 7 (Air To Air Message).

        Parameters:
        message (list): ADSB message (split)
        """

        if self.current_message_datetime == None:
            self.current_message_datetime = self.datetime_msg_generated(message)

        self.database[message[4]]['data_to_send'].append(
            {'current_altitude': message[11],
            'datetime': self.current_message_datetime,
            })

        self.log_aircraft(message[4], "Alt: %s" % (message[11]))

    def is_message_valid(self, message):
        """
        Perform basic checks against ADSB message (unsplit).

        Parameters:
        message (str): ADSB message (unsplit)
        """
        # Check if we have data to process
        if len(message) > 0:

            # Check if the message contains at least one comma
            if message.count(',') >= 1:

                # Split message into fields
                message = message.split(',')

                # Make sure there was data to split
                # Valid messages will have at least 10 fields
                if len(message) == 22:

                    # If message type is MSG (TRANSMISSION MESSAGE)
                    if message[0].upper() == "MSG":

                        return True

        return False

    def prepare_line_protocol(self, message, data_to_send):
        """
        Prepare line protocol to be sent to Telegraf.

        Parameters:
        message (list): ADSB Message (processed)
        data_to_send (dict): Dictionary containing data to send
        """
        # generate line protocol
        line_protocol = str()

        # measurement
        line_protocol += "piaware"
        line_protocol += ","

        # tags
        line_protocol += "hexident="
        line_protocol += message[4].strip()
        line_protocol += ","

        line_protocol += "callsign="
        line_protocol += \
            self.database[message[4]]['callsign'].strip()
        line_protocol += ","

        line_protocol += "squawk="
        line_protocol += \
            self.database[message[4]]['squawk'].strip()
        line_protocol += " "

        # fields
        first = True
        valid = False
        for field in data_to_send.keys():

            if field == 'datetime':
                continue

            if data_to_send[field] != '':
                if not first:
                    line_protocol += ","
                line_protocol += field.strip()
                line_protocol += "="
                line_protocol += data_to_send[field].strip()
                first = False
                valid = True

        return valid, line_protocol

    def send_data(self, message):
        """
        Send data to Telegraf, if required.

        Parameters:
        message (list): ADSB Message (processed)
        """
        # Do we have data to send?
        if len(self.database[message[4]]['data_to_send']) >= 1:

            # Do we have a callsign?
            if (
                    self.database[message[4]]['callsign'] != ''
                    and
                    self.database[message[4]]['squawk'] != ''
            ):

                # iterate through data to send
                for data_to_send in self.database[message[4]]['data_to_send']:

                    valid, line_protocol = \
                        self.prepare_line_protocol(message, data_to_send)

                    # send line protocol
                    if valid:
                        self.send_line_protocol(line_protocol)

                # remove entries we've already sent
                self.database[message[4]]['data_to_send'] = list()

    def process_message(self, message):
        """
        Process an incoming ADSB message.

        Parameters:
        message (str): ADSB Message (unsplit)
        """
        if self.is_message_valid(message):

            # Split message into fields
            message = message.split(',')

            if self.verbose_logging:
                self.log("<%s> Message contents: '%s'" % \
                    (inspect.currentframe().f_code.co_name,
                    repr(message)))

            # If the aircraft does not exist in our database,
            # then create it
            if message[4].upper() not in self.database.keys():
                self.add_vessel_to_db(message)

            # If it does exist, then we update the values
            else:
                self.update_vessel_in_db(message)

            # ES Identification and Category (callsign update)
            if message[1] == '1':
                pass

            # ES Surface Position Message
            # (Triggered by nose gear squat switch.)
            elif message[1] == '2':
                pass

            # ES Airborne Position Message
            elif (message[1] == '3' and
                  message[11] != '' and
                  message[14] != '' and
                  message[15] != ''):
                self.handle_msg_type_3(message)

            # ES Airborne Velocity Message
            elif (message[1] == '4' and
                  message[12] != '' and
                  message[13] != '' and
                  message[16] != ''):

                self.handle_msg_type_4(message)

            # Surveillance Alt Message
            # Triggered by ground radar. Not CRC secured.
            # MSG,5 will only be output if  the aircraft has
            # previously sent a MSG,1, 2, 3, 4 or 8 signal.
            elif message[1] == '5' and message[11] != '':
                self.handle_msg_type_5(message)

            # Surveillance ID Message
            # Triggered by ground radar. Not CRC secured.
            # MSG,6 will only be output if  the aircraft has
            # previously sent a MSG,1, 2, 3, 4 or 8 signal.
            elif message[1] == '6' and message[11] != '':
                self.handle_msg_type_6(message)

            # Air To Air Message
            # Triggered from TCAS.
            # MSG,7 is now included in the SBS socket output.
            elif message[1] == '7' and message[11] != '':
                self.handle_msg_type_7(message)

            # All Call Reply
            # Broadcast but also triggered by ground radar
            elif message[1] == '8':
                pass

            # Send data to InfluxDB
            self.send_data(message)

        # Remove stale db entries if any exist
        self.clean_database()


def setup_socket(host, port):
    """
    Create and configures a socket to Telegraf.

    Parameters:
    host (str): Host/IP for Telegraf inputs.http_listener
    port (int): TCP port for Telegraf inputs.http_listener
    """
    logmessage = "CONNECT: Connecting to "
    logmessage += "%s:%s to receive dump1090 " % (host, port)
    logmessage += "TCP BaseStation output data"
    D.log(logmessage)
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connected = False
    while not connected:
        try:
            skt.connect((host, port))
            D.log("CONNECT: Connected OK, receiving data")
        except:
            connected = False
            D.log("CONNECT: Could not connect, retrying")
            time.sleep(1)
        else:
            connected = True
    skt.setblocking(False)
    skt.settimeout(1)
    return skt


if __name__ == "__main__":

    appdescription = 'Read dump1090/readsb TCP BaseStation data, '
    appdescription += 'convert to InfluxDB line protocol, and send to InfluxDB'

    parser = argparse.ArgumentParser(description=appdescription)
    parser.add_argument(
        '-ds',
        '--dump1090-server',
        default="127.0.0.1",
        help="Host/IP for dump1090 [127.0.0.1]"
        )
    parser.add_argument(
        '-dp',
        '--dump1090-port',
        default="30003",
        help="Port for dump1090 TCP BaseStation data [30003]"
        )
    help_telegraf_url = "URL for Telegraf inputs.http_listener "
    help_telegraf_url += "[http://127.0.0.1:8186/write]"
    parser.add_argument(
        '-tu',
        '--telegraf-url',
        default="http://127.0.0.1:8186/write",
        help=help_telegraf_url
        )
    parser.add_argument(
        '-v',
        '--verbose',
        default=False,
        type=bool,
        help="Verbose logging"
        )
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version='%(prog)s ' + str(__version__)
        )
    args = parser.parse_args()

    print(args)
    print("piaware2influx.py version %s" % (__version__))

    HOST = args.dump1090_server
    PORT = int(args.dump1090_port)

    if os.getenv('VERBOSE_LOGGING', "").upper().strip() == 'TRUE':
        VERBOSE_LOGGING = True
    elif args.verbose:
        VERBOSE_LOGGING = True
    else:
        VERBOSE_LOGGING = False

    D = ADSB_Processor(
        telegraf_url=args.telegraf_url,
        verbose_logging=VERBOSE_LOGGING,
        )

    s = setup_socket(HOST, PORT)

    while True:
        try:
            data = s.recv(1024)
            s.send(bytes("\r\n", "UTF-8"))
            D.add_data_to_buffer(data.decode("utf-8"))
        except socket.timeout:
            # print("TIMEOUT!")
            pass
        except socket.error:
            D.log("CONNECT: Disconnected from dump1090!")
            s.close()
            time.sleep(1)
            s = setup_socket(HOST, PORT)
