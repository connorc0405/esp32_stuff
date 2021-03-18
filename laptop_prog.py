import datetime
import socket
import time

import pynmea2


conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
conn.connect(("10.10.10.1", 8080))

# Format is hhmmss.ss

while True:
	now = datetime.datetime.now()
	formatted = now.strftime("%H%M%S.%f")[:-4]
	test_sentence = str(pynmea2.GGA('GP', 'GGA', (f"{formatted}", '1929.045', 'S', '02410.506', 'E', '1', '12', '2.6', '100.00', 'M', '-33.9', 'M', '', '0000')))
	test_sentence = test_sentence.encode('utf-8')
	test_sentence += b"\r\n"
	print(test_sentence)
	conn.sendall(test_sentence)
	time.sleep(.19)