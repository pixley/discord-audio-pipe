import logging

# error logging
error_formatter = logging.Formatter(
	fmt="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

error_handler = logging.FileHandler("VBAN_errors.log", delay=True)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

info_handler = logging.FileHandler("VBAN.log", delay=True)
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(error_formatter)

base_logger = logging.getLogger()
base_logger.addHandler(error_handler)
base_logger.addHandler(info_handler)

import vban
import config
import asyncio
import sounddevice as sd

DEFAULT = 0
sd.default.channels = 2
sd.default.dtype = "int16"
sd.default.latency = "low"
sd.default.samplerate = 48000

async def main():
	# str host
	host = config.get_config_string("VBAN", "outgoing_host")
	# int port
	port = config.get_config_int("VBAN", "outgoing_port")
	# str stream_name
	stream_name = config.get_config_string("VBAN", "stream_name")
	# int device_id
	device_id = config.get_config_int("VBAN", "listen_device_id")
	# bool ipv6
	ipv6 = config.get_config_bool("VBAN", "ipv6")
	# bool verbose
	verbose = config.get_config_bool("VBAN", "verbose")

	# dict device
	device = sd.query_devices(device_id)
	print("Audio device: {}".format(device["name"]))

	# vban.VBAN_Send sender
	sender = vban.VBAN_Send(host, port, stream_name, sd.default.samplerate, device_id, ipv6=ipv6, verbose=verbose)
	try:
		while True:
			sender.runonce()
			await asyncio.sleep(0)
	except Exception as e:
		logging.exception("Exception in main!")
		print(e)
		sender.quit()

# run program
config.setup_config("vban_sender.cfg")
loop = asyncio.get_event_loop()
try:
	loop.run_until_complete(main())
except Exception as e:
	logging.info("Exiting...")
	print(e)
	# this sleep prevents a bugged exception on Windows
	loop.run_until_complete(asyncio.sleep(1))
	loop.close()