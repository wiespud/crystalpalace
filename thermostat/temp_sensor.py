#!/usr/bin/env python3

import os
import socket
import time
import zmq

def get_temp(address):
    reading_valid = False
    temperature = 0.0
    with open('/sys/bus/w1/devices/%s/w1_slave' % address) as fin:
        for line in fin:
            if 'YES' in line:
                reading_valid = True
            if 't=' in line:
                t = line.split('t=')[1].strip()
                temperature = float(t) / 1000
    if reading_valid:
        return temperature
    raise IOError # failed open for no such file also raises IOError

def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

if __name__ == '__main__':

    location = socket.gethostname()

    # find the temp sensor address
    # example: /sys/devices/w1_bus_master1/28-000003c73f29/w1_slave
    #                                      ^^^^^^^^^^^^^^^
    address = None
    while True:
        for d in os.listdir('/sys/devices/w1_bus_master1'):
            if d.startswith('28-'):
                address = d
        if address:
            break
        time.sleep(1)
    print('found temp sensor %s' % address)

    # set up the zmq publisher
    zmq_ctx = zmq.Context()
    pub_sock = zmq_ctx.socket(zmq.PUB)
    pub_sock.bind('tcp://*:5555')

    # poll the sensor
    while True:
        try:
            c_temp = get_temp(address)
        except IOError:
            time.sleep(1)
            continue
        f_temp = c_to_f(c_temp)
        pub_sock.send_string('temperature %s %f' % (location, f_temp))
        time.sleep(5)
