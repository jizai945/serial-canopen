import types

import canopen
import time
import serial
import struct
from can import Message

def listen_cb(msg):
    print(f'lcb: {msg}')

def my_serial_send(self, msg, timeout=None):
    '''Reconstruction sending method'''

    print('my_serial_send')
    try:
        a_id = struct.pack('<I', msg.arbitration_id)
    except struct.error:
        raise ValueError('Arbitration Id is out of range')
    send_array = bytearray([0x57, 0x58])                            # USB数据头
    send_array += bytearray(a_id[2:4])                              # can id
    send_array += bytearray(msg.data[:msg.dlc])                     # can数据
    send_array += bytearray([0 for _ in range(8 - msg.dlc)])        # 补零
    send_array += bytearray([msg.dlc])                              # 实际数据长度
    send_array += bytearray([0xA8, 0XA7])                           # USB数据尾
    self.ser.write(bytearray(send_array))                           # 发送


def my_recv_internal(self, timeout):
    '''Reconstruction receiving method'''

    try:
        # ser.read can return an empty string
        # or raise a SerialException
        rx_byte = self.ser.read()
    except serial.SerialException:
        return None, False

    try:
        if rx_byte and ord(rx_byte) == 0x57:
            rx_byte = self.ser.read()
            if not (rx_byte and ord(rx_byte) == 0x58):
                print('333')
                return None, False
            s = bytearray([0, 0, 0, 0])
            t = bytearray(self.ser.read(2))
            s[1], s[0] = t[0], t[1]
            arb_id = (struct.unpack('<I', s))[0]

            data = self.ser.read(8)
            dlc = ord(self.ser.read())
            rxd_byte = self.ser.read(2)
            timestamp = 0
            if rxd_byte and rxd_byte[0] == 0xA8 and rxd_byte[1] == 0xA7:
                # received message data okay
                msg = Message(timestamp=timestamp / 1000,
                              arbitration_id=arb_id,
                              dlc=8,
                              data=data)
                return msg, False

        else:
            return None, False
    except:
        return None, False


# Start with creating a network representing one CAN bus
network = canopen.Network()

# Add some nodes with corresponding Object Dictionaries
node = canopen.RemoteNode(6, './CANopenSocket.eds')
network.add_node(node)
node2 = canopen.RemoteNode(7, './e35.eds')
network.add_node(node2)

# Add some nodes with corresponding Object Dictionaries
network.connect(bustype="serial",  channel='COM6')
network.bus.send = types.MethodType(my_serial_send, network.bus)  # 重构发送方法
network.bus._recv_internal = types.MethodType(my_recv_internal, network.bus)  # 重构接收方法

network.listeners.append(listen_cb)                 # 添加一个监听回调函数

# send test message
network.send_message(0x06, bytes([0x11, 0x22]))

print('-'*30)
time.sleep(0.5)

network.sync.stop()
network.disconnect()

