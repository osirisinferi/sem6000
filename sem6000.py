from bluepy import btle
import time
import datetime
import uuid

class SEMSocket():
    password = "0000"
    powered = False
    voltage = 0
    current = 0
    power = 0
    power_factor = 0
    total_power = 0
    frequency = 0
    mac_address = ""
    custom_service = None
    authenticated = False
    _name = None
    _read_char = None
    _write_char = None
    _notify_char = None
    _name_char = None
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
        return msg.send()

    def setStatus(self, status):
        # 0f 06 03 00 01 00 00 05 ff ff  -> on
        # 0f 06 03 00 00 00 00 04 ff ff  -> off
        cmd = bytearray([0x03])
        payload = bytearray([0x00, status, 0x00, 0x00])
        msg = self.BTLEMessage(self, cmd, payload)
        return msg.send()

    def syncTime(self):
        #15, 12, 1, 0, SECOND, MINUTE, HOUR_OF_DAY, DAY_OF_MONTH, MONTH (+1), int(YEAR/256), YEAR%256, 0, 0, CHKSUM, 255, 255
        now = datetime.datetime.now()
        cmd = bytearray([0x01])
        payload = bytearray([0x00])
        payload += bytearray([now.second, now.minute, now.hour])
        payload += bytearray([now.day, now.month, int(now.year/256), now.year%256])
        payload += bytearray([0x00, 0x00])
        msg = self.BTLEMessage(self, cmd, payload)
        return msg.send()

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
        success = msg.send()
        self.authenticated = self.authenticated and success
        return success

    def changePassword(self, newPassword):
        cmd = bytearray([0x17])
        payload = bytearray()
        payload.append(0x00)
        payload.append(0x01)
        for i in range(4):
            payload.append(int(newPassword[i]))
        for i in range(4):
            payload.append(int(self.password[i]))
        self.password = newPassword
        msg = self.BTLEMessage(self, cmd, payload)
        success = msg.send()
        self.authenticated = self.authenticated and success
        return success

    @property
    def name(self):
        self._name = self._name_char.read().decode("UTF-8")
        return self._name

    @name.setter
    def name(self, newName):
        newName = newName.encode("UTF-8")
        cmd = bytearray([0x02])
        payload = bytearray()
        payload.append(0x02)
        for i in range(20):
            if i <= (len(newName) - 1):
                payload.append(newName[i])
            else:
                payload.append(0x00)
        msg = self.BTLEMessage(self, cmd, payload)
        success = msg.send()
        # For some reason the original app sets the first 7 bytes of the payload to zero and sends it again.
        # However, a first test showed, that this really doesn't change anything. If it becomes neccessary here's a first draft:
        #for i in range(7):
        #    payload[i+1] = 0x00
        #msg = self.BTLEMessage(self, cmd, payload)
        if not success: raise self.SendMessageFailed

    @property
    def connected(self):
        try:
            return "conn" in self._btle_device.status().get("state")
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
        self._name_char      = self._custom_service.getCharacteristics("0000fff6-0000-1000-8000-00805f9b34fb")[0]

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

    class SendMessageFailed(Exception):
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
            return self.__btle_device._btle_device.waitForNotifications(5)


    class BTLEHandler(btle.DefaultDelegate):
        def __init__(self, btle_device):
            btle.DefaultDelegate.__init__(self)
            self.__btle_device = btle_device

        def handleNotification(self, cHandle, data):
            if len(data) <= 3:
                print("Notification data seems invalid or incomplete. Could not parse: ", end="")
                print(data)
                return

            message_type = data[2]
            if message_type == 0x00:
                if data[4] == 0x01:
                    print("Checksum error!")
                else:
                    print("Unknown error:", data)
            elif message_type == 0x01: #sync time response
                if not data[3:] == b'\x00\x00\x02\xff\xff':
                    print("Time synced failed with unknown data: ", end="")
                    print(data)
            elif message_type == 0x02: #set name response
                if not data[3:] == b'\x00\x00\x03\xff\xff':
                    print("Set name failed with unknown data: ", end="")
                    print(data)
            elif message_type == 0x03: #switch toggle response
                self.__btle_device.getStatus()
            elif message_type == 0x04: #status related response
                voltage     = data[8]
                current     = (data[9] << 8 | data[10]) / 1000
                power       = (data[5] << 16 | data[6] << 8 | data[7]) / 1000
                total_power = (data[14] << 24 | data[15] << 16 | data[16] << 8 | data[17]) / 1000

                self.__btle_device.voltage = voltage
                self.__btle_device.current = current
                self.__btle_device.power   = power
                self.__btle_device.frequency = data[11]
                self.__btle_device.powered = bool(data[4])
                self.__btle_device.total_power = total_power

                # calculated values
                try:
                    self.__btle_device.power_factor = power / (voltage * current)
                except ZeroDivisionError:
                    self.__btle_device.power_factor = None
            elif message_type == 0x17: #authentication related response
                if data[5] == 0x00 or data[5] == 0x01:
                    # in theory the fifth byte indicates a login attempt response (0) or a response to a password change (1)
                    # but since a password change requires a valid login and a successful password changes logs you in,
                    # we can just ignore this bit and set the authenticated flag accordingly for both responses
                    self.__btle_device.authenticated = not data[4]
                else:
                    print("5th byte of login-response is > 1:", data)
            elif message_type == 0x0f: #set icon response
                if not data[3:] == b'\x00\x03\x00\x13\xff\xff':
                    print("Unknown response for setting icon: ", end="")
                    print(data[3:])
            else:
                print ("Unknown message from Handle: 0x" + format(cHandle,'02X') + " Value: "+ format(data))

