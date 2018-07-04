

# Protocol data from this URL:
# http://woodair.net/sbs/article/barebones42_socket_data.htm

import socket
import datetime
import time
import argparse
import requests


class ADSB_Processor(object):
	def __init__(self, telegraf_url):
		self._clear_buffer()
		self.database = {}
		self.messages_processed = 0
		self.points_sent = 0
		self.telegraf_url = telegraf_url

	def send_line_protocol(self, line_protocol):
		url = "%s?precision=s"
		try:
			r = requests.post(self.telegraf_url, data=line_protocol)
			self.points_sent += 1
		except:
			self.log("ERROR: could not submit line protocol! '%s'" % (repr(line_protocol)))
		if r.status_code != 204:
			self.log("ERROR: telegraf status code was '%s', expected '204'! " % (r.status_code))

	def log(self, text):
		print("Piaware2Influx: %s {%s msgs rx'd, %s points tx'd}" % (text, str(self.messages_processed), str(self.points_sent)))

	def log_aircraft(self, hexident, text, no_backoff=False):
		logstuff = True

		# if this vessel hasn't been logged, set up 'lastlogged' info
		if 'lastlogged' not in self.database[hexident].keys():
			logstuff = True
			self.database[hexident]['lastlogged'] = datetime.datetime.now()

		# if the vessel has been logged
		else:
			# if we need to back off (ie: log once per second)
			if not no_backoff:
				cutoff = datetime.datetime.now() - datetime.timedelta(seconds=60)
				if self.database[hexident]['lastlogged'] > cutoff:
					logstuff = False

		if logstuff:
			logtext = "AIRCRAFT ["
			logtext += hexident
			logtext += "]"
			if self.database[hexident]['callsign'] != "":
				logtext += "(%s)" % (self.database[hexident]['callsign'])
			logtext += ": "
			logtext += text
			self.log(logtext)

	def _clear_buffer(self):
		self.buffer = str()

	def add_data_to_buffer(self, data):
	    self.buffer = self.buffer + data
	    self.process_buffer()

	def process_buffer(self):
		new_message = str()
		last_two = "  "
		count = 0

		# Read buffer up to end of message.
		# If any data is left in the buffer, leave it there
		#   so when we receive the remainder of the data we can
		#   assemble the message.
		for c in self.buffer:
			if c != "\r" and c != "\n":
				new_message += c
			
			# maintain a record of the last two chars
			# used to detect end of message '\r\n'
			last_two += c
			last_two = last_two[1:]
			
			# count number of characters read, so we can
			#   remove this many chars from the start of
			#   the buffer.
			count += 1

			# if we get to an end of message, then we process
			#   the message, and reset our counters & stuff
			if last_two == '\r\n':
				#print("MESSAGE: ", repr(new_message), len(new_message.split(',')))
				self.process_message(new_message)
				self.buffer = self.buffer[count:]
				self.messages_processed += 1
				count = 0
				new_message = ""

	def clean_database(self):
		for hexident in self.database:
			# work out what was 15 mins ago
			cutoff = datetime.datetime.now() - datetime.timedelta(minutes=15)
			if self.database[hexident]['lastseen'] < cutoff:
				self.log("CLEANUP [%s]: Expiring inactive vessel" % (hexident))
				del self.database[hexident]

	def process_message(self, message):

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

						# If the aircraft does not exist in our database, then create it
						if message[4].upper() not in self.database.keys():

							self.database[message[4]] = dict()
							self.database[message[4]]['hexident'] = message[4].strip()
							self.database[message[4]]['data_to_send'] = list()
							msgdtstring = "%sT%s" % (message[6],message[7])
							msgdt = datetime.datetime.strptime(msgdtstring, '%Y/%m/%dT%H:%M:%S.%f')
							self.database[message[4]]['lastseen'] = msgdt
							self.database[message[4]]['callsign'] = message[10].strip()
							self.database[message[4]]['current_altitude'] = message[11].strip()
							self.database[message[4]]['current_groundspeed'] = message[12].strip()
							self.database[message[4]]['current_track'] = message[13].strip()
							self.database[message[4]]['current_latitude'] = message[14].strip()
							self.database[message[4]]['current_longitude'] = message[15].strip()
							self.database[message[4]]['current_verticalrate'] = message[16].strip()
							self.database[message[4]]['squawk'] = message[17].strip()
							self.database[message[4]]['alert_squawk_change'] = message[18].strip()
							self.database[message[4]]['emergency'] = message[19].strip()
							self.database[message[4]]['spi_ident'] = message[20].strip()
							self.database[message[4]]['is_on_ground'] = message[21].strip()

							self.log_aircraft(message[4], "Now receiving from this vessel", True)

						# If it does exist, then we update the values
						else:
							msgdtstring = "%sT%s" % (message[6],message[7])
							msgdt = datetime.datetime.strptime(msgdtstring, '%Y/%m/%dT%H:%M:%S.%f')
							self.database[message[4]]['lastseen'] = msgdt

							if message[10] != '':
								self.database[message[4]]['callsign'] = message[10].strip()

							if message[11] != '':
								# altitude is in ft
								self.database[message[4]]['current_altitude'] = message[11].strip()

							if message[12] != '':
								self.database[message[4]]['current_groundspeed'] = message[12].strip()

							if message[13] != '':
								self.database[message[4]]['current_track'] = message[13].strip()

							if message[14] != '':
								self.database[message[4]]['current_latitude'] = message[14].strip()

							if message[15] != '':
								self.database[message[4]]['current_longitude'] = message[15].strip()

							if message[16] != '':
								self.database[message[4]]['current_verticalrate'] = message[16].strip()

							if message[17] != '':
								self.database[message[4]]['squawk'] = message[17].strip()

							if message[18] != '':
								self.database[message[4]]['alert_squawk_change'] = message[18].strip()

							if message[19] != '':
								self.database[message[4]]['emergency'] = message[19].strip()

							if message[20] != '':
								self.database[message[4]]['spi_ident'] = message[20].strip()

							if message[21] != '':
								self.database[message[4]]['is_on_ground'] = message[21].strip()

						# ES Identification and Category (callsign update)
						if message[1] == '1':
							pass

						# ES Surface Position Message (Triggered by nose gear squat switch.)
						elif message[1] == '2':
							pass

						# ES Airborne Position Message
						elif message[1] == '3' and message[11] != '' and message[14] != '' and message[15] != '':
							self.database[message[4]]['data_to_send'].append({'current_altitude': message[11],
								                                              'current_latitude': message[14],
								                                              'current_longitude': message[15],
								                                              'mt': '3',
								                                              'datetime': msgdt,
								                                             })
							self.log_aircraft(message[4], "Alt: %s, Lat: %s, Long: %s" % (message[11], message[14], message[15]))

						# ES Airborne Velocity Message
						elif message[1] == '4' and message[12] != '' and message[13] != '' and message[16] != '':
							self.database[message[4]]['data_to_send'].append({'current_groundspeed': message[12],
								                                              'current_track': message[13],
								                                              'current_verticalrate': message[16],
								                                              'mt': '4',
								                                              'datetime': msgdt,
								                                             })
							self.log_aircraft(message[4], "GroundSpeed: %s, Track: %s, VerticalRate: %s" % (message[12], message[13], message[16]))


						# Surveillance Alt Message
						# Triggered by ground radar. Not CRC secured. 
						# MSG,5 will only be output if  the aircraft has previously sent a
					    # MSG,1, 2, 3, 4 or 8 signal.
						elif message[1] == '5' and message[11] != '':
							self.database[message[4]]['data_to_send'].append({'current_altitude': message[11],
																			  'datetime': msgdt,
																			  'mt': '5',
								                                             })
							self.log_aircraft(message[4], "Alt: %s" % (message[11]))

						# Surveillance ID Message
						# Triggered by ground radar. Not CRC secured. 
						# MSG,6 will only be output if  the aircraft has previously sent a
						# MSG,1, 2, 3, 4 or 8 signal.
						elif message[1] == '6' and message[11] != '':
							self.database[message[4]]['data_to_send'].append({'current_altitude': message[11],
																			  'datetime': msgdt,
																			  'mt': '6',
								                                             })
							self.log_aircraft(message[4], "Alt: %s" % (message[11]))

						# Air To Air Message
						# Triggered from TCAS. 
						# MSG,7 is now included in the SBS socket output.
						elif message[1] == '7' and message[11] != '':
							self.database[message[4]]['data_to_send'].append({'current_altitude': message[11],
																			  'datetime': msgdt,
																			  'mt': '7',
								                                             })
							self.log_aircraft(message[4], "Alt: %s" % (message[11]))

						# All Call Reply
						# Broadcast but also triggered by ground radar
						elif message[1] == '8':
							pass


						# Do we have data to send?
						if len(self.database[message[4]]['data_to_send']) >= 1:

							# Do we have a callsign?
							if self.database[message[4]]['callsign'] != '' and self.database[message[4]]['squawk'] != '':
								
								# iterate through data to send
								for data_to_send in self.database[message[4]]['data_to_send']:

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
									line_protocol += self.database[message[4]]['callsign'].strip()
									line_protocol += ","

									line_protocol += "squawk="
									line_protocol += self.database[message[4]]['squawk'].strip()
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
									
									# add timestamp
									#line_protocol += " "
									#line_protocol += str(int(time.mktime(data_to_send['datetime'].timetuple())))
									#line_protocol += "000000000" # sec -> ms -> µs -> ns
									#line_protocol += str(time.mktime(data_to_send['datetime'].timetuple()) * 1000 * 1000 * 1000) # sec -> ms -> µs -> ns

									# send line protocol
									if valid:
										self.send_line_protocol(line_protocol)

								# remove entries we've already sent
								self.database[message[4]]['data_to_send'] = list()

		self.clean_database()


