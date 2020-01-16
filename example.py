#!/usr/bin/env python3

import time
from sem6000 import SEMSocket

import bluepy

socket = None

while True:
    time.sleep(1)
    try:
        if socket == None:
            print("Connecting...")

            # auto_reconnect_timeout enabled auto reconnect if sending a command fails. Valid values:
            # None (default): everything that fails throws NotConnectedException's
            # -1: infinite retries
            # integer: seconds before exception is thrown

            socket = SEMSocket('f0:c7:7f:0d:e7:17', auto_reconnect_timeout=None)
            print("Connected.")

            #socket.login("1337")
            #socket.changePassword("1234")
            #socket.login("1234")

        socket.getStatus()
        socket.setStatus(True)
        print("=== {} ({}) ===".format(socket.mac_address, "on" if socket.powered else "off"))
        print("\t{}V {}A → {}W@{}Hz".format(socket.voltage, socket.current, socket.power, socket.frequency))
    except (SEMSocket.NotConnectedException, bluepy.btle.BTLEDisconnectError):
        print("Restarting...")
        if socket != None:
            socket.disconnect()
            socket = None

