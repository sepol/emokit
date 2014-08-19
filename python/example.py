#!/usr/bin/python

"""
About this example:
This is a simple example, based on the render.py module in emokit, that renders sensor data and streams it via UDP.
The UDP server runs on port 50010, which may be changed, and accepts a single request from a client.
Requests either contain a single packed integer -- the sample rate -- or two packed integer -- the sample rate and scan size.
The response is the number of channels, which will always be 18.
After that, a new socket is opened to stream the packets, which have the following channel ordering:
[Counter, Battery Level, gyroX, gyroY, 'F3','FC5','AF3','F7','T7','P7','O1','O2','P8','T8','F8','AF4','FC6','F4']
This is hard-coded in the emotiv.py file at the moment, but may easily be changed by reordering the sensorNames structure
"""

import pygame
import gevent
import sys
import socket
import time
from threading import Thread
import numpy as np
from struct import pack, unpack

from emokit.emotiv import Emotiv

class Grapher(object):
	def __init__(self, screen, name, i):
		self.screen = screen
		self.name = name
		self.range = float(1 << 13)
		self.xoff = 40
		self.y = i * gheight
		self.buffer = []
		font = pygame.font.Font(None, 24)
		self.text = font.render(self.name, 1, (255, 0, 0))
		self.textpos = self.text.get_rect()
		self.textpos.centery = self.y + gheight

	def update(self, packet):
		if len(self.buffer) == 800 - self.xoff:
			self.buffer = self.buffer[1:]
		self.buffer.append([packet.sensors[self.name]['value'], packet.sensors[self.name]['quality'], ])

	def calcY(self, val):
		return int(val / self.range * gheight)

	def draw(self):
		if len(self.buffer) == 0:
			return
		pos = self.xoff, self.calcY(self.buffer[0][0]) + self.y
		for i, (value, quality ) in enumerate(self.buffer):
			y = self.calcY(value) + self.y
			if quality == 0:
				color = (0, 0, 0)
			elif quality == 1:
				color = (255, 0, 0)
			elif quality == 2:
				color = (255, 165, 0)
			elif quality == 3:
				color = (255, 255, 0)
			elif quality == 4:
				color = (0, 255, 0)
			else:
				color = (255, 255, 255)
			pygame.draw.line(self.screen, color, pos, (self.xoff + i, y))
			pos = (self.xoff + i, y)
		self.screen.blit(self.text, self.textpos)

def udpServer():
	global acquiring
	global udp_clients
	global udp_active
	udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	udp_server.bind(('',50010))
	udp_server.setblocking(0)
	while acquiring:
		try:
			rate, addr = udp_server.recvfrom(8)
		except socket.error:
			pass
		else:
			if addr in udp_clients:
				udp_active[addr] = False
				udp_clients.remove(addr)
			elif len(udp_clients) >= 5:
				print 'No UDP connection accepted from ' + str(addr[0]) + ':' + str(addr[1]) + ' because too many clients are connected.'
			else:
				if len(rate) > 4:
					samples, scans = unpack('<ii', rate)
				else:
					samples, = unpack('<i', rate)
					scans = 1
				udp_clients.append(addr)
				udp_active[addr] = True
				channels = pack('<i', 18)
				udp_server.sendto(channels, addr)
				Thread(target=udpThread, args=(samples, scans, addr)).start()
				print 'UDP client connected on ' + str(addr[0]) + ':' + str(addr[1]) + ' at rate ' + str(samples) + 'Hz'
	for client in udp_clients:
		udp_active[client] = False
	udp_clients = []
	udp_server.close()
	print 'Disabled UDP server on port ' + str(50010)
	return

