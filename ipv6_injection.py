import discord
from discord.voice_state import VoiceConnectionState, ConnectionFlowState
from discord.gateway import DiscordVoiceWebSocket
import logging
import config
import asyncio
import struct
import threading
import concurrent.futures
import socket

from typing import Tuple, Dict, Any, List

_log = logging.getLogger(__name__)

class IPv6VoiceClient(discord.VoiceClient):
	def create_connection_state(self) -> VoiceConnectionState:
		_log.debug('Creating IPv6 connection state')
		return IPv6VoiceConnectionState(self)

class IPv6VoiceConnectionState(VoiceConnectionState):
	async def _connect_websocket(self, resume: bool) -> DiscordVoiceWebSocket:
		# the following is a copy-pasta of VoiceConnectionState._connect_websocket(),
		# but replacing the voice web socket class
		_log.debug('Connecting IPv6 websocket')
		ws = await IPv6VoiceWebSocket.from_connection_state(self, resume=resume, hook=self.hook)
		self.state = ConnectionFlowState.websocket_connected
		return ws
		
	def _create_socket(self) -> None:
		# the following is a copy-pasta of VoiceConnectionState._create_socket(),
		# but making the socket IPv6
		self.socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
		self.socket.setblocking(False)
		self._socket_reader.resume()
		
class IPv6VoiceWebSocket(DiscordVoiceWebSocket):
	async def initial_connection(self, data: Dict[str, Any]) -> None:
		# need to translate the IPv4 address Discord sends to us to an IPv6 address for use
		# with our socket.  per NAT64 standards, we'll format it with the prefix "64:ff9b"
		# and then fill the bottom 32 "bits" with the IPv4 address as hex
		ipv4: str = data['ip']
		_log.debug('Need to translate IPv4 address {} to IPv6'.format(ipv4))
		split_ipv4: List[str] = ipv4.split('.')
		split_ipv4_hex: List[str] = [hex(int(ip_byte))[2:] for ip_byte in split_ipv4]
		ipv6: str = '64:ff9b::' + split_ipv4_hex[0] + split_ipv4_hex[1] + ':' + split_ipv4_hex[2] + split_ipv4_hex[3]
		_log.debug('Translated address to {}'.format(ipv6))
		data['ip'] = ipv6
		await super().initial_connection(data)

	async def discover_ip(self) -> Tuple[str, int]:
		if not config.get_config_bool("System", "ipv6"):
			return super().discover_ip()
		else:
			# the following is basically a copy-pasta of DiscordVoiceWebSocket.discover_ip(),
			# but accounting for IPv6
			state = self._connection
			packet = bytearray(74)
			struct.pack_into('>H', packet, 0, 1)  # 1 = Send
			struct.pack_into('>H', packet, 2, 70)  # 70 = Length
			struct.pack_into('>I', packet, 4, state.ssrc)

			_log.debug('Sending ipv6 discovery packet')
			await self.loop.sock_sendall(state.socket, packet)

			fut: asyncio.Future[bytes] = self.loop.create_future()

			def get_ip_packet(data: bytes):
				_log.debug('IPv6 discovery response packet data (length {}):\n{}'.format(len(data), str(data)))
				if data[1] == 0x02 and len(data) == 74:
					self.loop.call_soon_threadsafe(fut.set_result, data)

			_log.debug('Waiting for ipv6 discovery packet response')
			fut.add_done_callback(lambda f: state.remove_socket_listener(get_ip_packet))
			state.add_socket_listener(get_ip_packet)
			recv = await fut

			_log.debug('Received ipv6 discovery packet: %s', recv)

			# the ip is ascii starting at the 8th byte and ending at the first null
			ip_start = 8
			ip_end = recv.index(0, ip_start)
			ip = recv[ip_start:ip_end].decode('ascii')

			port = struct.unpack_from('>H', recv, len(recv) - 2)[0]
			_log.debug('detected ip: %s port: %s', ip, port)

			return ip, port