while True:
	print("Sending GGA...")
	gga = "$GPGGA,115739.00,4158.8441367,N,09147.4416929,W,4,13,0.9,255.747,M,-32.00,M,01,0000*6E\r\n"
	stream.write(gga.encode('utf-8'))
	time.sleep(.2)