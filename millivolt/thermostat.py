#!/usr/bin/env python3

# simple thermostat for controlling millivolt gas fireplaces

import datetime
import flask
import gpiozero
import json
import logging
import os
import subprocess
import threading
import traceback
import time

from logging.handlers import RotatingFileHandler

margin = 0.5 # degrees f
sample_count = 3 # number of previous samples to average
poll_rate = 5 # seconds
timeout = 60 # seconds

persistent_state_file = '/var/www/html/state.json'
state_defaults = {
    'status' : 'off',
    'mode' : 'off',
    'set_temp' : 68,
    'cur_temp' : 72,
}
state = {}
off_time = time.time()

logger = None
def setup_logger():
    global logger
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = RotatingFileHandler('/var/log/thermostat/thermostat.log',
                                  maxBytes=1024*1024, backupCount=5)
    handler.setFormatter(formatter)
    logger = logging.getLogger('thermostat')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

def find_temp_sensor():
    address = None
    while True:
        for d in os.listdir('/sys/devices/w1_bus_master1'):
            if d.startswith('28-'):
                address = d
        if address:
            break
        time.sleep(1)
    return address

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

class TempSensor:
    ''' base class for temperature sensors '''
    def __init__(self):
        self.w1_address = find_temp_sensor()
        self.samples = []
        self.last_sample = time.time()
        self.poller = threading.Thread(target=self.poller_func)
        self.poller.daemon = True
        self.poller.start()

    def poller_func(self):
        while True:
            time.sleep(poll_rate)
            try:
                c_temp = get_temp(self.w1_address)
            except IOError:
                continue
            f_temp = c_to_f(c_temp)
            self.add_sample(f_temp)

    def get_last(self):
        return state['sensors'][self.name]

    def get_average(self):
        if len(self.samples) > 0:
            return sum(self.samples) / len(self.samples)
        else:
            return None

    def add_sample(self, sample):
        self.last_sample = time.time()
        self.samples.append(sample)
        if len(self.samples) > sample_count:
            self.samples.pop(0)

def rest_thread_func():
    api = flask.Flask('state')

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    @api.route('/state', methods=['GET'])
    def api_get_state():
        return flask.jsonify(state)

    @api.route('/button', methods=['POST'])
    def api_push_button():
        global off_time
        button = flask.request.get_data().decode("utf-8")
        if button == 'up':
            state['set_temp'] += 1
        elif button == 'down':
            state['set_temp'] -= 1
        elif button == 'off':
            state['mode'] = button
            off_time = time.time()
        elif button == 'plus_one_hour':
            now = time.time()
            if now > off_time:
                off_time = now
            off_time += 3600
            off_time_str = datetime.datetime.fromtimestamp(off_time).strftime('%H:%M')
            state['mode'] = 'Heating until %s' % off_time_str
        else:
            logger.warning('user pressed unknown button: %s' % button)
            return 'fail', 400
        logger.info('user pressed button: %s' % button)
        return 'success', 200

    api.run(host='0.0.0.0')

def main():
    global off_time

    # load persistent settings if available
    global state
    try:
        with open(persistent_state_file) as fin:
            state = json.loads(fin.read())
    except FileNotFoundError:
        logger.warning('%s not found, using defaults' % persistent_state_file)
        state = state_defaults

    # set up temperature sensor
    sensor = TempSensor()

    # start rest api
    rest_thread = threading.Thread(target=rest_thread_func)
    rest_thread.daemon = True
    rest_thread.start()

    # set up control lines
    heat = gpiozero.OutputDevice(24, active_high=False)
    heat.off()

    logger.info('waiting for data to accumulate')
    time.sleep(30)
    logger.info('starting main control loop')
    last_save = time.time()
    while True:
        time.sleep(5)
        now = time.time()

        # check for stale data
        if sensor.last_sample < (now - timeout):
            sensor.samples.clear()
            state['sensors'][name]['temperature'] = None
            logger.warning('%s: stale data' % sensor.name)

        # turn heat off if no temperature data is available
        average = sensor.get_average()
        if average:
            state['cur_temp'] = round(average)
        else:
            if heat.value > 0:
                logger.warning('turning heat off due to lack of data')
                heat.off()
            state['status'] = 'error'
            continue

        # set mode off when time runs out
        if state['mode'] != 'off' and now > off_time:
            logger.info('setting mode off because time expired')
            state['mode'] = 'off'

        # turn heat on/off based on temperature and margin
        if state['mode'] == 'off':
            if heat.value > 0:
                logger.info('turning heat off')
                heat.off()
        else:
            if heat.value > 0 and average > state['set_temp'] + margin:
                logger.info('turning heat off (%.1f F)' % average)
                heat.off()
            elif heat.value < 1 and average < state['set_temp'] - margin:
                logger.info('turning heat on (%.1f F)' % average)
                heat.on()

        # set status
        if heat.value > 0:
            state['status'] = 'heating'
        else:
            state['status'] = 'off'

        # persist the current settings every 5 minutes
        if now > last_save + 300:
            last_save = now
            with open(persistent_state_file, 'w') as fout:
                fout.write(json.dumps(state, indent=4))
                fout.flush()
                os.fsync(fout.fileno())

if __name__ == '__main__':
    setup_logger()
    try:
        main()
    except BaseException as e:
        logger.error(traceback.format_exc())
        raise
