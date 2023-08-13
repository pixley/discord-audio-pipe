import sys
import sound
import discord
import logging
import config
import psutil
import typing
import string
from discord.ext import commands
import secret_rolls as sroll
import datetime
import zoneinfo

# -------------------------
# Bot command global checks
# -------------------------

# params: Discord.ext.commands.Context context
@commands.check
async def no_dms(context):
	return context.guild is not None

# params: Discord.ext.commands.Context context
@commands.check
async def role_whitelist(context):
	# always allow admin users to control the bot
	for role in context.author.roles:
		if role.permissions.administrator:
			return True

	# List[str] allowed_roles
	allowed_roles = config.get_config_str_list("Commands", "role_whitelist")
	if "everyone" in allowed_roles:
		return True

	# Set[str] role_set
	# For more optimized access
	role_set = set(allowed_roles)
	for role in context.author.roles:
		if role.name in role_set:
			return True

	return False

# ------------
# Voice commands
# ------------

class VoiceCog(commands.Cog, name="Voice Commands"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.command(brief="Joins a voice channel.", description="Joins the user's current voice channel or a specified channel.")
	async def join(self, context, *split_channel_name):
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
			channel_name = " ".join(split_channel_name)
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

	@commands.command(brief="Leaves the voice channel.", description="Leaves the current voice channel if in one.")
	async def leave(self, context):
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

	@commands.command(brief="Check or adjust volume.", description="Changes volume to specified percentage or reports the current volume.")
	async def volume(self, context, vol: typing.Optional[int]):
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

	@commands.command(brief="Lists audio devices.", description="Outputs a list of audio devices present on the bot's host machine.  The indices can be used for `!set_device`.")
	async def devices(self, context):
		print("Device list requested.")
		# sounddevice.DeviceList device_list
		device_list = None
		try:
			device_list = sound.query_devices()
			await context.send(sound.query_devices())
		except DeviceNotFoundError:
			logging.exception("Error: exception in sound.query_devices()")
			await context.send("Error: Could not retrieve device list.  Contact administrator.")

	@commands.command(brief="Changes audio device.", description="Changes which audio device the bot is outputting from, based on indices presented in `!devices`")
	async def set_device(self, context, device_id: int):
		if context.bot.use_vban:
			await context.send("VBAN mode does not use audio devices.")
		elif context.bot.change_device(device_id):
			await context.send("Now playing from device {}".format(device_id))
		else:
			await context.send("Error: !set_device requires a valid device id.  Call !devices for a list of valid devices.")

	@commands.command(brief="Provides bot's current status.", description="Outputs current voice channel, audio device, and whether the watched process is active.")
	async def status(self, context):
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
					message = message + "\nProcess \"{}\" is running.".format(process_name)
				else:
					message = message + "\nNo running process named \"{}\"".format(process_name)

		await context.send(message)

	@commands.command(brief="Changes watched process.", description="Sets the watched process to the specified name.  You can use `!status` to see that process's status.")
	async def watch(self, context, process_name: typing.Optional[str]):
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

	@commands.command(brief="Changes VBAN source IP and stream name.", description="Changes which IP address to listen from and stream identifier when running in VBAN mode.")
	async def vban_change_stream(self, context, new_ip: str, stream_name: typing.Optional[str]):
		if context.bot.use_vban:
			config.set_config("VBAN", "incoming_ip", new_ip)
			if stream_name is not None:
				config.set_config("VBAN", "stream_name", stream_name)
			context.bot.reset_stream()

			# str output_name
			output_name = stream_name
			if output_name is None:
				output_name = config.get_config_string("VBAN", "stream_name")
			
			if context.bot.voice is not None:
				await context.send("Audio stream reset: now listening to {} on stream \"{}\"".format(new_ip, output_name))
			else:
				await context.send("Stream IP is now {}, with stream \"{}\"".format(new_ip, output_name))
		else:
			await context.send("Not running in VBAN mode.")

	@commands.command(brief="Shows roles with command permission.", description="Returns a list of roles that can issue commands to the bot.")
	async def roles(self, context):
		print("Whitelist requested.")

		# List[str] allowed_roles
		allowed_roles = config.get_config_str_list("Commands", "role_whitelist")
		# str message
		message = "Command role whitelist:"

		for role in allowed_roles:
			message = message + "\n" + role

		await context.send(message)

	@commands.command(brief="Gives role bot command rights.", description="Adds the given role name to the command whitelist.")
	async def add_role(self, context, *split_role_name):
		# str role_name
		role_name = " ".join(split_role_name)
		if config.config_list_add("Commands", "role_whitelist", role_name):
			await context.send("Role \"{}\" added to whitelist.".format(role_name))
		else:
			await context.send("Error adding role \"{}\" to whitelist.  It may already be present.".format(role_name))

	@commands.command(brief="Revokes role bot command rights.", description="Removes the given role name from the command whitelist.")
	async def remove_role(self, context, *split_role_name):
		# str role_name
		role_name = " ".join(split_role_name)
		if config.config_list_remove("Commands", "role_whitelist", role_name):
			await context.send("Role \"{}\" removed from whitelist.".format(role_name))
		else:
			await context.send("Error removing role \"{}\" from whitelist.  It may not have been there to begin with.".format(role_name))

# ----------------
# Chat commands
# ----------------
class ChatCog(commands.Cog, name="Chat Commands"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.command(brief="Sends a message at a specific time.", description="Sends a message to the specified channel at a specified time and date, using the set time zone.  An at-here is automatically applied.")
	async def schedule_post(self, context, channel: str, time: str, date: str, *split_message):
		if not channel.startswith("<#") or not channel.endswith(">"):
			await context.send("Error: Please use the \"#\" prefix with the channel name to generate a channel link.")
			return
		# discord.Guild current_server
		current_server = context.guild
		if current_server is None:
			await context.send("Error: This command cannot be invoked outside of a server.")
			return
		# int target_channel_id
		target_channel_id = int(channel[2:-1])
		# str message
		message = "@here " + " ".join(split_message)
		try:
			# determine how long in the future to post the message
			# datetime.datetime post_datetime
			post_datetime = config.parse_datetime(date, time).replace(tzinfo=zoneinfo.ZoneInfo(config.get_config_string("Time", "timezone")))
			# str post_datetime_str
			post_datetime_str = post_datetime.strftime("%a %d %b %Y, %I:%M%p")
			# datetime.datetime utc_now
			utc_now = datetime.datetime.now(datetime.timezone.utc)
			# datetime.timedelta delta_time
			delta_time = post_datetime - utc_now
			# really don't care about sub-second time resolution here
			delta_time.microseconds = 0
			# int delta_sec
			delta_sec = delta_time.total_seconds()
			if delta_sec < 0:
				await context.send("Error: The specified time ({}) is in the past!".format(post_datetime_str))
			else:
				context.bot.queue_message(context.guild.id, target_channel_id, message, delta_sec)
				await context.send("Sending message to channel {} at {} ({} from now).".format(channel, post_datetime_str, str(delta_time)))
		except ValueError:
			await context.send("Error: Invalid date/time format!")
		except Exception as e:
			await context.send("Error: {}".format(e))

	@commands.command(brief="Sets the bot's time zone.", description="Uses the given timezone key to set the timezone that the bot uses for time-based functionality.")
	async def set_time_zone(self, context, time_zone_key: str):
		if time_zone_key not in config.valid_time_zones:
			await context.send("Error: Invalid time zone specificed.  Please use the `list_time_zones` command to search for your intended time zone.")
			return
		current_time_zone = config.get_config_string("Time", "timezone")
		if current_time_zone is not time_zone_key:
			await context.send("The time zone is already set to {}".format(time_zone_key))
		else:
			config.set_config("Time", "timezone", time_zone_key)
			await context.send("The time zone is now set to {}".format(time_zone_key))

	@commands.command(brief="Lists available time zones.", description="Provides the list of known time zones, optionally filtered by a search string.")
	async def list_time_zones(self, context, search_substr: typing.Optional[str]):
		time_zones = config.valid_time_zones
		if time_zones is None or len(time_zones) == 0:
			await context.send("Error: Time zone data unavailable!")
		else:
			if search_substr is not None:
				time_zones = {x for x in time_zones if search_substr in x}
			send_str = "```\n"
			for zone in time_zones:
				send_str = send_str + str(zone) + "\n"
			send_str = send_str + "```"
			await context.send(send_str)

# ----------------
# Secret roll commands
# ----------------

class SecretRollCog(commands.Cog, name="Secret Roll Commands"):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	@commands.command(brief="Set or view party level.", description="Set or view the party's level")
	async def party_level(self, context, level: typing.Optional[int]):
		if level is not None:
			if sroll.set_level(level):
				await context.send("Party is now level {}.".format(level))
			else:
				await context.send("Error: Level must be in range [1,20].")
		else:
			await context.send("The party is level {}.".format(sroll.party["level"]))

	@commands.command(brief="Inspect player character data.", description="Presents the given character's data as a JSON object.")
	async def inspect_pc(self, context, pc_name: str):
		stat_block: str = sroll.inspect_pc(pc_name)
		if stat_block != "":
			await context.send(stat_block)
		else:
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))

	@commands.command(brief="Adds a new player character.", description="Adds a new character to the players' party.  Names cannot contain spaces, so please use first names only.  A starting level may be specified, but it defaults to 1.")
	async def add_pc(self, context, pc_name: str):
		if sroll.add_pc(pc_name):
			await context.send("Player character {} added to party.".format(pc_name.capitalize()))
		else:
			await context.send("Error: Party already contains a character with name \"{}\"".format(pc_name.capitalize()))

	@commands.command(brief="Removes a player character.", description="Removes a character from the players' party.  This completely removes all data for that character, and the operation cannot be undone.")
	async def remove_pc(self, context, pc_name:str):
		if sroll.remove_pc(pc_name):
			await context.send("Player character {} has been deleted.".format(pc_name.capitalize()))
		else:
			await context.send("Error: {} was not part of the party to begin with.".format(pc_name.capitalize()))

	@commands.command(brief="Sets an ability modifier for a character.", description="Sets the given ability modifier to the given value for the given character.")
	async def set_ability_modifier(self, context, pc_name: str, ability_name: str, modifier: int):
		if not sroll.check_party_member(pc_name):
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))
		elif sroll.set_ability_mod(pc_name, ability_name, modifier):
			await context.send("{}'s {} modifier has been set to {}".format(pc_name.capitalize(), ability_name.upper(), modifier))
		else:
			await context.send("Error: Invalid ability.")

	@commands.command(brief="Sets a PC's proficiency in a save/skill.", description="Change the proficiency of a PC's save/skill with the given name (plus Perception).")
	async def set_prof(self, context, pc_name: str, check_name: str, proficiency: str):
		if not sroll.check_party_member(pc_name):
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))
		elif sroll.set_proficiency(pc_name, check_name, proficiency):
			prof_enum: sroll.Proficiency = sroll.convert_proficiency(proficiency)
			await context.send("{}'s {} proficiency set to {}".format(pc_name.capitalize(), check_name.capitalize(), prof_enum.name))
		else:
			await context.send("Error: Unknown skill/save or unknown proficiency.")

	@commands.command(brief="Sets a PC's bonus in a save/skill.", description="Changes the character's bonus of the given type for a skill/save.")
	async def set_bonus(self, context, pc_name: str, check_name: str, bonus_type: str, bonus: int):
		if not sroll.check_party_member(pc_name):
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))
		elif sroll.set_bonus(pc_name, check_name, bonus_type, bonus):
			await context.send("{}'s {} bonus for {} is now {}".format(pc_name.capitalize(), bonus_type.lower(), check_name.capitalize(), bonus))
		else:
			await context.send("Error: Invalid skill/save or invalid bonus type.")

	@commands.command(brief="Add a feat to a PC.", description="Adds the specified feat to the character.")
	async def add_feat(self, context, pc_name: str, *split_feat_name):
		feat_name: str = " ".join(split_feat_name).lower()
		if not sroll.check_party_member(pc_name):
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))
		elif sroll.set_feat(pc_name, feat_name, True):
			await context.send("{} now has the feat {}.".format(pc_name.capitalize(), string.capwords(feat_name)))
		else:
			await context.send("{} already has the feat {}.".format(pc_name.capitalize(), string.capwords(feat_name)))

	@commands.command(brief="Removes a feat from a PC.", description="Removes the specified feat from the character.")
	async def remove_feat(self, context, pc_name: str, *split_feat_name):
		feat_name: str = " ".join(split_feat_name).lower()
		if not sroll.check_party_member(pc_name):
			await context.send("Error: {} is not in the party.".format(pc_name.capitalize()))
		elif sroll.set_feat(pc_name, feat_name, False):
			await context.send("{} no longer has the feat {}.".format(pc_name.capitalize(), string.capwords(feat_name)))
		else:
			await context.send("{} did not have the feat {}.".format(pc_name.capitalize(), string.capwords(feat_name)))

	@commands.command(brief="Rolls a secret check and displays the results.", description="Rolls the specified secret check against the entire party and presents a detailed breakdown of the results of that roll.")
	async def roll(self, context, modifier: int, *split_action_name):
		action_name: str = " ".join(split_action_name)
		action_name = action_name.lower()
		deletion_time: float = config.get_config_float("Rolls", "result_message_timeout")

		result_str: str = ""
		if action_name == "lie":
			result_str = sroll.activity_lie(modifier)
		elif action_name == "sneak":
			result_str = sroll.activity_sneak(modifier)
		elif action_name == "hide":
			result_str = sroll.activity_hide(modifier)
		elif action_name == "impersonate":
			result_str = sroll.activity_impersonate(modifier)
		elif action_name == "conceal an object":
			result_str = sroll.activity_conceal(modifier)
		else:
			await context.send("Error: unsupported action \"{}\".".format(action_name), delete_after=deletion_time)

		if result_str != "":
			await context.send(result_str + "\n\n**Note** These results do not account for temporary bonuses.  Temporary bonuses may influence relevant DCs.", delete_after=deletion_time)
		await context.message.delete(delay=deletion_time)

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
async def add_commands(bot):
	bot.add_check(no_dms)
	bot.add_check(role_whitelist)

	await bot.add_cog(VoiceCog(bot))
	await bot.add_cog(ChatCog(bot))
	await bot.add_cog(SecretRollCog(bot))