def udpThread(samples, scans, addr):
	global udp_active, buffer_1, buffer_2, buffer_ind
	udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	delay = 1.0/float(samples)
	try:
		while udp_active[addr]:
			prev = time.time()
			if buffer_ind[1] > (scans - 1):
				if buffer_ind[0] == 0:
					tosend = buffer_1[:,(buffer_ind[1]-scans):buffer_ind[1]]
				else:
					tosend = buffer_2[:,(buffer_ind[1]-scans):buffer_ind[1]]
				tosend = np.reshape(tosend, (1, np.size(tosend)), 'F').squeeze()
				tosend = pack('<%sf' % len(tosend), *tosend)
				udp_client.sendto(tosend, addr)
			temp = delay - (time.time() - prev)
			if temp > 0:
				time.sleep(temp)
	except:
		print 'Unable to detect whether ' + str(addr) + ' is active or not; closing connection'
	print 'UDP connection with ' + str(addr[0]) + ':' + str(addr[1]) + ' closed'
	return

def main(debug=False):
	global gheight, max_cols, buffer_1, buffer_2, buffer_ind
	# NOTE TO MAC USERS:
	# There is currently a bug in cython-hidapi preventing getting the serial number automatically
	# Instead, get the serial number of the emotiv dongle from the System Report tool and enter it below
	# emotiv = Emotiv(displayOutput=False,serialNumber='<serial number here>')
	emotiv = Emotiv(displayOutput=False)
	gevent.spawn(emotiv.setup)
	gevent.sleep(1)
	pygame.init()
	screen = pygame.display.set_mode((800, 600))
	graphers = []
	recordings = []
	recording = False
	record_packets = []
	updated = False
	curX, curY = 400, 300

	for name in 'AF3 F7 F3 FC5 T7 P7 O1 O2 P8 T8 FC6 F4 F8 AF4'.split(' '):
		graphers.append(Grapher(screen, name, len(graphers)))
	fullscreen = False
	Thread(target=udpServer).start()
	while True:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				emotiv.close()
				return
			if (event.type == pygame.KEYDOWN):
				if (event.key == pygame.K_ESCAPE):
					emotiv.close()
					return
				elif (event.key == pygame.K_f):
					if fullscreen:
						screen = pygame.display.set_mode((800, 600))
						fullscreen = False
					else:
						screen = pygame.display.set_mode((800,600), FULLSCREEN, 16)
						fullscreen = True
				elif (event.key == pygame.K_r):
					if not recording:
						record_packets = []
						recording = True
					else:
						recording = False
						recordings.append(list(record_packets))
						record_packets = None
		packetsInQueue = 0
		try:
			while packetsInQueue < 8:
				packet = emotiv.dequeue()
				d = packet.get_data()
				if buffer_ind[0] == 0:
					buffer_1[:,buffer_ind[1]] = d
				else:
					buffer_2[:,buffer_ind[1]] = d
				buffer_ind[1] += 1
				if buffer_ind[1] >= max_cols:
					buffer_ind[1] = 0
					if buffer_ind[0] == 0:
						buffer_ind[0] = 1
					else:
						buffer_ind[0] = 0
				if abs(packet.gyroX) > 1:
					curX = max(0, min(curX, 800))
					curX -= packet.gyroX
				if abs(packet.gyroY) > 1:
					curY += packet.gyroY
					curY = max(0, min(curY, 600))
				map(lambda x: x.update(packet), graphers)
				if recording:
					record_packets.append(packet)
				updated = True
				packetsInQueue += 1
		except Exception, e:
			print e
		if updated:
			screen.fill((75, 75, 75))
			map(lambda x: x.draw(), graphers)
			pygame.draw.rect(screen, (255, 255, 255), (curX - 5, curY - 5, 10, 10), 0)
			pygame.display.flip()
			updated = False
		gevent.sleep(0)

try:
	max_cols = (2000000/(18*8)) # 200 MB buffers
	buffer_1 = np.zeros((18,max_cols))
	buffer_2 = np.zeros((18,max_cols))
	buffer_1[:] = np.nan
	buffer_2[:] = np.nan
	buffer_ind = [0,0]
	
	gheight = 600 / 14
	hgheight = gheight >> 1
	acquiring = True
	udp_clients = []
	udp_active = {}
	main(*sys.argv[1:])
	acquiring = False

except Exception, e:
	print e