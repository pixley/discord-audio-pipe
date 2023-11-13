import discord
from discord.voice_state import VoiceConnectionState
import logging
import config
import asyncio
import struct
import threading
import concurrent.futures

from typing import Tuple

_log = logging.getLogger(__name__)

class IPv6VoiceClient(discord.VoiceClient):
	def create_connection_state(self) -> VoiceConnectionState:
		return IPv6VoiceConnectionState(self)

class IPv6VoiceConnectionState(VoiceConnectionState):
	async def discover_ip(self) -> Tuple[str, int]:
		if not config.get_config_bool("System", "ipv6"):
			return super().discover_ip(self)
		else:
			# the following is basically a copy-pasta of VoiceConnectionState.discover_ip(),
			# but accounting for IPv6
			state = self._connection
			packet = bytearray(74)
			struct.pack_into('>H', packet, 0, 1)  # 1 = Send
			struct.pack_into('>H', packet, 2, 70)  # 70 = Length
			struct.pack_into('>I', packet, 4, state.ssrc)

			_log.debug('Sending ip discovery packet')
			await self.loop.sock_sendall(state.socket, packet)

			fut: asyncio.Future[bytes] = self.loop.create_future()

			def get_ip_packet(data: bytes):
				if data[1] == 0x02: # and len(data) == 74:
					_log.debug('Length of IPv6 discovery data: {}'.format(len(data)))
					self.loop.call_soon_threadsafe(fut.set_result, data)

			fut.add_done_callback(lambda f: state.remove_socket_listener(get_ip_packet))
			state.add_socket_listener(get_ip_packet)
			recv = await fut

			_log.debug('Received ip discovery packet: %s', recv)

			# the ip is ascii starting at the 8th byte and ending at the first null
			ip_start = 8
			ip_end = recv.index(0, ip_start)
			ip = recv[ip_start:ip_end].decode('ascii')

			port = struct.unpack_from('>H', recv, len(recv) - 2)[0]
			_log.debug('detected ip: %s port: %s', ip, port)

			return ip, port