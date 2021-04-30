from serial import Serial

file = open('screenlog.0', 'rb')
content = file.read()
#print(repr(content))
#msgs = content.
print(content[0:5])

serialOut = Serial('/dev/tty.usbserial-145230',115200, timeout=5)
serialOut.write(content)