import socket
import logging
from io import BytesIO
from hashlib import sha1

from tornado import ioloop, iostream
from tornado.gen import engine, Task

stream_order = "little"

class CAPS(object):
	LONG_PASSWORD =   1   # new more secure passwords 
	FOUND_ROWS = 2    #Found instead of affected rows
	LONG_FLAG = 4    #Get all column flags */
	CONNECT_WITH_DB = 8  # One can specify db on connect */
	NO_SCHEMA = 16  #  /* Don't allow database.table.column */
	COMPRESS =       32    # Can use compression protocol */
	ODBC     =   64    # Odbc client */
	LOCAL_FILES =   128    # Can use LOAD DATA LOCAL */
	IGNORE_SPACE=    256    # Ignore spaces before '(' */
	PROTOCOL_41 =   512    # New 4.1 protocol */
	INTERACTIVE =   1024    # This is an interactive client */
	SSL         =     2048   #Switch to SSL after handshake */
	IGNORE_SIGPIPE =  4096    # IGNORE sigpipes */
	TRANSACTIONS  =  8192    # Client knows about transactions */
	RESERVED     =    16384   # Old flag for 4.1 protocol  */
	SECURE_CONNECTION = 32768  # New 4.1 authentication */
	MULTI_STATEMENTS= 65536   # Enable/disable multi-stmt support */
	MULTI_RESULTS   = 131072  # Enable/disable multi-results */

	__ALL__ = {LONG_PASSWORD: 'CLIENT_LONG_PASSWORD', 
			   FOUND_ROWS: 'CLIENT_FOUND_ROWS',
			   LONG_FLAG: 'CLIENT_LONG_FLAG',
			   CONNECT_WITH_DB: 'CLIENT_CONNECT_WITH_DB',
			   NO_SCHEMA: 'CLIENT_NO_SCHEMA',
			   COMPRESS: 'CLIENT_COMPRESS',
			   ODBC: 'CLIENT_ODBC',
			   LOCAL_FILES: 'CLIENT_LOCAL_FILES',
			   IGNORE_SPACE: 'CLIENT_IGNORE_SPACE',
			   PROTOCOL_41: 'CLIENT_PROTOCOL_41',
			   INTERACTIVE: 'CLIENT_INTERACTIVE',
			   SSL: 'CLIENT_SSL',
			   IGNORE_SIGPIPE: 'CLIENT_IGNORE_SIGPIPE',
			   TRANSACTIONS: 'CLIENT_TRANSACTIONS',
			   RESERVED: 'CLIENT_RESERVED',
			   SECURE_CONNECTION: 'CLIENT_SECURE_CONNECTION',
			   MULTI_STATEMENTS: 'CLIENT_MULTI_STATEMENTS',
			   MULTI_RESULTS: 'CLIENT_MULTI_RESULTS'}

	@classmethod
	def dbg(cls, caps):
		for value, name in cls.__ALL__.items():
			if caps & value:
				print(name)

class COMMAND:
	QUIT = 0x01
	INITDB = 0x02
	QUERY = 0x03
	LIST = 0x04
	PING = 0x0e

charset_map = {}
charset_map["big5"] = 1
charset_map["dec8"] = 3
charset_map["cp850"] = 4
charset_map["hp8"] = 6
charset_map["koi8r"] = 7
charset_map["latin1"] = 8
charset_map["latin1"] = 8
charset_map["latin2"] = 9
charset_map["swe7"] = 10
charset_map["ascii"] = 11
charset_map["ujis"] = 12
charset_map["sjis"] = 13
charset_map["hebrew"] = 16
charset_map["tis620"] = 18
charset_map["euckr"] = 19
charset_map["koi8u"] = 22
charset_map["gb2312"] = 24
charset_map["greek"] = 25
charset_map["cp1250"] = 26
charset_map["gbk"] = 28
charset_map["latin5"] = 30
charset_map["armscii8"] = 32
charset_map["utf8"] = 33
charset_map["utf8"] = 33
charset_map["ucs2"] = 35
charset_map["cp866"] = 36
charset_map["keybcs2"] = 37
charset_map["macce"] = 38
charset_map["macroman"] = 39
charset_map["cp852"] = 40
charset_map["latin7"] = 41
charset_map["cp1251"] = 51
charset_map["cp1256"] = 57
charset_map["cp1257"] = 59
charset_map["binary"] = 63
charset_map["geostd8"] = 92
charset_map["cp932"] = 95
charset_map["eucjpms"] = 97

def create_scramble_buff():
	import random
	return ''.join([chr(random.randint(0, 255)) for _ in xrange(20)])

def _scramble(passwd, seed):
	"""Scramble a password ready to send to MySQL"""
	import struct
	hash4 = None
	hash1 = sha1(passwd).digest()
	hash2 = sha1(hash1).digest() # Password as found in mysql.user()
	hash3 = sha1(seed + hash2).digest()
	xored = [ h1 ^ h3 for (h1,h3) in zip(hash1, hash3) ]
	hash4 = struct.pack('20B', *xored)
	
	return hash4

class ClientError(Exception):
	@classmethod
	def from_error_packet(cls, io, skip = 8):
		io.read(skip)
		return cls(io.read().decode())

