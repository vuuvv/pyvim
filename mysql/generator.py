from greenlet import greenlet

def test1():
	print(12)
	gr2.switch()
	print(34)

def test2():
	1/0
	gr1.switch()
	print(78)

gr1 = greenlet(test1)
gr2 = greenlet(test2)
gr1.switch()

