#!/usr/bin/env python3

import flask
import gpiozero
import json
import logging
import os
import subprocess
import threading
import traceback
import time
import zmq

from logging.handlers import RotatingFileHandler

margin = 0.5 # degrees f
sample_count = 3 # number of previous samples to average
poll_rate = 5 # seconds
timeout = 60 # seconds

persistent_state_file = '/var/www/html/thermostat/state.json'
state_defaults = {
    'status' : 'off',
    'mode' : 'heat',
    'fan' : 'auto',
    'set_temp' : 68,
    'cur_temp' : 72,
    'duty_cycle' : 0,
    'current_run_time' : 0,
    'last_run_time' : 0,
    'sensors' : {},
}
state = {}
sensors = {}

zmq_ctx = zmq.Context()
sub_sock = zmq_ctx.socket(zmq.SUB)
sub_sock.setsockopt_string(zmq.SUBSCRIBE, 'temperature')

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

def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0

class TempSensor:
    ''' base class for temperature sensors '''
    def __init__(self, name):
        if name not in state['sensors']:
            state['sensors'][name] = { 'temperature' : None, 'use_for_control' : True }
        self.name = name
        self.use_for_control = state['sensors'][name]['use_for_control']
        self.samples = []
        self.last_sample = time.time()
        self.poller = threading.Thread(target=self.poller_func)
        self.poller.daemon = True
        self.poller.start()
        logger.info('added %s sensor' % name)

    def poller_func(self):
        while true:
            time.sleep(poll_rate)

    def get_last(self):
        return state['sensors'][self.name]

    def get_average(self):
        if len(self.samples) > 0:
            return sum(self.samples) / len(self.samples)
        else:
            return None

    def add_sample(self, sample):
        state['sensors'][self.name]['temperature'] = round(sample)
        self.last_sample = time.time()
        self.samples.append(sample)
        if len(self.samples) > sample_count:
            self.samples.pop(0)

class ZMQTempSensor(TempSensor):
    ''' remote temp sensor reporting through zmq socket '''
    def __init__(self, name):
        TempSensor.__init__(self, name)
        sub_sock.connect('tcp://%s.local:5555' % name)

    def poller_func(self):
        while True:
            time.sleep(poll_rate)
            if time.time() > self.last_sample + (timeout / 2):
                logger.warning('%s: reconnecting' % self.name)
                sub_sock.disconnect('tcp://%s.local:5555' % self.name)
                sub_sock.connect('tcp://%s.local:5555' % self.name)

class CmdTempSensor(TempSensor):
    ''' temp sensor accessible through shell command '''
    def __init__(self, name, cmd):
        TempSensor.__init__(self, name)
        self.cmd = cmd

    def poller_func(self):
        while True:
            time.sleep(poll_rate)

            try:
                output = subprocess.check_output(self.cmd.split(), timeout=10)
            except subprocess.CalledProcessError:
                logger.warning('%s: CalledProcessError using command: %s' % (self.name, self.cmd))
                continue
            except subprocess.TimeoutExpired:
                logger.warning('%s: TimeoutExpired using command: %s' % (self.name, self.cmd))
                continue
            except ValueError:
                logger.warning('%s: ValueError using command: %s' % (self.name, self.cmd))
                continue

            if b'YES' not in output:
                logger.warning('%s: CRC check failed using command: %s' % (self.name, self.cmd))
                continue

            try:
                temp_str = output.split(b't=')[1].strip()
            except IndexError:
                logger.warning('%s: Unexpected format using command: %s' % (self.name, self.cmd))
                continue

            try:
                temp_c = float(temp_str) / 1000.0
            except ValueError:
                logger.warning('%s: Invalid temperature "%s" using command: %s' % (self.name, temp_str, self.cmd))
                continue

            temp_f = c_to_f(temp_c)
            self.add_sample(temp_f)

def sub_thread_func():
    while True:
        string = sub_sock.recv_string()
        topic, name, value = string.split()
        if topic != 'temperature':
            logger.warning('unexpected zmq topic %s' % topic)
            continue
        if name not in sensors:
            logger.warning('unexpected zmq sensor %s' % name)
            continue
        try:
            temp_f = float(value)
        except ValueError:
            logger.warning('%s: Invalid temperature "%s" returned through zmq' % (name, value))
            continue
        sensors[name].add_sample(temp_f)

def rest_thread_func():
    api = flask.Flask('state')

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    @api.route('/state', methods=['GET'])
    def api_get_state():
        return flask.jsonify(state)

    @api.route('/button', methods=['POST'])
    def api_push_button():
        button = flask.request.get_data().decode("utf-8")
        if button == 'up':
            state['set_temp'] += 1
        elif button == 'down':
            state['set_temp'] -= 1
        elif button == 'auto' or button == 'on':
            state['fan'] = button
        elif button == 'cool' or button == 'heat' or button == 'off':
            state['mode'] = button
        elif button in sensors:
            sensor = sensors[button]
            cur_val = sensors[button].use_for_control
            sensors[button].use_for_control = not cur_val
            state['sensors'][button]['use_for_control'] = not cur_val
        else:
            logger.warning('user pressed unknown button: %s' % button)
            return 'fail', 400
        logger.info('user pressed button: %s' % button)
        return 'success', 200

    api.run(host='0.0.0.0', port=5002)

