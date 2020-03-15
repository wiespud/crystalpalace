#!/usr/bin/env python3

import fcntl
import gpiozero
import logging
import os
import subprocess
import sys
import time

from logging.handlers import RotatingFileHandler

# Web content files
HALLWAYTEMP_FILE = '/var/www/html/hallwaytemp.txt'
HALLWAYHUM_FILE = '/var/www/html/hallwayhum.txt'
BEDROOMTEMP_FILE = '/var/www/html/bedroomtemp.txt'
NURSERYTEMP_FILE = '/var/www/html/nurserytemp.txt'
BASEMENTTEMP_FILE = '/var/www/html/basementtemp.txt'
CURSTAT_FILE = '/var/www/html/curstat.txt'
SETTEMP_FILE = '/var/www/html/temp.txt'
SETMODE_FILE = '/var/www/html/mode.txt'
SETFAN_FILE = '/var/www/html/fan.txt'

# Button color files
COOL_FILE = '/var/www/html/cool_color.txt'
HEAT_FILE = '/var/www/html/heat_color.txt'
AUTO_FILE = '/var/www/html/auto_color.txt'
ON_FILE = '/var/www/html/on_color.txt'

# Thermostat fine tuning
TEMP_UP_DOWN = { 'Up': 1, 'Down': -1 }
ON_MARGIN = 0.5
OFF_MARGIN = 0.5
SAMPLES = 5

HALLWAY_DATA_FILE = '/dev/rht03'
BEDROOM_CMD = 'ssh root@192.168.0.6 cat /sys/devices/w1_bus_master1/28-01143ba557aa/w1_slave'
NURSERY_CMD = 'ssh pi@192.168.0.7 cat /sys/devices/w1_bus_master1/28-000003c72bff/w1_slave'
BASEMENT_CMD = 'cat /sys/devices/w1_bus_master1/28-000003c73f29/w1_slave'

TEMP_CMD = NURSERY_CMD

