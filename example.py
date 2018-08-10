from sem6000 import SEMSocket
import time
socket = SEMSocket('f0:c7:7f:0d:e7:17')

socket.login("1337")
while True:
    time.sleep(1)
    socket.getStatus()
    print("=== {} ({}) ===".format(socket.mac_address, "on" if socket.powered else "off"))
    print("\t{}V {}A → {}W@{}Hz".format(socket.voltage, socket.current, socket.power, socket.frequency))
