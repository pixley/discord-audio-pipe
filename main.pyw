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

import sys
import cli
import sound
import bot
import config
import asyncio
import discord
import argparse
from discord.ext import commands

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

		asyncio.create_task(cli.connect(bot))

		# log in and connect
		await bot.start(token)

	except FileNotFoundError:
		print("No Token Provided")

	except discord.errors.LoginFailure:
		print("Login Failed: Please check if the token is correct")

	except Exception:
		logging.exception("Error on main")


# run program

config.setup_config()
# bot.Dap_Bot bot
bot = bot.Dap_Bot('!')
bot.case_insensitive = True

loop = asyncio.get_event_loop()

#apply config
bot.apply_config()

cli.add_commands(bot)

try:
	loop.run_until_complete(main(bot))
except KeyboardInterrupt:
	print("Exiting...")
	loop.run_until_complete(bot.close())
	# this sleep prevents a bugged exception on Windows
	loop.run_until_complete(asyncio.sleep(1))
	loop.close()
