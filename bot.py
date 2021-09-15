import sound
import discord
import logging
from discord.ext import commands

class Dap_Bot(commands.Bot):
	def __init__(self):
		self.stream = sound.PCMStream()
		self.device_id = -1

	# params: int new_id
	def change_device(self, new_id):
		if new_id != self.device_id:
			self.device_id = new_id
			self.stream.change_device(new_id)

	# params: float volume
	# return: boolean
	def change_volume(self, volume):
		if (volume >= 0.0 and volume <= 2.0):
			discord.PCMVolumeTransformer(self.stream, volume)
			return True
		return False