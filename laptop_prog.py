import datetime
import socket
import threading
import time

from pyubx2 import UBXReader, UBXMessage, GET


REMOTE_IP_ADDR = "10.10.10.1"
REMOTE_PORT = 8080


class GPSData():
	def __init__(self, itow, lat, lon, h_msl, fix_type, num_sats):
		self.itow = itow
		self.lat = lat
		self.lon = lon
		self.h_msl = h_msl
		self.fix_type = fix_type
		self.num_sats = num_sats
		self.lock = threading.Lock()


def send_msg(conn, pkt):
	len_pkt = len(pkt)
	total_bytes_sent=0
	while total_bytes_sent < len_pkt:
		bytes_sent = conn.send(pkt)
		total_bytes_sent += bytes_sent


def gen_msgs(conn, gps_data):
	num = 1
	while True:
		gps_data.lock.acquire()
		nav_pvt = UBXMessage(
			"NAV",
			"NAV-PVT",
			GET,
			iTOW=gps_data.itow,
			lat=gps_data.lat,
			lon=gps_data.lon,
			hMSL=gps_data.h_msl,
			fixType=gps_data.fix_type,
			numSV=gps_data.num_sats
		)
		gps_data.itow += 200
		gps_data.lock.release()
		print(f"Sending NAV-PVT {num}")
		num+=1
		send_msg(conn, nav_pvt.serialize())
		time.sleep(.2)


def key_monitor(gps_data):
	while True:
		char = input()
		print(repr(char))
		if char == 'w':  # increase latitude
			print("north")
			gps_data.lock.acquire()
			gps_data.lat += 200
			gps_data.lock.release()

		elif char == 's':  # decrease latitude
			print("south")
			gps_data.lock.acquire()
			gps_data.lat -= 200
			gps_data.lock.release()

		elif char == 'a':  # increase longitude
			print("east")
			gps_data.lock.acquire()
			gps_data.lon += 200
			gps_data.lock.release()

		elif char == 'd':  # decrease longitude
			print("west")
			gps_data.lock.acquire()
			gps_data.lon -= 200
			gps_data.lock.release()

		elif char == '[':  # increase height
			print("up")
			gps_data.lock.acquire()
			gps_data.h_msl += 1000
			gps_data.lock.release()

		elif char == '\'':  # decrease height
			print("down")
			gps_data.lock.acquire()
			gps_data.h_msl -= 1000
			gps_data.lock.release()

		else:
			print("Unrecognized Key")


def main():
	gps_data = GPSData(itow=172399, lat=423362230, lon=-710865380, h_msl=1000, fix_type=3, num_sats=12)

	input_thread = threading.Thread(target=key_monitor, args=(gps_data,))
	input_thread.start()

	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	conn.connect((REMOTE_IP_ADDR, REMOTE_PORT))
	print(f"Connected {REMOTE_IP_ADDR}:{REMOTE_PORT}")

	gen_msgs(conn, gps_data)


if __name__ == "__main__":
	main()



