import sys
import sound
import discord
import logging
import config
import psutil
import typing
from discord.ext import commands

# ------------
# Bot commands
# ------------

# params: Discord.ext.commands.Context context, List[str] split_channel_name
@commands.command(brief="Joins a voice channel.", description="Joins the user's current voice channel or a specified channel.")
async def join(context, *split_channel_name):
	# int channel_id
	channel_id = 0
	# str channel_name
	channel_name = ""

	if len(split_channel_name) == 0:
		# Discord.Member author
		author = context.author
		# Discord.VoiceState author_voice
		author_voice = author.voice
		if author_voice is not None:
			# Discord.VoiceChannel channel
			channel = author_voice.channel
			if channel.type == discord.ChannelType.voice:
				channel_id = channel.id
				channel_name = channel.name
	else:
		# str space_str
		space_str = " "
		channel_name = space_str.join(split_channel_name)
		# Discord.Guild server
		server = context.guild
		# List[Discord.VoiceChannel] channels
		channels = server.voice_channels
		for channel in channels:
			if channel.name == channel_name:
				channel_id = channel.id
	
	if channel_id == 0:
		print("Error: User wasn't in a voice channel and did not provide the name of one.")
		await context.send("Error: User must be in a voice channel or specify a voice channel's name when calling !join.")
	else:
		try:
			print("Joining channel...")
			# discord.VoiceChannel channel
			channel = context.bot.get_channel(channel_id)

			await context.bot.join_voice_channel(channel)

			print("Playing audio in {}".format(channel.name))
			await context.send("Joined channel {}.".format(channel.name))
		except Exception:
			logging.exception("Error on channel join")
			await context.send("Error joining channel {}.".format(channel_name))

# params: Discord.ext.commands.Context context
@commands.command(brief="Leaves the voice channel.", description="Leaves the current voice channel if in one.")
async def leave(context):
	# boolean success
	success = False
	# Discord.VoiceChannel channels
	channel = get_current_voice_channel(context)
	if channel is not None:
		await context.bot.leave_voice_channel()

		print("Left channel {}".format(channel.name))
		await context.send("Left channel {}.".format(channel.name))
	else:
		print("Error: Not in voice channel")
		await context.send("Error: Bot was not in a voice channel on this server.")

# params: Discord.ext.commands.Context context, int volume
@commands.command(brief="Check or adjust volume.", description="Changes volume to specified percentage or reports the current volume.")
async def volume(context, vol: typing.Optional[int]):
	if vol is None:
		# Respond with current volume.
		# int cur_volume
		cur_volume = int(config.get_config_float("Audio", "volume") * 100.0)
		print("Current volume requested")
		await context.send("Volume is currently set to {}%.".format(cur_volume))
	else:
		float_vol = float(vol) / 100.0
		if context.bot.change_volume(float_vol):
			print("Volume changed")
			await context.send("Volume changed to {}%".format(vol))
		else:
			print("Error: bad volume value")
			await context.send("Error: !volume accepts integer values from 0 to 200.")

# params: Discord.ext.commands.Context context
@commands.command(brief="Lists audio devices.", description="Outputs a list of audio devices present on the bot's host machine.  The indices can be used for `!set_device`.")
async def devices(context):
	print("Device list requested.")
	# sounddevice.DeviceList device_list
	device_list = None
	try:
		device_list = sound.query_devices()
		await context.send(sound.query_devices())
	except DeviceNotFoundError:
		logging.exception("Error: exception in sound.query_devices()")
		await context.send("Error: Could not retrieve device list.  Contact administrator.")

# params: Discord.ext.commands.Context context, int device_id
@commands.command(brief="Changes audio device.", description="Changes which audio device the bot is outputting from, based on indices presented in `!devices`")
async def set_device(context, device_id: int):
	if context.bot.use_vban:
		await context.send("VBAN mode does not use audio devices.")
	elif context.bot.change_device(device_id):
		await context.send("Now playing from device {}".format(device_id))
	else:
		await context.send("Error: !set_device requires a valid device id.  Call !devices for a list of valid devices.")

