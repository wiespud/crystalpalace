#!/usr/bin/env python

import os
import subprocess
import sys
import time

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

def time_print(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print '%s %s' % (ts, msg)

RETRIES = 5
def get_val(cmd):

    retry = 0
    while True:
        retry += 1
        try:
            output = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            if retry > RETRIES:
                time_print('Error encountered while trying to get temperature')
                raise
            else:
                time.sleep(1)
        else:
            break

    if 'w1_bus_master' in cmd and 'YES' not in output:
        time_print('CRC check failed')
        print output
        return None

    if 'w1_bus_master' in cmd:
        try:
            temp_str = output.split('t=')[1].strip()
        except IndexError:
            time_print('Unexpected format')
            print output
            return None
        try:
            temp_c = float(temp_str) / 1000.0
        except ValueError:
            time_print('Invalid temperature %s' % temp_str)
            print output
            return None
        val = temp_c * 9.0 / 5.0 + 32.0
    else:
        val = float(output.strip()) / 1000.0
        if 'temp' in cmd:
            val = val * 9.0 / 5.0 + 32.0

    return val

def main(args):

    series = {}
    series['timestamps'] = []
    roomsdir = '%s/rooms' % sys.path[0]
    rooms = os.listdir(roomsdir)
    for room in rooms:
        room_str = room.split('.')[0]
        series[room_str] = []
    prev_minute = int(time.time()) / 60

    while True:

        # Update plot once a minute
        while True:
            ts = time.time()
            ts_str = time.strftime('%H:%M')
            minute = int(ts) / 60
            if minute > prev_minute:
                break
            else:
                time.sleep(0.5)
        prev_minute = minute

        if len(series['timestamps']) > 1440:
            series['timestamps'].pop(0)
        series['timestamps'].append(ts_str)
        for room in rooms:
            room_str = room.split('.')[0]
            if len(series[room_str]) > 1440:
                series[room_str].pop(0)
            cmd_file = '%s/%s' % (roomsdir, room)
            with open(cmd_file) as fin:
                cmd = fin.read().strip()
            val = get_val(cmd)
            series[room_str].append(val)
            plt.plot(range(len(series[room_str])), series[room_str], label=room_str)

        plt.xticks(range(len(series['timestamps'])), series['timestamps'], rotation=90)
        plt.legend()
        plt.savefig('/var/www/html/thermostat.png', dpi=300)
        plt.clf()

    return 1

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
