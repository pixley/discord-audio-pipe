import socket
import struct
import sounddevice as sd
import errno
import logging

class VBAN_Recv(object):
	"""docstring for VBAN_Recv"""
	def __init__(self, senderHost, streamName, port, outDeviceIndex, ipv6=True, verbose=False, stream=None):
		super(VBAN_Recv, self).__init__()
		self.streamName = streamName
		self.const_VBAN_SRList = [6000, 12000, 24000, 48000, 96000, 192000, 384000, 8000, 16000, 32000, 64000, 128000, 256000, 512000, 11025, 22050, 44100, 88200, 176400, 352800, 705600] 
		family = socket.AF_INET6 if ipv6 else socket.AF_INET
		self.any_sender = senderHost is None
		for addrInfoTuple in socket.getaddrinfo(senderHost, port, family=family, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP):
			# Break up the tuple
			famInfo, typeInfo, protoInfo, canonName, socketAddr = addrInfoTuple
			if self.any_sender:
				# socket.getaddrinfo() gives localhost for the ip address if the host is None, but
				# that's not what socket.bind() wants
				# stupid tuples and immutability...
				socketAddr = socketAddr[:0] + ("",) + socketAddr[1:]
			self.senderIp = socketAddr[0]	# The first element of the sockAddr tuple is the IP address under both IPv4 and IPv6
			try:
				self.sock = socket.socket(family, socket.SOCK_DGRAM) # UDP
				self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				self.sock.setsockopt(socket.SOL_IP, 15, 1) # optname 15 refers to IP_FREEBIND
				self.sock.bind(socketAddr)
			except Exception:
				printed_ip = self.senderIp
				if self.any_sender:
					printed_ip = "::/0" if ipv6 else "0.0.0.0/0"
				if ipv6:
					printed_ip = "[" + printed_ip + "]"
				logging.exception("Failed socket binding for {}:{}.".format(printed_ip, port))
				self.sock = None
				continue
			break
		if self.sock is None:
			raise RuntimeError("Could not initialize VBAN recv socket!")

		self.sock.setblocking(False)
		self.sampRate = 48000
		self.channels = 2
		self.outDeviceIndex=outDeviceIndex
		self.stream_magicString = ""
		self.stream_sampRate = 0
		self.stream_sampNum = 0
		self.stream_chanNum = 0
		self.stream_dataFormat = 0
		self.stream_streamName = ""
		self.stream_frameCounter = 0
		if stream is None:
			self.stream = sd.RawOutputStream(device=self.outDeviceIndex)
			self.stream.start()
		else:
			self.stream = stream
		self.rawPcm = None
		self.running = True
		self.verbose = verbose
		self.rawData = None
		self.subprotocol = 0
		logging.info("pyVBAN-Recv Started")
		logging.info("Hint: Remeber that pyVBAN only support's PCM 16bits")

	def _correctPyAudioStream(self):
		self.channels = self.stream_chanNum 
		self.sampRate = self.stream_sampRate
		self.stream.stop()
		self.stream = sd.RawOutputStream(device=self.outDeviceIndex)
		self.stream.start()

	def _cutAtNullByte(self,stri):
		return stri.decode('utf-8').split("\x00")[0]

	def _parseHeader(self,data):
		self.stream_magicString = data[0:4].decode('utf-8')
		sampRateIndex = data[4] & 0x1F
		self.subprotocol = (data[4] & 0xE0) >> 5
		self.stream_sampRate = self.const_VBAN_SRList[sampRateIndex]
		self.stream_sampNum = data[5] + 1
		self.stream_chanNum = data[6] + 1
		self.stream_dataFormat = data[7]
		self.stream_streamName = self._cutAtNullByte(b''.join(struct.unpack("cccccccccccccccc",data[8:24])))
		self.stream_frameCounter = struct.unpack("<L",data[24:28])[0]

	def runonce(self):
		if self.stream == None:
			logging.info("Quit has been called")
			return

		try:
			data, addr = self.sock.recvfrom(2048) # buffer size is normally 1436 bytes Max size for vban
			self.rawData = data
			self._parseHeader(data)
			if self.verbose:
				logging.info("R"+self.stream_magicString+" "+str(self.stream_sampRate)+"Hz "+str(self.stream_sampNum)+"samp "+str(self.stream_chanNum)+"chan Format:"+str(self.stream_dataFormat)+" Name:"+self.stream_streamName+" Frame:"+str(self.stream_frameCounter))
			self.rawPcm = data[28:]   #Header stops at 28
			if self.stream_magicString == "VBAN" and self.subprotocol == 0:
				if not self.stream_streamName == self.streamName:
					return
				if self.anySender or ( addr[0] != self.senderIp ):
					return
				if self.channels != self.stream_chanNum or self.sampRate != self.stream_sampRate:
					self._correctPyAudioStream()
				self.stream.write(self.rawPcm)

		except OSError as e:
			if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
				# we're not worried about a lack of data from the recvfrom() call
				if self.verbose:
					logging.info("No incoming data.")
				# however, we do want to signal that we've run out of data to receive
				raise IndexError()
			else:
				raise e

	def runforever(self):
		while self.running:
			self.runonce()
		self.quit()

	def quit(self):
		self.running = False
		self.stream.close()
		self.stream = None

