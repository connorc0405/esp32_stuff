from serial import Serial
from pyubx2 import UBXReader, UBXMessage, GET
import time

stream = Serial('/dev/tty.usbserial-145230', 115200, timeout=5)
reader = UBXReader(stream)

for (_, parsed_data) in reader:
	if parsed_data.identity == "CFG-MSG" and parsed_data.msgID == 6:  # Probably telling us to enable NAV-SOL (msg ID 6)
		ack = UBXMessage("ACK", "ACK-ACK", GET, clsID=6, msgID=1)  # 6 is CFG class id, 1 is CFG-MSG message id
		print("Sending ACK...")
		print(ack.serialize())
		stream.write(ack.serialize())
		break

while True:
	print("Sending NAV-SOL...")
	stream.write(b"\xb5b\x01\x064\x00d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\xc4C\x04&\x00\x00\x00\x00\x00\x00\x00\x00\xc0\xdf\xb6&\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00}\x00\x00'\x02\x00\xe0J\x03\x00m\xcbO")
	time.sleep(.2)
