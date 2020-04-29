#!/usr/bin/env python

import gpiozero
import os
import signal
import subprocess
import sys
import time

'''

amixer set Headphone mute
amixer set Headphone unmute
amixer set Headphone 10%

$ mpg123 http://cms.stream.publicradio.org/cms.mp3
High Performance MPEG 1.0/2.0/2.5 Audio Player for Layers 1, 2 and 3
        version 1.25.10; written and copyright by Michael Hipp and others
        free software (LGPL) without any warranty but with best wishes

Directory: http://cms.stream.publicradio.org/

Terminal control enabled, press 'h' for listing of keys and functions.

Playing MPEG stream 1 of 1: cms.mp3 ...
ICY-NAME: Classical Minnesota Public Radio
ICY-URL: http://www.classicalmpr.org/

MPEG 1.0 L III cbr128 44100 j-s

ICY-META: StreamTitle='';StreamUrl='';metadata='adswizzContext=fGg6MV58cDo0OTU2NCN1Ojc4MzY0';adw_ad='true';durationMilliseconds='16300';insertionType='preroll';

ICY-META: StreamTitle='Good Night and Good Rest - John Johnson';StreamUrl='';

'''

pid_file = '/tmp/alarm.pid'
alarm = False
play = False

def handle_signal(signum, stack):
    global alarm
    global play
    if not alarm and not play:
        alarm = True

def handle_button():
    global alarm
    global play
    if alarm or play:
        alarm = False
        play = False
    else:
        play = True

def main(args):
    global pid_file
    global alarm
    global play

    pid = None
    try:
        with open(pid_file, 'r') as fin:
            pid = fin.read()
    except IOError:
        pass

    if 'daemon' in args:
        if pid:
            print 'alarm daemon is already running pid=%s' % pid
            return 1
        else:
            pid = str(os.getpid())
            with open(pid_file, 'w') as fout:
                fout.write(pid)

        # daemon setup
        signal.signal(signal.SIGUSR1, handle_signal)
        button = gpiozero.Button(26)
        button.when_pressed=handle_button
        proc = None
        start = 0.0

        # daemon loop
        try:
            while True:
                if proc:
                    if ((start > 0.0 and (time.time() - start) > 3600) or
                        (not alarm and not play)):
                        proc.terminate()
                        proc = None
                        alarm = False
                        play = False
                else:
                    if alarm:
                        # mute and wait 30 seconds in case the stream starts with an advertisement
                        subprocess.call(["amixer", "set", "Headphone", "mute"])
                        proc = subprocess.Popen(["mpg123", "http://cms.stream.publicradio.org/cms.mp3"])
                        start = time.time()
                        time.sleep(30)
                        subprocess.call(["amixer", "set", "Headphone", "unmute"])
                    elif play:
                        proc = subprocess.Popen(["mpg123", "http://cms.stream.publicradio.org/cms.mp3"])
                        start = 0.0
                time.sleep(1)
        except:
            os.unlink(pid_file)
            return 1

    # alarm called from cron
    else:
        if pid:
            os.kill(int(pid), signal.SIGUSR1)
        else:
            # the daemon is not running so run a standalone alarm instance
            button = gpiozero.Button(26)

            # mute and wait 30 seconds in case the stream starts with an advertisement
            subprocess.call(["amixer", "set", "Headphone", "mute"])
            proc = subprocess.Popen(["mpg123", "http://cms.stream.publicradio.org/cms.mp3"])
            start = time.time()
            time.sleep(30)
            subprocess.call(["amixer", "set", "Headphone", "unmute"])

            # wait 1 hour for button press
            button.wait_for_press(3600)

            # stop stream
            proc.terminate()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
