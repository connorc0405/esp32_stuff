#! /usr/bin/env python

"""
Requirements:
- pynmea2
- pyserial

http://dangerousprototypes.com/blog/2009/10/09/bus-pirate-raw-bitbang-mode/
http://dangerousprototypes.com/blog/2009/10/19/bus-pirate-binary-uart-mode/
"""

import sys
import io

import serial
import pynmea2

# set the following value to your buspirate's port
PORT = "/dev/tty.usbserial-A702YQFN"


def enter_bitbang(conn):
	conn.flushInput()
	for _ in range(20):
		conn.write(b'\x00')
	if not b'BBIO' in conn.read(5):
		cleanup(conn)
		print("failed to enter bitbang")
		sys.exit(1)


def exit_bitbang(conn):
	conn.write(b'\x00')
	conn.write(b'\x0F')


def enter_uart(conn):
	conn.write(b'\x03')
	if not b'ART1' in conn.read(4):
		cleanup(conn)
		print("failed to enter uart")
		sys.exit(1)


def cleanup(conn):
	exit_bitbang(conn)


def configure(conn, byte):
	conn.write(byte)
	if not b'\x01' in conn.read(1):
		cleanup(conn)
		print("failed to configure settings")
		sys.exit(1)


conn = serial.Serial(PORT, 115200, timeout=0.1)

# setup
enter_bitbang(conn)
enter_uart(conn)

# configure settings
# set baud rate to 9600
configure(conn, b'\x64')
# # set baud rate to 115200
# configure(conn, b'\x6A')
# set pin output to 3.3v
configure(conn, b'\x90')
# enable power supply
configure(conn, b'\x48')

print("setup done")

# start bridge
conn.write(b'\x0f')
conn.read(1)
sio = io.TextIOWrapper(io.BufferedRWPair(conn, conn))

while True:
	try:
		output = sio.read()
		lines = output.split("\n")
		for line in lines:
			if line:
				msg = pynmea2.parse(line)
				print(repr(msg))
	except serial.SerialException as e:
		print("Device error: {}".format(e))
		sys.exit(1)
	except pynmea2.ParseError as e:
		print("Parse error: {}".format(e))
		continue
	except KeyboardInterrupt:
		break

cleanup(conn)