class ClientLoginError(ClientError): pass
class ClientCommandError(ClientError): pass
class ClientProgrammingError(ClientError): pass
class UnsupportVersion(Exception): pass

def read_packet(stream, callback=None):
	def _on_head(data):
		length = int.from_bytes(data[:3], stream_order)
		stream.read_bytes(length, callback)
	stream.read_bytes(4, _on_head)

class Stream(BytesIO):
	def read_until(self, end):
		pos = self.tell()
		index = self.getvalue().find(end, pos)
		if index == -1:
			raise RuntimeError("Can't find the end symbol")
		val = self.read(index - pos)
		self.read(len(end))
		return val

	def read_int(self, size):
		return int.from_bytes(self.read(size), stream_order)

	def write_int(self, n, size = 1):
		self.write(n.to_bytes(size, stream_order))

	def pack(self, packet_number):
		buf = self.getvalue()
		length = len(buf)
		return length.to_bytes(3, stream_order) + packet_number.to_bytes(1, stream_order) + buf

	def eof(self):
		return self.tell() == len(self.getvalue())

class Connection(object):
	STATE_ERROR = -1
	STATE_INIT = 0
	STATE_CONNECTING = 1
	STATE_CONNECTED = 2
	STATE_CLOSING = 3
	STATE_CLOSED = 4

	def __init__(self):
		self.state = self.STATE_INIT

	@engine
	def connect(self, host = "localhost", port = 3306, user = "", password = "", 
			db = "", autocommit = None, charset = "utf8"):

		assert type(host) == str, "make sure host is a string"

		if host[0] == '/': #assume unix domain socket
			addr = host
		elif ':' in host:
			host, port = host.split(':')
			port = int(port)
			addr = (host, port)
		else:
			addr = (host, port)
		self.autocommit = autocommit

		assert self.state == self.STATE_INIT, "make sure connection is not already connected or closed"

		self.state = self.STATE_CONNECTING
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.stream = iostream.IOStream(sock)

		try:
			yield Task(self.stream.connect, addr)
			packet = yield Task(read_packet, self.stream)
			yield Task(self.stream.write, self.prepare_handshake(packet, db, charset))
			packet = yield Task(read_packet, self.stream)
			self.check_handshake(packet)
			self.state = self.STATE_CONNECTED
		except ClientLoginError:
			self.state = self.STATE_INIT
			logging.error("Exception on login: ", exc_info=True)
		except Exception:
			self.state = self.STATE_ERROR
			logging.error("Exception on login: ", exc_info=True)

	@engine
	def command(self, cmd, cmd_text):
		assert type(cmd_text) == str
		assert self.state == self.STATE_CONNECTED
		assert self._incommand, "overlapped commands not supported"
		assert self.current_resultset, "overlapped commands not supported"
		cmd_text = cmd_text.encode(self.charset)
		output = Stream()
		output.write_int(1, cmd)
		output.write(cmd_text)
		yield Task(self.stream.write, output.pack(0))
		print((yield Task(read_packet, self.stream)))

	def prepare_handshake(self, packet, user, password, db, charset):
		input = Stream(packet)
		self.protocol_version = input.read_int(1)
		if self.protocol_version == 0xff:
			raise ClientLoginError.from_error_packet(input, skip = 2)
		elif self.protocol_version == 10:
			pass
		else:
			raise UnsupportVersion("unexpected protocol version %02x" % self.protocol_version)

		self.server_version = input.read_until(b"\0")
		self.thread_id = input.read(4)
		scramble_buff = input.read(8)
		input.read(1)
		server_caps = input.read_int(2)
		CAPS.dbg(server_caps)

		if not server_caps & CAPS.PROTOCOL_41:
			raise UnsupportVersion("<4.1 auth not supported")

		server_language = input.read_int(1)
		server_status = input.read_int(2)
		input.read(13)
		if not input.eof():
			scramble_buff += input.read_until(b'\0')
		else:
			raise UnsupportVersion("<4.1 auth not supported")

		client_caps = server_caps

		#turn off compression and ssl
		client_caps &= ~CAPS.COMPRESS
		client_caps &= ~CAPS.NO_SCHEMA
		client_caps &= ~CAPS.SSL

		if not server_caps & CAPS.CONNECT_WITH_DB and db:
			raise UnsupportVersion("initial db given but not supported by server")
		if not db:
			client_caps &= ~CAPS.CONNECT_WITH_DB

		output = Stream()
		output.write_int(client_caps, 4)
		output.write_int(1 << 24, 4)

		output.write_int(charset_map[charset.replace("-", "")])
		self.charset = charset

		output.write(b'\0' * 23)
		output.write(user.encode(charset) + b'\0')

		#output.write(b'\0')
		output.write_int(20)
		output.write(_scramble(password.encode(charset), scramble_buff))
		output.write(b'\0')

		return output.pack(1)

	def check_handshake(self, packet):
		input = Stream(packet)
		indicator = input.read_int(1)
		if indicator == 0xff:
			raise ClientLoginError.from_error_packet(input)
		elif indicator == 0xfe:
			raise UnsupportVersion("old password handshake not implemented")

c = Connection()
c.connect(user="test", password="test")
print("connected")
c.command(COMMAND.QUERY, "use test")
ioloop.IOLoop.instance().start()

#test()

