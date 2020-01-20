#!/usr/bin/env python3
# coding: utf-8
# vim: noet ts=2 sw=2 sts=2

import os
import time
import collectd

from sem6000 import SEMSocket
import bluepy

instances = []

def init_func():
	pass

def config_func(cfg):
	global instances

	config = {}

	for node in cfg.children:
		key = node.key.lower()
		value = node.values[0]

		if key in ['address', 'socketname']:
			config[key] = value

		if key == 'readtimeout':
			config['readtimeout'] = int(value)

		if key == 'suspendtime':
			config['suspendtime'] = int(value)

	if 'address' not in config.keys():
		collectd.error('sem6000: address must be set')
		return

	if 'socketname' not in config.keys():
		config['socketname'] = config['address'].replace(':', '')

	if 'readtimeout' not in config.keys():
		config['readtimeout'] = 30

	if 'suspendtime' not in config.keys():
		config['suspendtime'] = 300

	instances.append( {
		'config': config,
		'socket': None,
		'suspended': False,
		'lastsuccess': 0,
		'resumetime': 0
		} )

def read_func():
	global instances

	for inst in instances:
		config = inst['config']

		if inst['suspended']:
			if time.time() < inst['resumetime']:
				continue
			else:
				collectd.info("sem6000: Device {} waking up.".format(config['address']))
				inst['suspended'] = False
				inst['lastsuccess'] = time.time()

		try:
			if inst['socket'] == None:
				collectd.info("sem6000: Connecting to {}...".format(config['address']))

				inst['socket'] = SEMSocket(config['address'])
				collectd.info("sem6000: Connected.")

			inst['socket'].getStatus()
		except (SEMSocket.NotConnectedException, bluepy.btle.BTLEDisconnectError, BrokenPipeError) as e:
			collectd.warning("sem6000: Exception caught: {}".format(e))
			collectd.warning("sem6000: Restarting on next cycle...")

			if inst['lastsuccess'] < time.time() - config['readtimeout']:
				collectd.error("sem6000: no successful communication with {} for {:.1f} seconds. Suspending device for {:.1f} seconds.".format(
					config['address'], config['readtimeout'], config['suspendtime']))

				inst['suspended'] = True
				inst['resumetime'] = time.time() + config['suspendtime']

			if inst['socket'] != None:
				inst['socket'].disconnect()
				inst['socket'] = None

		socket = inst['socket']

		if socket != None and socket.voltage != 0:
			collectd.debug("Uploading values for {}".format(socket.mac_address))

			inst['lastsuccess'] = time.time()

			val = collectd.Values(plugin = 'sem6000-{}'.format(config['socketname']))

			val.type = 'voltage'
			val.type_instance = 'grid'
			val.values = [ socket.voltage ]
			val.dispatch()

			val.type = 'current'
			val.type_instance = 'load'
			val.values = [ socket.current ]
			val.dispatch()

			val.type = 'power'
			val.type_instance = 'real_power'
			val.values = [ socket.power ]
			val.dispatch()

			val.type = 'gauge'
			val.type_instance = 'power_factor'
			val.values = [ socket.power_factor ]
			val.dispatch()

			val.type = 'gauge'
			val.type_instance = 'load_on'
			val.values = [ socket.powered ]
			val.dispatch()

			val.type = 'frequency'
			val.type_instance = 'grid'
			val.values = [ socket.frequency ]
			val.dispatch()

def shutdown_func():
	global instances

	for inst in instances:
		if inst['socket'] != None:
			inst['socket'].disconnect()

	instances = []

collectd.register_config(config_func)
collectd.register_init(init_func)
collectd.register_read(read_func)
collectd.register_shutdown(shutdown_func)
