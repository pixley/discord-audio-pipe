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

# params: Discord.ext.commands.Context context
@commands.command()
async def help(context):
    # Set[Discord.ext.commands.Command] registered_commands
    registered_commands = context.bot.commands
    # String command_list
    command_list = "This bot accepts the following commands:"

    for command in registered_commands:
        command_list = command_list + "\n" + command.name

    await context.send(command_list)

# params: Discord.ext.commands.Context context, List[String] split_channel_name
@commands.command()
async def join(context, *split_channel_name):
    # int channel_id
    channel_id = 0
    # String channel_name
    channel_name = ""

    if split_channel_name is None:
        # Discord.Member author
        author = Context.author
        # Discord.VoiceState author_voice
        author_voice = author.voice
        if author_voice is not None:
            # Discord.VoiceChannel channel
            channel = author_voice.channel
            if channel.type == discord.ChannelType.voice:
                channel_id = channel.id
                channel_name = channel.name
    else:
        # String space_str
        space_str = " "
        channel_name = space_str.join(split_channel_name)
        # Discord.Guild server
        server = context.guild
        # List[Discord.VoiceChannel] channels
        channels = server.voice_channels
        for channel in channels:
            if channel.name == joined_channel_name:
                channel_id = channel.id
    
    if channel_id == 0:
        print("Error: User wasn't in a voice channel and did not provide the name of one.")
        await context.send("Error: User must be in a voice channel or specify a voice channel's name when calling !join.")
    else:
        try:
            print("Joining channel...")
            # discord.VoiceChannel channel
            channel = context.bot.get_channel(channel_id)

            context.bot.join_voice_channel(channel)

            print(f"Playing audio in {channel.name}")
            await context.send("Joined channel {}.".format(channel.name))
        except Exception:
            logging.exception("Error on channel join")
            await context.send("Error joining channel {}.".format(channel_name))

# params: Discord.ext.commands.Context context
@commands.command()
async def leave(context):
    # boolean success
    success = False
    # Discord.VoiceChannel channels
    channel = get_current_voice_channel(context)
    if channel is not None:
        await channel.disconnect()
        context.bot.clear_voice()

        print(f"Left channel {channel.name}")
        await context.send("Left channel {}.".format(channel.name))
    else:
        print("Error: Not in voice channel")
        await context.send("Error: Bot was not in a voice channel on this server.")

# params: Discord.ext.commands.Context context, int volume
@commands.command()
async def volume(context, vol: typing.Optional[int]):
    if vol is None:
        # Respond with current volume.
        # int cur_volume
        cur_volume = int(config.get_config_float("Audio", "volume") * 100.0)
        print("Current volume requested")
        await context.send("Volume is currently set to {}.".format(cur_volume))
    float_vol = float(int(vol)) / 100.0
    if context.bot.change_volume(vol):
        print("Volume changed")
        await context.send("Volume changed to {}".format(vol))
    else:
        print("Error: bad volume value")
        await context.send("Error: !volume accepts integer values from 0 to 200.")

# params: Discord.ext.commands.Context context
@commands.command()
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
@commands.command()
async def set_device(context, device_id):
    if context.bot.set_device(device_id):
        await context.send("Now playing from device {}".format(device_id))
    else:
        await context.send("Error: !set_device requires a valid device id.  Call !devices for a list of valid devices.")

# params: Discord.ext.commands.Context context
@commands.command()
async def status(context):
    # present voice connection status, current audio device, and watched process status
    print("Status requested")

    # String message
    message = "Current Status:"

    # Find current voice channel
    # Discord.VoiceChannel channel
    channel = get_current_voice_channel(context)
    if channel is not None:
        message = message + "\nConnected to voice channel {}".format(channel.name)
    else:
        message = message + "\nNot currently connected to a voice channel."

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
            message = message + "\nProcess {} is running.".format(process_name)
        else:
            message = message + "\nNo running process named {}".format(process_name)

    await context.send(message)

#params: Discord.ext.commands.Context context, String process_name
@commands.command()
async def watch(context, process_name):
    print("Watched process changed to {}".format(process_name))
    config.set_config("System", "watched_process_name", process_name)
    if process_name is None:
        await context.send("Watched process has been cleared.")
    else:
        # String message
        message = "Now watching process {}.".format(process_name)
        if (check_process(process_name)):
            message = message + "  It is active."
        else:
            message = message + "  It is not active."
        await context.send(message)

# ----------------
# End bot commands
# ----------------

# params: Discord.ext.commands.Context context
# return Discord.VoiceChannel
def get_current_voice_channel(context):
    # String cur_channel
    cur_channel = ""
    # List[Discord.VoiceChannel] channels
    for channel in channels:
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
    bot.add_command(help)
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
        print("Connecting...")
        await bot.wait_until_ready()
        print(f"Logged in as {bot.user.name}")

    except Exception:
        logging.exception("Error on cli connect")
        sys.exit(1)
