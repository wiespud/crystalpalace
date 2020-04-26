#!/usr/bin/env python

import gpiozero
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

def main(args):

    # set up button to turn off alarm
    button = gpiozero.Button(26)

    # mute and wait 30 seconds in case the stream starts with an advertisement
    subprocess.call(["amixer", "set", "Headphone", "mute"])
    proc = subprocess.Popen(["mpg123", "http://cms.stream.publicradio.org/cms.mp3"])
    time.sleep(30)
    subprocess.call(["amixer", "set", "Headphone", "unmute"])

    # wait 1 hour for button press
    button.wait_for_press(3600)

    # stop stream
    proc.terminate()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