def main():
    # load persistent settings if available
    global state
    try:
        with open(persistent_state_file) as fin:
            state = json.loads(fin.read())
    except FileNotFoundError:
        logger.warning('%s not found, using defaults' % persistent_state_file)
        state = state_defaults

    # initialize sensors
    sensors['basement'] = CmdTempSensor('basement', 'cat /sys/devices/w1_bus_master1/28-000003c73f29/w1_slave')
    sensors['familyroom'] = CmdTempSensor('familyroom', 'ssh root@familyroom.local cat /sys/devices/w1_bus_master1/28-01143ba557aa/w1_slave')
    sensors['bedroom'] = ZMQTempSensor('bedroom')
    sensors['apollo'] = ZMQTempSensor('apollo')
    sensors['nursery'] = ZMQTempSensor('nursery')

    # start zmq subscriber thread
    sub_thread = threading.Thread(target=sub_thread_func)
    sub_thread.daemon = True
    sub_thread.start()

    # start rest api
    rest_thread = threading.Thread(target=rest_thread_func)
    rest_thread.daemon = True
    rest_thread.start()

    # set up control lines
    heat = gpiozero.OutputDevice(22, active_high=False)
    fan = gpiozero.OutputDevice(23, active_high=False)
    ac = gpiozero.OutputDevice(24, active_high=False)

    logger.info('waiting for data to accumulate')
    time.sleep(30)
    logger.info('starting main control loop')
    duty_cycle_times = []
    duty_cycle_values = []
    run_time_start = None
    last_save = time.time()
    while True:
        time.sleep(5)
        now = time.time()

        # check for stale data
        for name in sensors:
            sensor = sensors[name]
            if sensor.last_sample < (now - timeout):
                sensor.samples.clear()
                state['sensors'][name]['temperature'] = None
                logger.warning('%s: stale data' % sensor.name)

        # get average temperatures from sensors
        averages = []
        for name in sensors:
            sensor = sensors[name]
            if sensor.use_for_control:
                sensor_average = sensor.get_average()
                if sensor_average:
                    averages.append(sensor_average)

        # turn heat/ac off if no temperature data is available
        if len(averages) == 0:
            if heat.value > 0:
                logger.warning('turning heat off due to lack of data')
                heat.off()
            if ac.value > 0:
                logger.warning('turning ac off due to lack of data')
                ac.off()
            state['status'] = 'error'
            continue

        # compute house average temperature
        house_average = sum(averages) / len(averages)
        state['cur_temp'] = round(house_average)

        # turn heat/ac on/off based on temperature and margin
        if state['mode'] == 'heat':
            if ac.value > 0:
                logger.info('turning ac off')
                ac.off()
            if heat.value > 0 and house_average > state['set_temp'] + margin:
                logger.info('turning heat off (%.1f F)' % house_average)
                heat.off()
            elif heat.value < 1 and house_average < state['set_temp'] - margin:
                logger.info('turning heat on (%.1f F)' % house_average)
                heat.on()
        elif state['mode'] == 'cool':
            if heat.value > 0:
                logger.info('turning heat off')
                heat.off()
            if ac.value > 0 and house_average < state['set_temp'] - margin:
                logger.info('turning ac off (%.1f F)' % house_average)
                ac.off()
            elif ac.value < 1 and house_average > state['set_temp'] + margin:
                logger.info('turning ac on (%.1f F)' % house_average)
                ac.on()
        else: # mode == off
            if heat.value > 0:
                logger.info('turning heat off')
                heat.off()
            if ac.value > 0:
                logger.info('turning ac off')
                ac.off()

        # handle fan
        if fan.value > 0 and state['fan'] == 'auto':
            logger.info('turning fan off')
            fan.off()
        elif fan.value < 1 and state['fan'] == 'on':
            logger.info('turning fan on')
            fan.on()

        # set status
        if heat.value > 0:
            state['status'] = 'heating'
        elif ac.value > 0:
            state['status'] = 'cooling'
        elif fan.value > 0:
            state['status'] = 'fan'
        else:
            state['status'] = 'off'

        # calculate duty cycle and run times
        duty_cycle_times.append(now)
        if state['status'] in ('heating', 'cooling'):
            duty_cycle_values.append(1)
            if run_time_start:
                state['current_run_time'] = round((now - run_time_start) / 60.0)
            else:
                run_time_start = now
        else:
            duty_cycle_values.append(0)
            if run_time_start:
                run_time_start = None
                state['last_run_time'] = state['current_run_time']
                state['current_run_time'] = 0
        while duty_cycle_times[0] < (now - 24*60*60):
            duty_cycle_times.pop(0)
            duty_cycle_values.pop(0)
        state['duty_cycle'] = round(100.0 * float(sum(duty_cycle_values)) / float(len(duty_cycle_values)))

        # persist the current settings every 5 minutes
        if now > last_save + 300:
            last_save = now
            with open(persistent_state_file, 'w+') as fout:
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
