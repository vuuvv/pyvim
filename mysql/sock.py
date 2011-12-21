import inspect

def logger(msg):
	print("logger:", msg)
	print("called from %s:%d" % inspect.stack()[1][1:3])
	print

def client1():
	logger("one")

def client2():
	logger("two")

client1()
client2()



