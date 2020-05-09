#!/usr/bin/env python3

import time
from sem6000 import SEMSocket

import bluepy

socket = None

while True:
    time.sleep(1)
    try:
        if socket == None:
            print("Connecting... ", end="")
            socket = SEMSocket('f0:c7:7f:0d:e7:17')
            print("Success!")
            print("You're now connected to: {} (Icon: {})".format(socket.name, socket.icons[0]))
            if socket.login("1234") and socket.authenticated:
                print("Login successful!")
                socket.getSynConfig()
                print()
                print("=== Tariff settings ===")
                print("Default charge:", socket.default_charge)
                print("Night charge:", socket.night_charge)
                print("Night tariff from {} to {}".format(socket.night_charge_start_time.tm_hour, socket.night_charge_end_time.tm_hour))
                print()
                print("=== Other settings ===")
                print("Night mode:", "active" if socket.night_mode else "inactive")
                print("Power protection:", socket.power_protect)
                print()

        socket.getStatus()
        print("=== {} ({}) ===".format(socket.mac_address, "on" if socket.powered else "off"))
        print("\t{}V {}A → {}W@{}Hz (PF: {})".format(socket.voltage, socket.current, socket.power, socket.frequency, socket.power_factor))
    except (SEMSocket.NotConnectedException, bluepy.btle.BTLEDisconnectError, BrokenPipeError):
        print("Restarting...")
        if socket != None:
            socket.disconnect()
            socket = None