class VBAN_Send(object):
	"""docstring for VBAN_Send"""
	def __init__(self, toHost, toPort, streamName, sampRate, inDeviceIndex, ipv6=True, verbose=False ):
		super(VBAN_Send, self).__init__()
		self.streamName = streamName
		family = socket.AF_INET6 if ipv6 else socket.AF_INET
		self.toPort = toPort
		# We only care about the first result
		for addrInfoTuple in socket.getaddrinfo(toHost, toPort, type=socket.SOCK_DGRAM, family=family, proto=socket.IPPROTO_UDP):
			# Break up the tuple
			famInfo, typeInfo, protoInfo, canonName, socketAddr = addrInfoTuple
			self.socketAddr = socketAddr
			self.toIp = socketAddr[0]	# The first element of the sockAddr tuple is the IP address under both IPv4 and IPv6
			try:
				self.sock = socket.socket(family, socket.SOCK_DGRAM) # UDP
				self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				self.sock.connect(socketAddr)
			except Exception as e:
				logging.info(e)
				self.sock = None
				continue
			break
		if self.sock is None:
			raise RuntimeError("Could not initialize VBAN recv socket!")

		self.sock.setblocking(False)
		self.const_VBAN_SR = [6000, 12000, 24000, 48000, 96000, 192000, 384000, 8000, 16000, 32000, 64000, 128000, 256000, 512000,11025, 22050, 44100, 88200, 176400, 352800, 705600]
		self.channels = sd.default.channels[0]
		if sampRate not in self.const_VBAN_SR:
			logging.info("SampRate not valid/compatible")
			return
		self.samprate = sampRate
		self.inDeviceIndex = inDeviceIndex
		self.chunkSize = 256
		self.stream = sd.RawInputStream(device=self.inDeviceIndex)
		self.stream.start()

		self.framecounter = 0
		self.running = True
		self.verbose = verbose
		self.rawPcm = None
		self.rawData = None

	def _constructFrame(self,pcmData):
		header  = b"VBAN" 
		header += bytes([self.const_VBAN_SR.index(self.samprate)])
		header += bytes([self.chunkSize-1])
		header += bytes([self.channels-1])
		header += b'\x01'  #VBAN_CODEC_PCM
		header += bytes(self.streamName + "\x00" * (16 - len(self.streamName)), 'utf-8')
		header += struct.pack("<L",self.framecounter)
		if self.verbose:
			logging.info("SVBAN "+str(self.samprate)+"Hz "+str(self.chunkSize)+"samp "+str(self.channels)+"chan Format:1 Name:"+self.streamName+" Frame:"+str(self.framecounter))
		return header+pcmData

	def runonce(self):
		self.framecounter += 1
		try:
			self.rawPcm = bytes(self.stream.read(self.chunkSize)[0])
			self.rawData = self._constructFrame(self.rawPcm)
			self.sock.sendto(self.rawData, self.socketAddr)
		except Exception as e:
			logging.exception()

	def runforever(self):
		while self.running:
			self.runonce()

	def quit(self):
		self.running = False
		self.stream.close()
		self.stream = None

class VBAN_SendText(object):
	"""docstring for VBAN_SendText"""
	def __init__(self, toIp, toPort,baudRate, streamName):
		super(VBAN_SendText, self).__init__()
		self.toIp = toIp
		self.toPort = toPort
		self.streamName = streamName
		self.baudRate = baudRate
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
		self.sock.connect((self.toIp,self.toPort))
		self.VBAN_BPSList = [0, 110, 150, 300, 600, 1200, 2400, 4800, 9600, 14400,19200, 31250, 38400, 57600, 115200, 128000, 230400, 250000, 256000, 460800,921600, 1000000, 1500000, 2000000, 3000000]
		self.framecounter = 0

	def _constructFrame(self,text):
		header  = b"VBAN" 
		header += bytes([int("0b01000000",2)  + self.VBAN_BPSList.index(self.baudRate)])
		header += b'\x00'
		header += b'\x00' #Channel indent 0 by default
		header += bytes([int("0b00010000",2)]) # UTF8
		header += bytes(self.streamName + "\x00" * (16 - len(self.streamName)), 'utf-8')
		header += struct.pack("<L",self.framecounter)
		return header+bytes(text, 'utf-8')

	def send(self,text):
		try:
			self.framecounter += 1
			self.rawData = self._constructFrame(text)
			self.sock.sendto(self.rawData, (self.toIp,self.toPort))
		except Exception as e:
			logging.info(e)