import time
import threading

from serial import Serial
from pyubx2 import UBXReader, UBXMessage, GET


def send_sol(stream):
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
			hMSL=1000,
			fixType=3
		)
		print("Sending NAV-SOL...")
		stream.write(nav_sol.serialize())
		print("Sending NAV-PVT...")
		stream.write(nav_pvt.serialize())
		itow += 200
		lat+=200
		lon+=200
		time.sleep(.2)


if __name__ == "__main__":
	stream = Serial('/dev/tty.usbserial-145230', 115200, timeout=5)
	reader = UBXReader(stream)

	sol_thread = threading.Thread(target=send_sol, args=(stream,))
	sol_thread.start()

	for (_, parsed_data) in reader:
		print(parsed_data)
		if parsed_data.identity == "CFG-MSG" and parsed_data.msgID == 6:  # Probably telling us to enable NAV-SOL (msg ID 6)
			ack = UBXMessage("ACK", "ACK-ACK", GET, clsID=6, msgID=1)  # 6 is CFG class id, 1 is CFG-MSG message id
			print("Sending ACK...")
			# print(ack.serialize())
			stream.write(ack.serialize())
			break
		if parsed_data.identity == "CFG-PRT": #and parsed_data.msgID == 6:  # Probably asking for port config
			print(parsed_data)
			# ack = UBXMessage("ACK", "ACK-ACK", GET, clsID=6, msgID=1)  # 6 is CFG class id, 1 is CFG-MSG message id
			# print("Sending ACK...")
			# print(ack.serialize())
			# stream.write(ack.serialize())
			# break




