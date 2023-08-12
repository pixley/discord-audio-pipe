import logging

# error logging
error_formatter = logging.Formatter(
	fmt="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

error_handler = logging.FileHandler("DAP_errors.log", delay=True)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

base_logger = logging.getLogger()
base_logger.addHandler(error_handler)

from ctypes.util import find_library
import sys
import cli
import sound
import bot
import config
import asyncio
import discord
import argparse
from discord.ext import commands
import secret_rolls as sroll

# commandline args
parser = argparse.ArgumentParser(description="Discord Audio Pipe")

parser.add_argument(
	"-t",
	"--token",
	dest="token",
	action="store",
	default=None,
	help="The token for the bot",
)

parser.add_argument(
	"-v",
	"--verbose",
	dest="verbose",
	action="store_true",
	help="Enable verbose logging",
)

args = parser.parse_args()

# verbose logs
if args.verbose:
	debug_formatter = logging.Formatter(
		fmt="%(asctime)s:%(levelname)s:%(name)s: %(message)s"
	)

	debug_handler = logging.FileHandler(
		filename="discord.log", encoding="utf-8", mode="w"
	)
	debug_handler.setFormatter(debug_formatter)

	debug_logger = logging.getLogger("discord")
	debug_logger.setLevel(logging.DEBUG)
	debug_logger.addHandler(debug_handler)

# main
async def main(bot):
	try:
		# check for token
		# String token
		token = args.token
		if token is None:
			# File token_file
			token_file = open("token.txt", "r")
			token = token_file.read()
			if token == "":
				print("Error: no token specified.")
				return
			token_file.close()

		await cli.add_commands(bot)

		# log in and connect
		print("Logging into Discord...")
		await bot.start(token)

	except FileNotFoundError:
		print("No Token Provided")

	except discord.errors.LoginFailure:
		print("Login Failed: Please check if the token is correct")

	except Exception:
		logging.exception("Error on main")


# run program

config.setup_config("settings.cfg")
sroll.setup()
# discord.Intents all_intents
all_intents = discord.Intents.all()
# bot.Dap_Bot bot
bot = bot.Dap_Bot('!', intents=all_intents)
bot.case_insensitive = True

@bot.event
async def on_ready():
	print("Logged in to Discord as {}!".format(bot.user.name))

loop = asyncio.get_event_loop_policy().get_event_loop()

#apply config
bot.apply_config()

if not discord.opus.is_loaded():
	print("Need to load Opus libraries...")
	
	opus_lib_str = find_library("opus")
	if opus_lib_str is None:
		# fallback suggested by discord.py's docs
		opus_lib_str = "libopus.so.1"
		print("Could not find libopus - using fallback")
	else:
		print("libopus found: {}".format(opus_lib_str))
		
	print("Attempting to load Opus libraries...")
	try:
		discord.opus.load_opus(opus_lib_str)
		print("Opus libraries successfully loaded!")
	except:
		print("Could not load libopus...  Audio unlikely to function.")
else:
	print("Opus libraries loaded automatically!")

try:
	loop.run_until_complete(main(bot))
except KeyboardInterrupt:
	print("Received keyboard interrupt!")
except Exception as e:
	print(e)
print("Exiting...")
loop.run_until_complete(bot.close())
# this sleep prevents a bugged exception on Windows
loop.run_until_complete(asyncio.sleep(1))
loop.close()
