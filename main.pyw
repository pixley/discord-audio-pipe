import logging
import sys

# logging
error_formatter = logging.Formatter(
	fmt="%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

log_formatter = logging.Formatter(
	fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

print_formatter = logging.Formatter(
	fmt="[%(levelname)s] %(message)s"
)

error_handler = logging.FileHandler("DAP_errors.log", encoding="utf-8", delay=True)
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)

log_handler = logging.FileHandler("DAP.log", encoding="utf-8", delay=True)
# Not setting level means all messages go to log
log_handler.setFormatter(log_formatter)

print_handler = logging.StreamHandler(sys.stdout)
# Not setting level means all messages are printed
print_handler.setFormatter(print_formatter)

base_logger = logging.getLogger()
base_logger.addHandler(error_handler)
base_logger.addHandler(log_handler)
base_logger.addHandler(print_handler)

from ctypes.util import find_library
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
		filename="DAP_debug.log", encoding="utf-8", mode="w"
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
				logging.info("Error: no token specified.")
				return
			token_file.close()

		await cli.add_commands(bot)

		# log in and connect
		logging.info("Logging into Discord...")
		await bot.start(token)

	except FileNotFoundError:
		logging.info("No Token Provided")

	except discord.errors.LoginFailure:
		logging.info("Login Failed: Please check if the token is correct")

	except Exception as e:
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
	logging.info("Logged in to Discord as {}!".format(bot.user.name))

loop = asyncio.get_event_loop_policy().get_event_loop()

#apply config
bot.apply_config()

if not discord.opus.is_loaded():
	logging.info("Need to load Opus libraries...")
	
	opus_lib_str = find_library("opus")
	if opus_lib_str is None:
		# fallback suggested by discord.py's docs
		opus_lib_str = "libopus.so.1"
		logging.info("Could not find libopus - using fallback")
	else:
		logging.info("libopus found: {}".format(opus_lib_str))
		
	logging.info("Attempting to load Opus libraries...")
	try:
		discord.opus.load_opus(opus_lib_str)
		logging.info("Opus libraries successfully loaded!")
	except:
		logging.info("Could not load libopus...  Audio unlikely to function.")
else:
	logging.info("Opus libraries loaded automatically!")

try:
	loop.run_until_complete(main(bot))
except KeyboardInterrupt:
	logging.info("Received keyboard interrupt!")
except Exception as e:
	logging.info(e)
logging.info("Exiting...")
loop.run_until_complete(bot.close())
# this sleep prevents a bugged exception on Windows
loop.run_until_complete(asyncio.sleep(1))
loop.close()
