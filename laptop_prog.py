import datetime
import socket
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


def send_msg(conn, pkt):
	len_pkt = len(pkt)
	total_bytes_sent=0
	while total_bytes_sent < len_pkt:
		bytes_sent = conn.send(pkt)
		total_bytes_sent += bytes_sent


def gen_msgs(conn, gps_data):
	while True:
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
		print("Sending NAV-PVT...")
		conn.sendall(nav_pvt.serialize())
		gps_data.itow += 200
		# gps_data.lat+=200
		# gps_data.lon+=200
		time.sleep(.2)


def main():
	gps_data = GPSData(itow=172399, lat=423362230, lon=710865380, h_msl=1000, fix_type=3, num_sats=12)


	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	conn.connect((REMOTE_IP_ADDR, REMOTE_PORT))
	print(f"Connected {REMOTE_IP_ADDR}:{REMOTE_PORT}")

	gen_msgs(conn, gps_data)


if __name__ == "__main__":
	main()



