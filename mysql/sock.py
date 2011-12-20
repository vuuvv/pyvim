def echo(value=None):
	try:
		print("Execution starts when 'next()' is called for the first time.")
		yield 0
		1/0
	except:
		print("ABCDEFG")

g = echo()
#print(g.send(None))


