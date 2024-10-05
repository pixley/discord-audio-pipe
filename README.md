# Pixley's discord-audio-pipe

This is forked from https://github.com/QiCuiHub/discord-audio-pipe.  Makes use of a modified version of [pyVBAN](https://github.com/TheStaticTurtle/pyVBAN).

Program to send stereo audio (microphone, stereo mix, virtual audio cable, etc) into a Discord bot.

## Features
* Two operating modes:
    * Direct transmission: Broadcast input from a local audio device.  Works best on user's local machine.
    * VBAN connection: In conjunction with the `vban_sender.pyw` applet, receive an audio feed from a user and broadcast it.  Works best on a dedicated server.
* Discord chat commands: The bot is set-and-forget.  Most configuration can be done via Discord chat commands.  For a list of commands, either check `cli.py` or run the bot and call `!help`.

## Limitations
* This bot might be able to connect to multiple servers, but they cannot have independent control.
* This bot does not currently have the ability to be controlled only by certain roles, though this is planned.

## Setting Up a Bot Account
1. Follow the steps [**here**](https://discordpy.readthedocs.io/en/latest/discord.html) to setup and invite a discord bot
2. To link the program to your bot, create a file ``token.txt`` in the same directory as `main.pyw` and save the bot token inside

## Dependencies
Requires Python 3.9+. Install dependencies by running `pip3 install -r requirements.txt`.  On newer Python versions and Linux distros, you may get an error about `externally-managed-environment`.  How you resolve this is unfortunately up to your particular needs for your machine.  Since I am the sole user of the VM on which I host my personal instance, I am comfortable with just running `pip install` with the `--break-system-packages` flag, but that is **not a recommendation**.

In some cases PortAudio, xcb, and ffmpeg libraries may be missing on linux. On Ubuntu, they can be installed with
```
    $ sudo apt install portaudio19-dev
    $ sudo apt install libxcb-xinerama0
    $ sudo apt install ffmpeg libavcodec-extra
```
