import sys
import sound
import discord
import logging
import config
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

    if channel_name is None:
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
            channel = bot.get_channel(channel_id)

            voice = await channel.connect()
            voice.play(discord.PCMAudio(bot.stream))

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
    # List[VoiceChannel] channels
    channels = context.bot.voice_clients
    for channel in channels:
        if channel.guild == context.guild:
            await channel.disconnect()

            print(f"Left channel {channel.name}")
            await context.send("Left channel {}.".format(channel.name))
            success = True
            break

    if not success:
        print("Error: Not in voice channel")
        await context.send("Error: Bot was not in a voice channel on this server.")

# params: Discord.ext.commands.Context context, int volume
@commands.command()
async def volume(context, vol: int):
    float_vol = vol / 100.0
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
    await context.send(sound.query_devices())

# params: Discord.ext.commands.Context context, int device_id
@commands.command()
async def set_device(context, device_id):
    if context.bot.set_device(device_id):
        await context.send("Now playing from device {}".format(device_id))
    else:
        await context.send("Error: !set_device requires a valid device id.  Call !devices for a list of valid devices.")


# ----------------
# End bot commands
# ----------------

# params: bot.Dap_Bot bot
def add_commands(bot):
    bot.add_command(help)
    bot.add_command(join)
    bot.add_command(leave)
    bot.add_command(volume)
    bot.add_command(devices)
    bot.add_command(set_device)

# params: bot.Dap_Bot bot
async def connect(bot):
    try:
        print("Connecting...")
        await bot.wait_until_ready()
        print(f"Logged in as {bot.user.name}")

    except Exception:
        logging.exception("Error on cli connect")
        sys.exit(1)
