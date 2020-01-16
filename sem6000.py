from bluepy import btle
import time
import uuid

class SEMSocket():
    password = "0000"
    powered = False
    voltage = 0
    current = 0
    power = 0
    frequency = 0
    mac_address = ""
    custom_service = None
    _read_char = None
    _write_char = None
    _notify_char = None
    _btle_device = None

    def __init__(self, mac):
        self.mac_address = mac
        self._btle_device = btle.Peripheral(None ,addrType=btle.ADDR_TYPE_PUBLIC,iface=0)
        try:
            self.reconnect()
        except self.NotConnectedException:
            # initial connection may fail. It is up to the code what to do
            pass

    def getStatus(self):
        #15, 5, 4, 0, 0, 0, 5, -1, -1
        cmd = bytearray([0x04])
        payload = bytearray([0x00, 0x00, 0x00])
        msg = self.BTLEMessage(self, cmd, payload)
        msg.send()

    def setStatus(self, status):
        # 0f 06 03 00 01 00 00 05 ff ff  -> on
        # 0f 06 03 00 00 00 00 04 ff ff  -> off
        cmd = bytearray([0x03])
        payload = bytearray([0x00, status, 0x00, 0x00])
        msg = self.BTLEMessage(self, cmd, payload)
        msg.send()

    def login(self, password):
        self.password = password
        cmd = bytearray([0x17])
        payload = bytearray()
        payload.append(0x00)
        payload.append(0x00)
        for i in range(4):
            payload.append(int(self.password[i]))
        payload.append(0x00)
        payload.append(0x00)
        payload.append(0x00)
        payload.append(0x00)
        msg = self.BTLEMessage(self, cmd, payload)
        msg.send()

    def changePassword(self, newPassword):
        cmd = bytearray([0x17])
        payload = bytearray()
        payload.append(0x00)
        payload.append(0x01)
        for i in range(4):
            payload.append(int(self.newPassword[i]))
        for i in range(4):
            payload.append(int(self.password[i]))
        self.password = newPassword
        msg = self.BTLEMessage(self, cmd, payload)
        msg.send()

    @property
    def connected(self):
        try:
            if "conn" in self._btle_device.status().get("state"):
                return True
            else:
                return False
        except:
            return False

    def reconnect(self):
        self.disconnect()
        self.connect()
        if not self.connected:
            raise self.NotConnectedException

    def connect(self):
        self.disconnect()
        self._btle_device.connect(self.mac_address)
        self._btle_handler = self.BTLEHandler(self)

        self._custom_service = self._btle_device.getServiceByUUID(0xfff0)
        self._read_char      = self._custom_service.getCharacteristics("0000fff1-0000-1000-8000-00805f9b34fb")[0]
        self._write_char     = self._custom_service.getCharacteristics("0000fff3-0000-1000-8000-00805f9b34fb")[0]
        self._notify_char    = self._custom_service.getCharacteristics("0000fff4-0000-1000-8000-00805f9b34fb")[0]
        self._btle_device.setDelegate(self._btle_handler)

    def disconnect(self):
        if self.connected == True:
            self._btle_device.disconnect()

    #def SynVer(self):
    #    print("SynVer")
    #    self.read_char.read_value()

    #def GetSynConfig(self):
    #    print("GetSynConfig")
    #    #15, 5, 16, 0, 0, 0, 17, -1, -1
    #    self.write_char.write_value(bytearray(b'\x0f\x05\x10\x00\x00\x00\x11\xff\xff'))

    #def ______RESET(self):
    #    #15, 5, 16, 0, 0, 0, 17, -1, -1  ??? maybe reset?
    #    pass

    #def GetSN(self):
    #    print("GetSN")
    #    #15, 5, 17, 0, 0, 0, 18, -1, -1
    #    self.write_char.write_value(bytearray(b'\x0f\x05\x11\x00\x00\x00\x12\xff\xff'))

    #    self.SynVer()
    #    self.notify_char.enable_notifications()
    #    self.Login("1337")
    #    self.GetSynConfig()
    #    #self.GetSN()

    class NotConnectedException(Exception):
        pass

    class BTLEMessage():
        MAGIC_START = bytearray([0x0f])
        MAGIC_END = bytearray([0xff, 0xff])
        __data = bytearray()
        __cmd = bytearray(1) # cmd cannot be empty
        __payload = bytearray()

        def __init__(self, btle_device, cmd=bytearray(), payload=bytearray()):
            self.__btle_device = btle_device
            self.cmd = cmd
            self.payload = payload

        @property
        def cmd(self):
            return self.__cmd

        @cmd.setter
        def cmd(self, cmd):
            self.__data = self.MAGIC_START + bytearray(1) + cmd + self.__payload + bytearray(1) + self.MAGIC_END
            self.__cmd = cmd
            self.__calc_length()
            self.__calc_checksum()

        @property
        def payload(self):
            return self.__payload

        @payload.setter
        def payload(self, payload):
            self.__data = self.MAGIC_START + bytearray(1) + self.__cmd + payload + bytearray(1) + self.MAGIC_END
            self.__payload = payload
            self.__calc_length()
            self.__calc_checksum()

        def __calc_checksum(self):
            checksum = 1
            for i in range(2, self.__data[1] + 2):
                checksum += self.__data[i]
            self.__data[-3] = checksum & 0xff

        def __calc_length(self):
            self.__data[1] = 1 + len(self.__payload) + 1 # cmd + payload + checksum

        def send(self):
            if not self.__btle_device.connected:
                self.__btle_device.reconnect()

            self.__btle_device._write_char.write(self.__data, True)
            self.__btle_device._btle_device.waitForNotifications(5)


    class BTLEHandler(btle.DefaultDelegate):
        def __init__(self, btle_device):
            btle.DefaultDelegate.__init__(self)
            self.__btle_device = btle_device

        def handleNotification(self, cHandle, data):
            message_type = data[2]
            if message_type == 0x00:
                if data[4] == 0x01:
                    print("Checksum error!")
                else:
                    print("Unknown error:", data)
            elif message_type == 0x03: #switch toggle
                print("Switch toggled")
                self.__btle_device.getStatus()
            elif message_type == 0x04: #status related data
                self.__btle_device.voltage = data[8]
                self.__btle_device.current = (data[9] << 8 | data[10]) / 1000
                self.__btle_device.power = (data[5] << 16 | data[6] << 8 | data[7]) / 1000
                self.__btle_device.frequency = data[11]
                self.__btle_device.powered = bool(data[4])
            elif message_type == 0x17:
                if data[5] == 0x00 or data[5] == 0x01:
                    if data[4]:
                        print("Login failed")
                else:
                    print("5th byte of login-response is > 1:", data)
            else:
                print ("Unknown message from Handle: 0x" + format(cHandle,'02X') + " Value: "+ format(data))
