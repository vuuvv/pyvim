import sys
import time
import random
import re

import socket
from tornado import ioloop, iostream
from tornado import gen

def on_connect():
	print("hi")

@gen.engine
def connect(stream):
	import pdb;pdb.set_trace()
	yield gen.Task(stream.connect, ("www.facebook.com", 80))
	get_header(stream)

@gen.engine
def get_header(stream):
	yield gen.Task(stream.write, b"GET / HTTP/1.1\r\nHost: www.facebook.com\r\n\r\n")
	print("hi")
	resp = yield gen.Task(stream.read_until, b"\r\n\r\n")
	print(resp)

class Task(object):
	def __init__(self, func, *args, **kwargs):
		self.kwargs["callback"] = self.callback
		func(*args, **kwargs)

	def callback(self, *arg, **kwargs):
		pass

def tasklet(gfunc):
	def wrapper(*args, **kwargs):
		g = gfunc(*args, **kwargs)
		ResultChecker(g).run()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
stream = iostream.IOStream(sock)
connect(stream)
ioloop.IOLoop.instance().start()

