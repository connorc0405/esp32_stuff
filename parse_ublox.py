from serial import Serial
from pyubx2 import UBXReader, UBXMessage

# stream = open('captures/listening_gps_which_listens_board_115200_2.out', 'rb')
# stream = open('captures/board_gps_boot.txt', 'rb')
stream = Serial('/dev/tty.usbserial-145210', 115200, timeout=5)
reader = UBXReader(stream)

for (raw_data, parsed_data) in reader: print(parsed_data)


for (_, parsed_data) in reader:
	print(parsed_data)
	# if parsed_data.identity == "CFG-MSG":  # Probably telling us to enable NAV-SOL
	#if parsed_data.identity == "ACK-ACK":  # Probably telling us to enable NAV-SOL
		# print(parsed_data.msgClass)
		# print(parsed_data.msgID)
		# ack = UBXMessage('ACK', 'ACK-ACK', GET)
		# print(ack)
		# print(parsed_data.clsID)

	
	# <UBX(ACK-ACK, clsID=CFG, msgID=CFG-MSG)>