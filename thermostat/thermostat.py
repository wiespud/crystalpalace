#!/usr/bin/env python

import gpiozero
import subprocess
import time

def time_print(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    print '%s %s' % (ts, msg)

TEMP_CMD = 'ssh root@Omega-95EF.local cat /sys/devices/w1_bus_master1/28-01143ba557aa/w1_slave'
RETRIES = 5
def get_temp():
    retry = 0
    while True:
        retry += 1
        try:
            output = subprocess.check_output(TEMP_CMD, shell=True)
        except subprocess.CalledProcessError:
            if retry > RETRIES:
                time_print('Error encountered while trying to get temperature')
                raise
            else:
                time.sleep(1)
        else:
            break
    if 'YES' not in output:
        time_print('CRC check failed')
        print output
        return None
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
    temp = temp_c * 9.0 / 5.0 + 32.0
    return temp

SET_TEMP_FILE = '/home/pi/thermostat_set_temp.txt'
def get_set_temp():
    with open(SET_TEMP_FILE) as fin:
        set_temp = fin.read().strip()
    return float(set_temp)

ON_MARGIN = 0.5
OFF_MARGIN = 0.5
SAMPLES = 5
def main(args):

    ac = gpiozero.OutputDevice(4, active_high=False)
    running = False
    samples = [ None for i in range(0, SAMPLES) ]

    while True:
        temp = get_temp()
        samples.pop(0)
        samples.append(temp)
        set_temp = get_set_temp()
        avg_temp = 0.0

        if None not in samples:
            avg_temp = sum(samples) / float(SAMPLES)
            if running:
                if avg_temp <= set_temp - OFF_MARGIN:
                    time_print('turning off AC')
                    ac.off()
                    running = False
            else:
                if avg_temp >= set_temp + ON_MARGIN:
                    time_print('turning on AC')
                    ac.on()
                    running = True

        time_print('temp=%.1f avg=%.1f set=%.1f ac=%s' % (temp, avg_temp, set_temp, running))
        time.sleep(5)

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
