#!/usr/bin/env python3

import datetime
import fcntl
import gpiozero
import logging
import os
import subprocess
import sys
import time

from logging.handlers import RotatingFileHandler

# Web content files
WEB_PREFIX = '/var/www/html/thermostat_files/'
AVERAGE_FILE = WEB_PREFIX + 'averagetemp.txt'
CURSTAT_FILE = WEB_PREFIX + 'curstat.txt'
SETTEMP_FILE = WEB_PREFIX + 'temp.txt'
SETMODE_FILE = WEB_PREFIX + 'mode.txt'
SETFAN_FILE = WEB_PREFIX + 'fan.txt'
COOL_FILE = WEB_PREFIX + 'cool_color.txt'
HEAT_FILE = WEB_PREFIX + 'heat_color.txt'
AUTO_FILE = WEB_PREFIX + 'auto_color.txt'
ON_FILE = WEB_PREFIX + 'on_color.txt'
HOUR_DC_FILE = WEB_PREFIX + 'hourdutycycle.txt'
DAY_DC_FILE = WEB_PREFIX + 'daydutycycle.txt'
LAST_UPDATE_FILE = WEB_PREFIX + 'lastupdate.txt'

# Thermostat fine tuning
TEMP_UP_DOWN = { 'Up': 1, 'Down': -1 }
MARGIN = 0.5
SAMPLES = 5
HOLD_TIME = 300.0 # seconds to force off after running continuously for one hour

ROOMS = {
    'basement' : {
        'cmd'  : 'cat /sys/devices/w1_bus_master1/28-000003c73f29/w1_slave',
        'file' : WEB_PREFIX + 'basementtemp.txt',
    },
    'bedroom' : {
        'cmd'  : 'ssh pi@bedroom.local cat /sys/devices/w1_bus_master1/28-01143bc12daa/w1_slave',
        'file' : WEB_PREFIX + 'bedroomtemp.txt',
        'data' : [ None for i in range(0, SAMPLES) ],
    },
    'closet' : {
        'cmd'  : 'ssh pi@pihole.local cat /sys/devices/w1_bus_master1/28-01143b8f3caa/w1_slave',
        'file' : WEB_PREFIX + 'closettemp.txt',
    },
    'familyroom' : {
        'cmd'  : 'ssh root@192.168.0.6 cat /sys/devices/w1_bus_master1/28-01143ba557aa/w1_slave',
        'file' : WEB_PREFIX + 'familyroomtemp.txt',
        'data' : [ None for i in range(0, SAMPLES) ],
    },
    'nursery' : {
        'cmd'  : 'ssh pi@nursery.local cat /sys/devices/w1_bus_master1/28-000003c72bff/w1_slave',
        'file' : WEB_PREFIX + 'nurserytemp.txt',
        'data' : [ None for i in range(0, SAMPLES) ],
    }
}

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

