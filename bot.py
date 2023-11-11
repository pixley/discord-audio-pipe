import sound
import discord
import logging
import config
from discord.ext import commands
import datetime
import asyncio

class Dap_Bot(commands.Bot):
	def __init__(self, command_prefix, intents):
		commands.Bot.__init__(self, command_prefix, intents=intents)
		# discord.AudioSource stream
		self.stream = None
		# int device_id
		self.device_id = -1
		# discord.VoiceClient voice
		self.voice = None
		# boolean use_vban
		self.use_vban = False

	def apply_config(self):
		self.use_vban = config.get_config_bool("Audio", "use_vban")

	def start_stream(self):
		if self.voice is None:
			return
	
		if self.use_vban:
			self.stream = sound.VBANStream()
			self.stream.start_vban()
		else:
			# device id
			self.device_id = config.get_config_int("Audio", "device_id")
			self.stream = sound.PCMStream()
			self.stream.change_device(self.device_id)
			
		# float vol	
		vol = config.get_config_float("Audio", "volume")
		
		if self.voice.is_playing():
			self.voice.stop()
		
		self.voice.play(self.stream)
		self.voice.source = discord.PCMVolumeTransformer(original=self.stream, volume=vol)

	# params: int new_id
	# return boolean
	def change_device(self, new_id):
		if not self.use_vban:
			if new_id != self.device_id:
				# sounddevice.DeviceList device_list
				device_list = sound.query_devices()
				# int device_count
				device_count = len(device_list)
				if new_id >= 0 and new_id < device_count:
					self.device_id = new_id
					self.stream.change_device(new_id)
					config.set_config("Audio", "device_id", new_id)
					print("Device {} selected".format(new_id))
					return True
				else:
					print("Error: invalid device id or no devices available!")
					return False
		else:
			return False

	# params: float volume
	# return: boolean
	def change_volume(self, volume):
		if volume >= 0.0 and volume <= 2.0:
			if self.voice is not None and self.voice.source is not None:
				self.voice.source.volume = volume
			config.set_config("Audio", "volume", volume)
			return True
		return False

	#params: Discord.VoiceChannel channel
	async def join_voice_channel(self, channel):
		self.voice = await channel.connect()
		self.start_stream()

	async def leave_voice_channel(self):
		if self.voice is not None:
			await self.voice.disconnect()
			self.voice = None
		if self.stream is not None:
			self.stream.cleanup()
			self.stream = None

	def reset_stream(self):
		if self.voice is not None:
			if self.stream is not None:
				self.stream.cleanup()
			if self.voice is not None and self.voice.source is not None:
				self.start_stream()

	def queue_message(self, guild_id: int, channel_id: int, message: str, delay: int):
		asyncio.create_task(self.post_queued_message(guild_id, channel_id, message, delay))

	async def post_queued_message(self, guild_id: int, channel_id: int, message: str, delay: int):
		await asyncio.sleep(delay)
		# discord.Guild guild
		guild = self.get_guild(guild_id)
		if guild is None:
			print("Error: guild doesn't exist")
			return
		# discord.abd.GuildChannel channel
		channel = guild.get_channel(channel_id)
		if channel is None:
			print("Error: channel doesn't exist")
			return
		if isinstance(channel, discord.TextChannel):
			await channel.send(message)
		else:
			print("Error: channel is no longer a text channel.")