logger = None
def setup_logger(name):
    global logger
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = RotatingFileHandler('/var/log/thermostat/%s.log' % name,
                                  maxBytes=1024*1024, backupCount=5)
    handler.setFormatter(formatter)
    logger = logging.getLogger('thermostat %s' % name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

RETRIES = 5
def get_temp(temp_cmd):
    global logger
    retry = 0
    while True:
        retry += 1
        try:
            output = subprocess.check_output(temp_cmd.split(), timeout=10)
        except subprocess.CalledProcessError:
            logger.warning('CalledProcessError while trying to get temperature using command: %s' % temp_cmd)
            if retry > RETRIES:
                return None
            else:
                time.sleep(1)
        except subprocess.TimeoutExpired:
            logger.warning('TimeoutExpired while trying to get temperature using command: %s' % temp_cmd)
            if retry > RETRIES:
                return None
            else:
                time.sleep(1)
        else:
            break
    if b'YES' not in output:
        logger.warning('CRC check failed using command: %s' % temp_cmd)
        return None
    try:
        temp_str = output.split(b't=')[1].strip()
    except IndexError:
        logger.warning('Unexpected format using command: %s' % temp_cmd)
        return None
    try:
        temp_c = float(temp_str) / 1000.0
    except ValueError:
        logger.warning('Invalid temperature %s using command: %s' % temp_str, temp_cmd)
        return None
    temp = c_to_f(temp_c)
    return temp

def get_hallway_data():
    global logger
    try:
        with open(HALLWAY_DATA_FILE) as fin:
            data_str = fin.read()
    except:
        logger.warning('Unable to read from %s' % HALLWAY_DATA_FILE)
        return (None, None)
    try:
        data_str = data_str.strip('\n')
        data = data_str.split(' ')
        h = float(data[0].split('=')[1]) / 10.0
        t = float(data[1].split('=')[1]) / 10.0
        t = c_to_f(t)
        return (t, h)
    except:
        logger.warning('Unable to parse %s' % data_str)
        return (None, None)
    return (None, None)

def read_file(filename):
    with open(filename) as fin:
        fcntl.flock(fin, fcntl.LOCK_EX)
        contents = fin.read()
        fcntl.flock(fin, fcntl.LOCK_UN)
        return contents

def write_file(filename, contents):
    with open(filename, 'w+') as fout:
        fcntl.flock(fout, fcntl.LOCK_EX)
        fout.write(contents)
        fout.flush()
        os.fsync(fout.fileno())
        fcntl.flock(fout, fcntl.LOCK_UN)

def main(args):
    global logger

    # web page php calls
    if len(sys.argv) > 1:
        setup_logger('web')
        if len(sys.argv) < 3:
            logger.error('Missing argument')
            return 1
        cmd = sys.argv[1]
        arg = sys.argv[2]
        if cmd == 'temp':
            if arg  in [ 'Up', 'Down' ]:
                settemp = int(read_file(SETTEMP_FILE))
                settemp += TEMP_UP_DOWN[arg]
                write_file(SETTEMP_FILE, str(settemp))
            else:
                logger.error('Invalid argument %s for command %s' % (arg, cmd))
                return 1
        elif cmd == 'mode':
            if arg in [ 'Cool', 'Heat', 'Off' ]:
                write_file(SETMODE_FILE, arg)
                if arg == 'Cool':
                    write_file(COOL_FILE, 'aqua')
                    write_file(HEAT_FILE, 'silver')
                elif arg == 'Heat':
                    write_file(COOL_FILE, 'silver')
                    write_file(HEAT_FILE, 'orange')
                elif arg == 'Off':
                    write_file(COOL_FILE, 'silver')
                    write_file(HEAT_FILE, 'silver')
            else:
                logger.error('Invalid argument %s for command %s' % (arg, cmd))
                return 1
        elif cmd == 'fan':
            if arg in [ 'Auto', 'On' ]:
                write_file(SETFAN_FILE, arg)
                if arg == 'Auto':
                    write_file(AUTO_FILE, 'lime')
                    write_file(ON_FILE, 'silver')
                elif arg == 'On':
                    write_file(AUTO_FILE, 'silver')
                    write_file(ON_FILE, 'lime')
            else:
                logger.error('Invalid argument %s for command %s' % (arg, cmd))
                return 1
        else:
            logger.error('Invalid command %s' % cmd)
            return 1
        time.sleep(0.5)
        return 0

    # else start daemon loop
    setup_logger('daemon')

    heat = gpiozero.OutputDevice(22, active_high=False)
    #~ fan = gpiozero.OutputDevice(23, active_high=False)
    #~ ac = gpiozero.OutputDevice(24, active_high=False)

    running = False
    samples = [ None for i in range(0, SAMPLES) ]
    warmup_samples = SAMPLES

    while True:
        temp = get_temp(TEMP_CMD)
        samples.pop(0)
        samples.append(temp)
        set_temp = float(read_file(SETTEMP_FILE))
        avg_temp = 0.0

        if temp is not None and warmup_samples > 0:
            warmup_samples -= 1

        eligible_samples = [ i for i in samples if i is not None ]
        if warmup_samples <= 0:
            if len(eligible_samples) > 0:
                avg_temp = sum(eligible_samples) / float(len(eligible_samples))
                if running:
                    if avg_temp >= set_temp + OFF_MARGIN:
                        logger.info('turning off heat')
                        heat.off()
                        running = False
                        write_file(CURSTAT_FILE, 'Off')
                else:
                    if avg_temp <= set_temp - ON_MARGIN:
                        logger.info('turning on heat')
                        heat.on()
                        running = True
                        write_file(CURSTAT_FILE, 'Running')
            else:
                if running:
                    logger.info('turning off heat due to lack of temperature data')
                    heat.off()
                    running = False
                    write_file(CURSTAT_FILE, 'Error')

        sleep_time = 5
        if temp is None:
            temp = 'Error'
            nursery_temp = 'Error'
        else:
            sleep_time = 1

            #~ (hallway_temp, hallway_hum) = get_hallway_data()
            #~ if hallway_temp is None or hallway_hum is None:
                #~ hallway_temp = 'Error'
                #~ hallway_hum = 'Error'
            #~ else:
                #~ hallway_temp = '%.1f F' % hallway_temp
                #~ hallway_hum = '%.1f%%' % hallway_hum
            #~ write_file(HALLWAYTEMP_FILE, hallway_temp)
            #~ write_file(HALLWAYHUM_FILE, hallway_hum)

            bedroom_temp = get_temp(BEDROOM_CMD)
            if bedroom_temp is None:
                bedroom_temp = 'Error'
            else:
                bedroom_temp = '%.1f F' % bedroom_temp
            write_file(BEDROOMTEMP_FILE, bedroom_temp)

            #~ nursery_temp = get_temp(NURSERY_CMD)
            #~ if nursery_temp is None:
                #~ nursery_temp = 'Error'
            #~ else:
                #~ nursery_temp = '%.1f F' % nursery_temp
            #~ write_file(NURSERYTEMP_FILE, bedroom_temp)

            basement_temp = get_temp(BASEMENT_CMD)
            if basement_temp is None:
                basement_temp = 'Error'
            else:
                basement_temp = '%.1f F' % basement_temp
            write_file(BASEMENTTEMP_FILE, basement_temp)

            # Nursery here
            temp = '%.1f' % temp
            nursery_temp = '%s F' % temp
        write_file(NURSERYTEMP_FILE, nursery_temp)
            
        logger.info('temp=%s avg=%.1f set=%.1f heat=%s' % (temp, avg_temp, set_temp, running))
        time.sleep(sleep_time)

    return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