# params: Discord.ext.commands.Context context
@commands.command(brief="Provides bot's current status.", description="Outputs current voice channel, audio device, and whether the watched process is active.")
async def status(context):
	# present voice connection status, current audio device, and watched process status
	print("Status requested")

	# String message
	message = "Current Status:"

	# Find current voice channel
	# Discord.VoiceChannel channel
	channel = get_current_voice_channel(context)
	if channel is not None:
		message = message + "\nConnected to voice channel \"{}\"".format(channel.name)
	else:
		message = message + "\nNot currently connected to a voice channel."

	if context.bot.use_vban:
		message = message + "\nRunning in VBAN mode.  Listening for stream \"{}\"".format(config.get_config_string("VBAN", "stream_name"))
	else:
		# Get current audio device
		try:
			# dict device
			device = sound.get_device(context.bot.device_id)
			message = message + "\nCurrent audio device is [{}] {}".format(context.bot.device_id, device["name"])
		except DeviceNotFoundError:
			logging.exception("Error: exception in sound.get_device()")
			message = message + "\nInvalid audio device.  Please check the list of audio devices with !devices and set a new one using !set_device."

		# Check watched process
		# String process_name
		process_name = config.get_config_string("System", "watched_process_name")
		if process_name == "":
			message = message + "\nNo watched process."
		else:
			if check_process(process_name):
				message = message + "\nProcess \"{}\"" is running.".format(process_name)
			else:
				message = message + "\nNo running process named \"{}\"".format(process_name)

	await context.send(message)

#params: Discord.ext.commands.Context context, str process_name
@commands.command(brief="Changes watched process.", description="Sets the watched process to the specified name.  You can use `!status` to see that process's status.")
async def watch(context, process_name: typing.Optional[str]):
	if context.bot.use_vban:
		await context.send("Watched process is not supported in VBAN mode.")
		return
	
	print("Watched process changed to {}".format(process_name))
	if process_name is None:
		config.set_config("System", "watched_process_name", "")
		await context.send("Watched process has been cleared.")
	else:
		config.set_config("System", "watched_process_name", process_name)
		# String message
		message = "Now watching process \"{}\".".format(process_name)
		if (check_process(process_name)):
			message = message + "  It is active."
		else:
			message = message + "  It is not active."
		await context.send(message)

# params: Discord.ext.commands.Context context, str new_ip
@commands.command(brief="Changes VBAN source IP and stream name.", description="Changes which IP address to listen from and stream identifier when running in VBAN mode.")
async def vban_change_stream(context, new_ip, stream_name: typing.Optional[str]):
	if context.bot.use_vban:
		config.set_config("VBAN", "incoming_ip", new_ip)
		if stream_name is not None:
			config.set_config("VBAN", "stream_name", stream_name)
		context.bot.reset_stream()

		# str output_name
		output_name = stream_name
		if output_name is None:
			output_name = config.get_config_string("VBAN", "stream_name")

		await context.send("Now listening to {} on stream \"{}\"".format(new_ip, output_name))
	else:
		await context.send("Not running in VBAN mode.")

# ----------------
# End bot commands
# ----------------

# params: Discord.ext.commands.Context context
# return Discord.VoiceChannel
def get_current_voice_channel(context):
	for client in context.bot.voice_clients:
		# Discord.VoiceChannel channel
		channel = client.channel
		if channel.guild == context.guild:
			return channel
	return None

# params: String process_name
# return boolean
def check_process(process_name):
	success = False
	for process in psutil.process_iter():
		try:
			if process_name.lower() == process.name().lower():
				success = True
				break
		except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
			pass
	return success

# params: bot.Dap_Bot bot
def add_commands(bot):
	bot.add_command(join)
	bot.add_command(leave)
	bot.add_command(volume)
	bot.add_command(devices)
	bot.add_command(set_device)
	bot.add_command(status)
	bot.add_command(watch)

# params: bot.Dap_Bot bot
async def connect(bot):
	try:
		print("Connecting to Discord...")
		await bot.wait_until_ready()
		print("Logged in to Discord as {}!".format(bot.user.name))

	except Exception:
		logging.exception("Error on cli connect")
		sys.exit(1)
