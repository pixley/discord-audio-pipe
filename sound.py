import discord
import vban
import collections
import asyncio
import config
import sounddevice as sd
import threading
import logging
from pprint import pformat

DEFAULT = 0
sd.default.channels = 2
sd.default.dtype = "int16"
sd.default.latency = "low"
sd.default.samplerate = 48000

class VBANStream(discord.AudioSource):
	# int bytes_per_frame
	# 4 bytes per sample (stereo 16-bit audio)
	bytes_per_frame = 3840
	# int bytes_per_sec
	# this is dictated by Discord; each frame is 20 ms
	bytes_per_sec = bytes_per_frame * 50

	def __init__(self):
		discord.AudioSource.__init__(self)
		# bytearray stream_buffer
		# holds ten seconds of audio as a FIFO queue
		# insert on right, remove on left
		self.stream_buffer = bytearray()
		# int sample_rate
		self.sample_rate = sd.default.samplerate
		# asyncio.Task recv_task
		self.recv_task = None
		# boolean verbose
		self.verbose = config.get_config_bool("VBAN", "verbose")
		# threading.Lock buffer_lock
		self.buffer_lock = threading.Lock()
		# bool buffering
		self.buffering = False
		# float buffering_min
		# if the buffer has less than this many seconds worth of audio data, buffering will be enabled
		self.buffering_min = config.get_config_float("VBAN", "buffering_min")
		# float buffering_max
		# if we are buffering, when the buffer reaches this many seconds worth of audio data, buffering will be disabled
		self.buffering_max = config.get_config_float("VBAN", "buffering_max")
		# vban.VBAN_Recv receiver
		self.receiver = None

	def read(self):
		# int frame_len
		frame_len = VBANStream.bytes_per_frame

		self.buffer_lock.acquire()
		# ENTER CRITICAL SECTION
		# int buffer_len
		buffer_len = len(self.stream_buffer)

		# enforce buffer constraints
		if self.buffering and buffer_len > int(VBANStream.bytes_per_sec * self.buffering_max):
			self.buffering = False
		elif not self.buffering and buffer_len < int(VBANStream.bytes_per_sec * self.buffering_min):
			self.buffering = True

		if self.buffering:
			# END CRITICAL SECTION
			self.buffer_lock.release()
			# we don't have enough audio to present a 20 ms frame; return the corresponding amount of silence instead
			if self.verbose:
				logging.info("Insufficient audio data in VBAN buffer; transmitting silence")
			# the bytes(int) constructor creates a zero-filled object of length equal to the param
			return bytes(frame_len)
		else:
			# bytes frame
			frame = bytes(self.stream_buffer[0:frame_len])
			# remove the frame bytes from the buffer before returning
			del self.stream_buffer[0:frame_len]
			# int new_len
			new_len = len(self.stream_buffer)
			if self.verbose:
				logging.info("Removing {} bytes from VBAN buffer".format(frame_len))
				logging.info("VBAN buffer now contains {} bytes".format(new_len))
			# END CRITICAL SECTION
			self.buffer_lock.release()
			return frame


	# params: bytes raw_pcm
	def write(self, raw_pcm):
		self.buffer_lock.acquire()
		# ENTER CRITICAL SECTION
		self.stream_buffer += raw_pcm
		# int new_len
		new_len = len(self.stream_buffer)
		if self.verbose:
			logging.info("Recieved data from {}.".format(self.receiver.senderIp))
			logging.info("Adding {} bytes to VBAN buffer".format(len(raw_pcm)))
			logging.info("VBAN buffer now contains {} bytes".format(new_len))
		# END CRITICAL SECTION
		self.buffer_lock.release()

	def cleanup(self):
		self.stop_vban()

	def close(self):
		# need close() to satisfy the interface VBAN_Recv expects, but we're doing the closure on this side (see cleanup()).
		pass

	# return: boolean
	def is_opus(self):
		return False

	def start_vban(self):
		logging.info("Creating VBAN task...")
		self.recv_task = asyncio.create_task(self.recv_vban())

	def stop_vban(self):
		if self.recv_task is not None:
			logging.info("Cancelling VBAN task...")
			self.recv_task.cancel()
			self.recv_task = None

	async def recv_vban(self):
		logging.info("Initializing VBAN receiver...")
		# str host
		host = config.get_config_string("VBAN", "incoming_host")
		# int port
		port = config.get_config_int("VBAN", "incoming_port")
		# bool ipv6
		ipv6 = config.get_config_bool("System", "ipv6")
		# str stream_name
		stream_name = config.get_config_string("VBAN", "stream_name")
		
		if host == "any":
			# if we want any incoming host, then we pass None into VBAN_Recv
			host = None

		try:
			# vban.VBAN_Recv receiver
			self.receiver = vban.VBAN_Recv(host, stream_name, port, 0, ipv6=ipv6, verbose=self.verbose, stream=self)
			# str logging.infoed_ip
			logging.infoed_ip = self.receiver.senderIp
			if ipv6:
				logging.infoed_ip = "[" + logging.infoed_ip + "]"
			logging.info("VBAN receiver initalized on {}:{}!".format(logging.infoed_ip, port))

			try:
				while True:
					try:
						self.receiver.runforever()
					except IndexError:
						# we have nothing left to receive; let's wait a bit
						await asyncio.sleep(0.02)
			except asyncio.CancelledError:
				logging.info("VBAN task cancelled!")
				self.receiver.quit()
		except Exception as e:
			logging.info(e)
			logging.info("Connection to {} failed.".format(host))
		self.stream_buffer = bytearray()
		self.reciever = None


class PCMStream(discord.AudioSource):
	def __init__(self):
		discord.AudioSource.__init__(self)
		self.stream = None

	def read(self):
		if self.stream is None:
			logging.info("Audio stream unavailable.")
			return
		
		# Discord reads 20 ms worth of audio at a time (20 ms * 50 == 1000 ms == 1 sec)
		frames = int(self.stream.samplerate / 50)
		data = self.stream.read(frames)[0]

		# convert to pcm format
		return bytes(data)

	def change_device(self, num):
		if self.stream is not None:
			self.stream.stop()
			self.stream.close()

		self.stream = sd.RawInputStream(device=num)
		self.stream.start()

	def cleanup(self):
		if self.stream is not None:
			self.stream.stop()
			self.stream.close()
			self.stream = None

	def is_opus(self):
		return False


class DeviceNotFoundError(Exception):
	def __init__(self):
		self.devices = sd.query_devices()
		self.host_apis = sd.query_hostapis()
		super().__init__("No Devices Found")

	def __str__(self):
		return (
			"Devices \n"
			"{self.devices} \n "
			"Host APIs \n"
			"{pformat(self.host_apis)}"
		)


def query_devices():
	options = {
		device.get("name"): index
		for index, device in enumerate(sd.query_devices())
		if (device.get("max_input_channels") > 0 and device.get("hostapi") == DEFAULT)
	}

	if not options:
		raise DeviceNotFoundError()

	return options

def get_device(index):
	device = sd.query_devices(index)
	if device is None:
		raise DeviceNotFoundError()
	else:
		return device