def setup_socket(host,port):
	D.log("CONNECT: Connecting to %s:%s to receive dump1090 TCP BaseStation output data" % (HOST, PORT))
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	connected = False
	while not connected:
		try:
			s.connect((HOST, PORT))
			print("CONNECT: Connected OK, receiving data")
		except:
			connected = False
			print("CONNECT: Could not connect, retrying")
			time.sleep(1)
		else:
			connected = True
	s.setblocking(False)
	s.settimeout(1)
	return s


def main():
	pass
if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Read dump1090 TCP BaseStation data, convert to InfluxDB line protocol, and send to InfluxDB')
	parser.add_argument('-ds', '--dump1090-server', default="127.0.0.1", help="Host/IP for dump1090 [127.0.0.1]")
	parser.add_argument('-dp', '--dump1090-port', default="30003", help="Port for dump1090 TCP BaseStation data [30003]")
	parser.add_argument('-tu', '--telegraf-url', default="http://127.0.0.1:8186/write", help="URL for Telegraf inputs.http_listener [http://127.0.0.1:8186/write]")
	args = parser.parse_args()

	print(args)

	HOST = args.dump1090_server
	PORT = int(args.dump1090_port)

	D = ADSB_Processor(args.telegraf_url)

	s = setup_socket(HOST, PORT)

	while True:
		try:
			data = s.recv(1024)
			s.send(bytes( "\r\n", "UTF-8" ))
			D.add_data_to_buffer(data.decode("utf-8"))
		except socket.timeout:
			#print("TIMEOUT!")
			pass
		except socket.error:
			D.log("CONNECT: Disconnected from dump1090!")
			s.close()
			time.sleep(1)
			s = setup_socket(HOST, PORT)
