from serial import Serial
from pyubx2 import UBXReader

stream = open('listening_gps_which_listens_board_115200_2.out', 'rb')
# stream = open('board_gps_boot.txt', 'rb')
# stream = Serial('/dev/tty.usbserial-145230', 115200, timeout=5)
reader = UBXReader(stream)

for (raw_data, parsed_data) in reader: print(parsed_data)
# (raw_data, parsed_data) = reader.read()
# print(parsed_data)