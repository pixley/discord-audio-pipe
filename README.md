# discord-audio-pipe

This is forked from https://github.com/QiCuiHub/discord-audio-pipe.

Program to send stereo audio (microphone, stereo mix, virtual audio cable, etc) into a Discord bot.  This fork is specifically adapted to work with the Syrinscape Online Player.

## Upcoming Features
This fork intends to extend the functionality of the original by adding the following:

* Detection as to whether the Syrinscape Online Player is running on the host machine.
* Accept text commands from Discord to change settings.
  * Connect to voice channel
  * Disconnect from voice channel
  * Set output volume
  * Query audio devices
  * Change audio device

None of these have been implemented yet.

## Setting up a Bot account
1. Follow the steps [**here**](https://discordpy.readthedocs.io/en/latest/discord.html) to setup and invite a discord bot
2. To link the program to your bot, create a file ``token.txt`` in the same directory as `main.pyw` and save the bot token inside

## Dependencies
Requires Python 3.5+. Install dependencies by running `pip3 install -r requirements.txt`

In some cases PortAudio and xcb libraries may be missing on linux. On Ubuntu they can be installed with
```
    $ sudo apt-get install libportaudio2
    $ sudo apt-get install libxcb-xinerama0
```
macOS requires PortAudio and Opus libraries
```
    $ brew install portaudio --HEAD
    $ brew install opus
```

## CLI
Running `main.pyw` without any arguments will start the graphical interface. Alternatively, discord-audio-pipe can be run from the command line and contains some tools to query system audio devices and accessible channels.
```
usage: main.pyw [-h] [-t TOKEN] [-v] [-c CHANNEL] [-d DEVICE] [-D] [-C]

Discord Audio Pipe

optional arguments:
  -h, --help            show this help message and exit
  -t TOKEN, --token TOKEN
                        The token for the bot
  -v, --verbose         Enable verbose logging

Command Line Mode:
  -c CHANNEL, --channel CHANNEL
                        The channel to connect to as an id
  -d DEVICE, --device DEVICE
                        The device to listen from as an index

Queries:
  -D, --devices         Query compatible audio devices
  -C, --channels        Query servers and channels (requires token)
```
