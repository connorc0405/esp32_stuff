import datetime
import socket
import time


from pyubx2 import UBXReader, UBXMessage, GET

# Format is hhmmss.ss


def send_msg(conn, pkt):
	len_pkt = len(pkt)
	total_bytes_sent=0
	while total_bytes_sent < len_pkt:
		bytes_sent = conn.send(pkt)
		total_bytes_sent += bytes_sent


def gen_msg(conn):
	itow = 172399
	lat=423362230
	lon=-710865380
	while True:
		nav_sol = UBXMessage(
			"NAV",
			"NAV-SOL",
			GET,
			iTOW=itow,
			fTOW=0,
			week=2150,
			gpsFix=3,
			numSV=12
			# ecefx=1530567000,
			# ecefy=-4466994000,
			# ecefz=273291000
		)
		nav_pvt = UBXMessage(
			"NAV",
			"NAV-PVT",
			GET,
			iTOW=itow,
			lat=lat,
			lon=lon,
			height=10,
			hMSL=1000,
			fixType=3,
			numSV=12
		)
		# print("Sending NAV-SOL...")
		# stream.write(nav_sol.serialize())
		print("Sending NAV-PVT...")
		conn.sendall(nav_pvt.serialize())
		# print(len(nav_pvt.serialize()))
		itow += 200
		lat+=200
		lon+=200
		time.sleep(.2)


def main():
	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	conn.connect(("10.10.10.1", 8080))
	gen_msg(conn)


if __name__ == "__main__":
	main()



