# SEM6000 Python Library

SEM6000 is a energy meter and power switch with Bluetooth 4.0.

This library provides a Python module for these devices

## Run the example code

```
$ git clone … sem6000
$ cd sem6000
$ virtualenv -p python3 python3_venv
$ . ./python3_venv/bin/activate
$ pip3 install -r requirements.txt
$ python3 example.py
```

## Collectd Plugin

You can find a Plugin for [collectd](https://collectd.org) in the `collectd`
subdirectory.

Installation procedure (the target directory may be changed of course):

```shell
# mkdir -p /usr/local/lib/collectd/python
# cp collectd/collectd_sem6000.py /usr/local/lib/collectd/python
# cp sem6000.py /usr/local/lib/collectd/python
```

Add or adjust the configuration for your collectd’s Python plugin as follows:

```
<Plugin python>
  ModulePath "/usr/local/share/collectd/python"
  LogTraces true
  Interactive false
  Import "collectd_sem6000"

  <Module collectd_sem6000>
    Address "12:34:56:78:90:ab"
    SocketName "FirstSocket"
  </Module>
  <Module collectd_sem6000>
    Address "ab:cd:ef:13:37:42"
    SocketName "ASecondSocket"
  </Module>
  # ...
</Plugin>
```

Make sure that everything listed in `requirements.txt` is available to the user
running collectd.