def get_temp(temp_cmd):
    global logger

    try:
        output = subprocess.check_output(temp_cmd.split(), timeout=10)
    except subprocess.CalledProcessError:
        logger.warning('CalledProcessError while trying to get temperature using command: %s' % temp_cmd)
        return None
    except subprocess.TimeoutExpired:
        logger.warning('TimeoutExpired while trying to get temperature using command: %s' % temp_cmd)
        return None
    except ValueError:
        logger.warning('ValueError while trying to get temperature using command: %s' % temp_cmd)
        return None

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
    fan = gpiozero.OutputDevice(23, active_high=False)
    ac = gpiozero.OutputDevice(24, active_high=False)

    duty_cycle_times = []
    duty_cycle_values = []
    hold_end = 0.0
    while True:
        samples = []
        avg_temp = 0.0
        error_flag = False

        # get temperatures
        for room in ROOMS:
            temp = get_temp(ROOMS[room]['cmd'])
            if 'data' in ROOMS[room]:
                ROOMS[room]['data'].pop(0)
                ROOMS[room]['data'].append(temp)
                samples += ROOMS[room]['data']
            if temp is None:
                temp = 'Error'
            else:
                temp = '%.1f F' % temp
            write_file(ROOMS[room]['file'], temp)

        # get settings and status from web page
        set_temp = float(read_file(SETTEMP_FILE))
        set_mode = read_file(SETMODE_FILE)
        set_fan = read_file(SETFAN_FILE)
        cur_stat = read_file(CURSTAT_FILE)

        # handle fan
        if fan.value > 0:
            if set_fan == 'Auto':
                logger.info('turning off fan')
                fan.off()
        else:
            if set_fan == 'On':
                logger.info('turning on fan')
                fan.on()

        ts = time.time()

        # handle heat and ac
        eligible_samples = [ i for i in samples if i is not None ]
        if len(eligible_samples) < len(samples) / 2:
            if heat.value > 0:
                logger.warning('turning off heat due to lack of data')
                heat.off()
            if ac.value > 0:
                logger.warning('turning off ac due to lack of data')
                ac.off()
            error_flag = True
        else:
            avg_temp = sum(eligible_samples) / float(len(eligible_samples))
            if set_mode == 'Heat':
                if ac.value > 0:
                    logger.info('turning off ac')
                    ac.off()
                if heat.value > 0:
                    if hold_end > ts:
                        logger.info('turning off heat due to overuse')
                        heat.off()
                    elif avg_temp >= set_temp + MARGIN:
                        logger.info('turning off heat')
                        heat.off()
                else:
                    if avg_temp <= set_temp - MARGIN and ts > hold_end:
                        logger.info('turning on heat')
                        heat.on()
            elif set_mode == 'Cool':
                if heat.value > 0:
                    logger.info('turning off heat')
                    heat.off()
                if ac.value > 0:
                    if hold_end > ts:
                        logger.info('turning off ac due to overuse')
                        ac.off()
                    elif avg_temp <= set_temp - MARGIN:
                        logger.info('turning off ac')
                        ac.off()
                else:
                    if avg_temp >= set_temp + MARGIN and ts > hold_end:
                        logger.info('turning on ac')
                        ac.on()

        # set status
        new_stat = 'Off'
        if error_flag:
            new_stat = 'Error'
        elif hold_end > ts:
            new_stat = 'Hold'
        elif heat.value > 0:
            new_stat = 'Heating'
        elif ac.value > 0:
            new_stat = 'Cooling'
        elif fan.value > 0:
            new_stat = 'Fan'
        if cur_stat != new_stat:
            write_file(CURSTAT_FILE, new_stat)
        write_file(AVERAGE_FILE, '%.1f F' % avg_temp)

        # duty cycle
        duty_cycle_times.append(ts)
        if new_stat in ('Heating', 'Cooling'):
            duty_cycle_values.append(1)
        else:
            duty_cycle_values.append(0)
        while duty_cycle_times[0] < (ts - 24*60*60):
            duty_cycle_times.pop(0)
            duty_cycle_values.pop(0)
        hour_times = [ i for i in duty_cycle_times if i > (ts - 60*60) ]
        hour_values = duty_cycle_values[-len(hour_times):]
        hour_duty_cycle = 100.0 * float(sum(hour_values)) / float(len(hour_values))
        day_duty_cycle = 100.0 * float(sum(duty_cycle_values)) / float(len(duty_cycle_values))
        write_file(HOUR_DC_FILE, '%.0f%%' % hour_duty_cycle)
        write_file(DAY_DC_FILE, '%.0f%%' % day_duty_cycle)

        # if it has been running for an hour straight, let it rest for a bit
        if hour_duty_cycle > 99.9:
            hold_end = ts + HOLD_TIME

        write_file(LAST_UPDATE_FILE, '%s' % datetime.datetime.now())
        logger.info('avg=%.1f set=%.1f mode=%s status=%s' % (avg_temp, set_temp, set_mode, new_stat))

    return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
