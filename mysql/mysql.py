import socket
from tornado import ioloop, iostream
from tornado import stack_context

class Client(object):
	def __init__(self, host='localhost', port=3306, user='', passwd=''):
		self.host = host
		self.port = port
		self.user = user
		self.passwd = passwd

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.stream = iostream.IOStream(sock)

	def connect(self):
		self.stream.connect((self.host, self.port), self.on_connected)

	def on_connected(self):
		import pdb;pdb.set_trace()
		self.stream.read_bytes(4, stack_context.wrap(self.on_packet_header))

	def on_packet_header(self, data):
		length = data[0] + (data[1] << 8) + (data[2] << 8)
		self.stream.read_bytes(length, self.on_packet_body)
	
	def on_packet_body(self, data):
		pass

c = Client()
c.connect()
ioloop.IOLoop.instance().start()
