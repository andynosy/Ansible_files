#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import json
import mytools
import netmiko
import os
import signal
import sys

signal.signal(signal.SIGPIPE, signal.SIG_DFL)  # IOError: Broken pipe
signal.signal(signal.SIGINT, signal.SIG_DFL)  # KeyboardInterrupt: Ctrl-C


def get_config_from_cdp_neighbors(input_string):
    lines = input_string.splitlines()[5:]
    hostname = None
    config = []
    for line in lines:
        words = line.split()
        if len(words) == 1:
            hostname = words[0].split('.')[0]
        else:
            if hostname is None:
                hostname = words.pop(0).split('.')[0]
            local = ''.join(words[0:2])
            description = 'UPLINK to'+ hostname
            config.append('interface ' + local)
            config.append(' description ' + description)
            config.append('!')  # totally optional
            hostname = None
    return config


if len(sys.argv) < 2:
    print('Usage:', os.path.split(sys.argv[0])[-1], 'devices.json')
    exit()

change_number = mytools.get_input('Please enter and approved change number: ')

netmiko_exceptions = (netmiko.ssh_exception.NetMikoTimeoutException,
                      netmiko.ssh_exception.NetMikoAuthenticationException)

username, password = mytools.get_credentials()

with open(sys.argv[1]) as dev_file:
     devices = json.load(dev_file)

results = {'Successful': [], 'Failed': []}

for device in devices:
    device['username'] = username
    device['password'] = password
    try:
        print('~' * 79)
        print('Connecting to device:', device['ip'])
        print()
        connection = netmiko.ConnectHandler(**device)
        log_message = 'send log 6 "{} change {}"'
        connection.send_command(log_message.format('Starting', change_number))
        output = connection.send_command('show cdp neighbors')
        config = get_config_from_cdp_neighbors(output)
        print('\n'.join(config))
        connection.send_config_set(config)
        connection.send_command('write memory')
        connection.send_command(log_message.format('Completed', change_number))
        connection.disconnect()
        results['Successful'].append(device['ip'])
    except netmiko_exceptions as error:
        print('Failed to ', device['ip'], error)
        results['Failed'].append(': '.join((device['ip'], str(error))))

print(json.dumps(results, indent=2))
with open('results-' + change_number + '.json', 'w') as results_file:
    json.dump(results, results_file, indent=2)


"""Changes from original Video:
Line 38:
Using os.path.split() which provides a path split function
that works equally well on Windows or Linux/Unix.
Line 61:
Created a log_message string variable that includes most of the text
that will be written to the system log.
Also using the "6" to send the message as "INFO" level log,
rather than "DEBUG" level log.
Line 62 and 68:
Using the log_message variable to create the string with either
'Starting' or 'Completed' plus the change number.
Line 71:
Capturing the exceptions as "error", rather than just as "e"
"""