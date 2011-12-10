
class Line(object):
	def __init__(self, initial_value="", newline=None, growsize=32):
		self.buf = io.StringIO(initial_value, newline)
		self.growsize = 32

		self.init(initial_value)

	def init(self, value):
		self.length = len(value)
		self.gap_pos = 0
		self.gap_length = 0

	def move_gap(self, pos):
		buf = self.buf
		pos = min(self.length, pos)
		gap_pos = self.gap_pos
		gap_length = self.gap_length
		if gap_length > 0:
			if pos < gap_pos:
				buf.seek(pos)
				t = buf.read(gap_pos - pos)
				buf.seek(pos + gap_length)
				buf.write(t)
			else:
				buf.seek(gap_pos + gap_length)
				t = buf.read(pos - gap_pos)
				buf.seek(gap_pos)
				buf.write(t)
		self.gap_pos = pos

	def check_room(self, pos, size):
		if self.gap_length < size:
			self.realloc(pos, self.length + size + self.growsize)
		self.move_gap(pos)

	def realloc(self, newsize):
		buf = self.buf
		t = self.part2
		len2 = len(t)
		buf.seek(newsize - len2)
		buf.write(t)
		self.gap_length = newsize - self.length

	def read(self, pos, length):
		if pos < self.gap_pos:
			self.buf.seek(pos)
			if pos + length <= self.gap_pos:
				return self.buf.read(length)
			else:
				len1 = self.gap_pos-pos
				p1 = self.buf.read(len1)
				self.buf.seek(self.gap_pos + self.gap_length)
				p2 = self.buf.read(length-len1)
				return p1 + p2
		else:
			self.buf.seek(self.gap_length+pos)
			return self.buf.read(length)
	
	def write(self, pos, text):
		""" text can not contain the newline character """
		length = len(text)
		buf = self.buf
		if pos >= self.length:
			buf.seek(self.length + self.gap_length)
			buf.write(text)
			self.length += length
		else:
			self.check_room(pos, length)
			buf.seek(pos)
			buf.write(text)
			self.gap_pos += length
			self.gap_length -= length
			self.length += length

	def append(self, text):
		self.write(self.length, text)

	# TODO: memory clean, PS: can use truncate when call remove

	def remove(self, pos, length):
		if pos + length >= self.length:
			self.gap_pos = pos
			self.gap_length = 0
			self.length = self.gap_pos
		else:
			self.move_gap(pos)
			self.gap_length += length
			self.length -= length

	@property
	def text(self):
		return self.part1 + self.part2

	@text.setter
	def text(self, value):
		self.buf.seek(0)
		self.buf.write(value)
		self.init(value)

	@property
	def part1(self):
		pos = self.buf.tell()
		self.buf.seek(0)
		s = self.buf.read(self.gap_pos)
		self.buf.seek(pos)
		return s

	@property
	def part2(self):
		pos = self.buf.tell()
		self.buf.seek(self.gap_pos + self.gap_length)
		s = self.buf.read(self.length - self.gap_pos)
		self.buf.seek(pos)
		return s

class Document(object):
	def __init__(self, text):
		pass
