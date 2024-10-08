import vban
import config
import asyncio
import sounddevice as sd
import pkg_resources
import logging

print_formatter = logging.Formatter(
	fmt="[%(name)s - %(levelname)s] %(message)s"
)

print_handler = logging.StreamHandler()
print_handler.setLevel(logging.INFO)
print_handler.setFormatter(print_formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(print_handler)


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
	
	if verbose:
		print_handler.setLevel(logging.DEBUG)

	# dict device
	device = sd.query_devices(device_id)
	logging.info("Audio device: {}".format(device["name"]))

	try:
		# vban.VBAN_Send sender
		sender = vban.VBAN_Send(host, port, stream_name, sd.default.samplerate, device_id, ipv6=ipv6, verbose=verbose)
		# str printed_ip
		printed_ip = sender.toIp
		if ipv6:
			printed_ip = "[" + printed_ip + "]"
		logging.info("Beginning VBAN stream \"{}\" to {}:{}".format(stream_name, printed_ip, port))
		try:
			while True:
				sender.runonce()
				await asyncio.sleep(0)
		finally:
			sender.quit()
	except Exception:
		logging.exception()
		logging.info("Connection to {} failed.".format(host))

# check dependency on pyaudio, as we don't import it, and not having it will silently fail
if "pyaudio" not in {pkg.key for pkg in pkg_resources.working_set}:
	logging.error("This applet requires the 'pyaudio' package.  You can install it with the command 'pip install pyaudio'.")
	quit()
else:
	logging.info("Package 'pyaudio' found!")

# run program
config.setup_config("vban_sender.cfg")
loop = asyncio.get_event_loop()
try:
	loop.run_until_complete(main())
except KeyboardInterrupt:
	logging.info("Exit requested!")
except Exception:
	logging.exception
finally:
	logging.info("Exiting...")
	# this sleep prevents a bugged exception on Windows
	loop.run_until_complete(asyncio.sleep(1))
	loop.close()