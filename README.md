# discord-audio-pipe

This is forked from https://github.com/QiCuiHub/discord-audio-pipe.  Makes use of a modified version of [pyVBAN](https://github.com/TheStaticTurtle/pyVBAN).

Program to send stereo audio (microphone, stereo mix, virtual audio cable, etc) into a Discord bot.

## Limitations
* This bot may be able to connect to multiple servers, but they cannot have independent control.
* This bot does not currently have the ability to be controlled only by certain roles, though this is planned.

## Setting Up a Bot Account
1. Follow the steps [**here**](https://discordpy.readthedocs.io/en/latest/discord.html) to setup and invite a discord bot
2. To link the program to your bot, create a file ``token.txt`` in the same directory as `main.pyw` and save the bot token inside

## Dependencies
Requires Python 3.8+. Install dependencies by running `pip3 install -r requirements.txt`

In some cases PortAudio, xcb, and ffmpeg libraries may be missing on linux. On Ubuntu, they can be installed with
```
    $ sudo apt-get install libportaudio2
    $ sudo apt-get install libxcb-xinerama0
    $ sudo apt-get install ffmpeg libavcodec-extra
```

## Chat Commands
Rather than configuring the bot via the command line, everything is configured using Discord chat.  See `cli.py` for commands and their implementations.  Additionally, when running the bot, you can call `!help`.