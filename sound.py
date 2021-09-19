import discord
import sounddevice as sd
from pprint import pformat

DEFAULT = 0
sd.default.channels = 2
sd.default.dtype = "int16"
sd.default.latency = "low"
sd.default.samplerate = 48000


class PCMStream(discord.AudioSource):
	def __init__(self):
		discord.AudioSource.__init__(self)
		self.stream = None

	def read(self):
		if self.stream is None:
			print("Audio stream unavailable.")
			return
		
		# frame is 4 bytes
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