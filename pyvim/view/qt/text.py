import os
import io
import sys
import stat
import codecs

from pyvim.view.qt.qt import *
from pyvim.view.qt import settings

bom_dict = {
	"UTF-8": codecs.BOM_UTF8,
	"UTF-16-LE": codecs.BOM_UTF16_LE,
	"UTF-16-BE": codecs.BOM_UTF16_BE,
	"UTF-32-LE": codecs.BOM_UTF32_LE,
	"UTF-32-BE": codecs.BOM_UTF32_BE,
}

class Char(object):
	def __init__(self, display, type = "single", width = 1):
		self.display = display
		self.type = type
		self.width = width

listchars = {
	"eol":		Char("\u00ac", "eol"),
	"tab":		Char("\u2192 ", "tab"),
	"eof":		Char("\u00b6", "eof"),
	"trail":	Char("", "trail"),
}

class Text(QAbstractScrollArea):
	def __init__(self, parent=None):
		super().__init__(parent)

		self._font = QFont("Courier New", 12)
		self.background = Qt.white
		self.color = Qt.black
		self.caret_background = Qt.black
		self.caret_color = Qt.white
		self.selected_background = Qt.blue
		self.selected_color = Qt.white
		self.document = Document()
		self.init()

	@property
	def top(self):
		return self._top

	@top.setter
	def top(self, value):
		value = min(value, self.document.rows)
		value = max(0, value)
		self._top = value
		self.verticalScrollBar().setValue(value)
		self.update_area()

	def init(self):
		self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		self.verticalScrollBar().setSingleStep(1)
		vbar = self.verticalScrollBar()
		vbar.setMaximum(self.document.rows)
		self._top = 0
		self.left = 0
		self.row = 0
		self.col = 0
		self.drow = 0
		self.dcol = 0
		self.tabstop = 8

		self.setFont(settings.DEFAULT_FONT)

		self.render_method = self.render_area
		self.caret_timer = QTimer(self)
		self.connect(self.caret_timer, SIGNAL("timeout()"), self.update_caret)

	def char_metrics(self):
		fm = QFontMetrics(self._font)
		return (fm.width("M"), fm.height())

	def char_at(self, row, col):
		doc = self.document
		line = doc.row(row)
		rows = doc.rows
		if (col == len(line)):
			return listchars["eol"] if row < rows - 1 else listchars["eof"]
		c = doc.char_at(row, col)
		if (c == '\t'):
			return listchars["tab"]
		return Char(c)

	def test(self):
		self.document.open("d:/text.py")
		self.verticalScrollBar().setMaximum(self.document.rows)

	def next_char(self, col, char):
		type, tabstop = char.type, self.tabstop
		if type == "tab":
			return (col // tabstop + 1) * tabstop
		return col + char.width

	def get_document_pos(self, row, col):
		p = 0
		i = 0
		next_char, char_at = self.next_char, self.char_at
		for i in range(len(self.document.row(row))):
			p = next_char(p, char_at(row, i))
			if p > col:
				return i
		return i

	def get_screen_pos(self, row, col):
		next_char, char_at = self.next_char, self.char_at
		for i in range(col):
			n = next_char(0, char_at(row, i))
		return n

	def draw_raw_char(self, painter, char, x, y, width, height, color, bg):
		#print("draw raw char:", x, y, [char.encode()])
		painter.fillRect(x, y, width, height, bg)
		painter.setPen(color)
		painter.drawText(QRectF(x, y, width, height), char)

	def draw_char(self, painter, char, row, col, color, bg):
		cw, ch = self.char_metrics()
		x, y = (col - self.left) * cw, (row - self.top) * ch
		width = cw * char.width
		if char.type == "tab":
			end = self.next_char(col, char)
			self.draw_raw_char(painter, char.display[0], x, y, cw, ch, color, bg)
			i = col + 1
			x += cw
			while i < end:
				self.draw_raw_char(painter, char.display[1], x, y, cw, ch, color, bg)
				x += cw
				i += 1
			return end
		else:
			self.draw_raw_char(painter, char.display, x, y, width, ch, color, bg)
			return col + char.width

	def draw_line(self, painter, row, start, end, color, bg):
		line = self.document.row(row)
		dcol = self.get_document_pos(row, start)
		while start <= end:
			start = self.draw_char(painter, self.char_at(row, start), row, start, color, bg)

	def draw_rect(self, painter, x, y, width, height):
		"""Suppose the rect (x, y, width, height) is in the viewport of widget"""
		cw, ch = self.char_metrics()
		col, row = x // cw + self.left, y // ch + self.top
		ecol, erow = (x + width) // cw + self.left + 1, (y + height) // ch + self.top
		erow = min(erow, self.document.rows - 1)
		get_row = self.document.row
		color, bg = self.color, self.background
		painter.fillRect(0, 0, width, height, self.background)
		painter.setPen(self.color)
		painter.setFont(self._font)
		while row <= erow:
			length = len(get_row(row))
			dcol = self.get_document_pos(row, col)
			start = col
			while start <= ecol and dcol < length:
				start = self.draw_char(painter, self.char_at(row, dcol), row, start, color, bg)
				dcol += 1
			row += 1

	def show_caret(self, painter, row, col, char, w = None, shown=True):
		background = self.caret_background if shown else self.background
		color = self.caret_color if shown else self.color
		painter.setFont(self._font)
		self.draw_char(painter, char, row, col, color, background)
		self.caret_shown = shown

	def blink_caret(self):
		timer = self.caret_timer
		if timer.isActive():
			timer.stop()
		self.caret_shown = False
		self.update_caret()
		self.caret_timer.start(400)

	def update_caret(self):
		cw, ch = self.char_metrics()
		c = self.char_at(self.drow, self.dcol)
		x, y = (self.col - self.left) * cw, (self.row - self.top) * ch
		self.render_method = self.render_caret
		self.viewport().repaint(x, y, cw * c.width, ch)
		self.render_method = self.render_area

	def update_area(self, rect = None):
		if rect is None:
			rect = self.viewport().rect()
		self.render_method = self.render_area
		self.viewport().update(rect)

	def update_selection(self):
		pass

	# Render functions
	def render_caret(self, painter, rect):
		c = self.char_at(self.drow, self.dcol)
		self.show_caret(painter, self.row, self.col, char = c, shown = not self.caret_shown)

	def render_area(self, painter, rect):
		self.caret_timer.stop()
		self.draw_rect(painter, rect.x(), rect.y(), rect.width(), rect.height())
		#self.blink_caret()

	def render_selection(self, painter, rect):
		pass
	
	# Overload
	def scrollContentsBy(self, dx, dy):
		if dx == 0 and dy == 0:
			return
		self.top -= dy

	def paintEvent(self, event=None):
		self.render_method(QPainter(self.viewport()), event.rect())
	
	def resizeEvent(self, ev):
		pass

	def showEvent(self, ev):
		pass

	def hideEvent(self, ev):
		self.caret_timer.stop()

	def keyPressEvent(self, ev):
		pass

	def mousePressEvent(self, ev):
		pass

class Line(object):
	def __init__(self, initial_value="", newline=None, growsize=32):
		self.buf = io.StringIO(initial_value, newline)
		self.growsize = 32

		self.init(initial_value)

	def __getitem__(self, index):
		if isinstance(index, int):
			return self.read(index, 1)
		elif isinstance(index, slice):
			start = index.start if index.start is not None else 0
			if index.stop is None:
				return self.read(start)
			else:
				return self.read(start, index.stop - start)
		else:
			raise IndexError("Wrong index '%s'", index)

	def __setitem__(self, index, value):
		self.write(index, value)

	def __len__(self):
		return self.length

	def __iter__(self):
		current = 0
		read = self.read
		length = self.length
		while current < length:
			yield read(current, 1)
			current += 1

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

	def realloc(self, pos, newsize):
		buf = self.buf
		t = self.part2
		len2 = len(t)
		buf.seek(newsize - len2)
		buf.write(t)
		self.gap_length = newsize - self.length

	def read(self, pos, length = None):
		length = length if length is not None else self.length - pos
		gap_pos = self.gap_pos
		if pos < gap_pos:
			self.buf.seek(pos)
			if pos + length <= gap_pos:
				return self.buf.read(length)
			else:
				len1 = gap_pos - pos
				p1 = self.buf.read(len1)
				self.buf.seek(gap_pos + self.gap_length)
				p2 = self.buf.read(length - len1)
				return p1 + p2
		else:
			self.buf.seek(self.gap_length + pos)
			return self.buf.read(length)
	
	def write(self, pos, text):
		""" text should not contain the newline character """
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

	# TODO: memory shrink, PS: can use truncate when call remove

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

class Document(QObject):
	CHUNK_SIZE = 65536
	DEFAULT_CODEC = "UTF-8"
	LF_LINE_TEMINATOR = "\n"
	CRLF_LINE_TERMINATOR = "\r\n"
	CR_LINE_TERMINATOR = "\r"

	# signal
	title_changed = pyqtSignal(str)
	changed = pyqtSignal()

	def __init__(self, filename=None, parent=None):
		super().__init__(parent)
		self.default_path = ""
		self.suggested_file_name = ""
		self.mime_type = ""
		self.storage_settings = None
		self.extra_encoding_settings = None
		self.highlighter = None
		self.line_terminator = self.LF_LINE_TEMINATOR
		self.codec = self.DEFAULT_CODEC
		self.bom = False
		self.file_is_read_only = False
		self.has_decoding_error = False
		self.decoding_error_sample = None
		self.lines = []
		self.last_edit_row = None

		if filename is not None:
			self.open(filename)

	def detect_encoding(self, byteio):
		line = b''
		try:
			line = byteio.readline()
		except StopIteration:
			pass

		size = len(line)
		self.file_has_utf8_bom = False
		self.codec = self.DEFAULT_CODEC

		for key, bom in bom_dict.items():
			length = len(bom)
			if size >= length and line[:length] == bom:
				self.codec = key
				self.bom = bom
				byteio.seek(length)
				return
		byteio.seek(0)

	def check_file(self, filename):
		if os.path.isfile(filename):
			self.filename = os.path.abspath(filename)
			self.file_is_read_only = os.stat(filename).st_mode & stat.S_IWRITE == 0
			return True
		return False

	def open(self, filename = None):
		title = "untitled"
		self.has_decoding_error = False
		if filename is not None:
			if not self.check_file(filename):
				return False
			title = os.path.basename(filename)
			file = open(filename, "rb")
			self.detect_encoding(file)

			buf = b''
			try:
				buf = file.read()
			except (IOError, MemoryError):
				return False
			finally:
				if file is not None:
					file.close()

			bytes_read = len(buf)
			content = None
			try:
				content = buf.decode(self.codec)
			except UnicodeError:
				content = buf.decode(self.codec, "replace")
				self.has_decoding_error = True
				self.file_is_read_only = True

			if self.has_decoding_error:
				p = buf.find(b"\n", 16384)
				if p < 0:
					self.decoding_error_sample = buf
				else:
					self.decoding_error_sample = buf[:p]
			else:
				self.decoding_error_sample = ""

			p = content.find("\n")
			if p > 0:
				self.line_terminator = self.CRLF_LINE_TERMINATOR if content[p-1] == "\r" else self.LF_LINE_TEMINATOR
			self.lines = [line for line in content.split(self.line_terminator)]

			self.title_changed.emit(title)
			self.changed.emit()
		return True

	def gap_line(self, row):
		last = self.last_edit_row
		if last == row:
			return self.lines[row]

		row = min(self.rows, row)
		last = self.last_edit_row
		if last is not None:
			line = self.lines[last]
			self.lines[last] = self.lines[last].text
			line.text = self.lines[row]
		else:
			line = Line(self.lines[row])

		self.lines[row] = line
		self.last_edit_row = row
		return line

	def insert(self, row, col, text):
		lines = text.split(self.line_terminator)
		rows = len(lines)

		if row >= self.rows:
			self.lines.extend([t for t in lines])
			self.gap_line(self.rows - 1)
			return

		line = self.gap_line(row)
		if rows == 1:
			line.write(col, text)
		else:
			if col > line.length:
				self.lines[row+1:row+1] = lines
				self.line_join(row + rows)
			else:
				right = line.read(col, line.length - col)
				line.remove(col, line.length-col)
				line.write(col, lines[0])
				row += 1
				self.lines[row:row] = [t for t in lines[1:]]
				row += rows - 2
				line = self.gap_line(row)
				line.append(right)

	def remove(self, row, col, length):
		line = self.gap_line(row)
		size = line.length
		line.remove(col, length)
		if col + length > size:
			self.line_join(row)

	def line_join(self, row):
		lines = self.lines
		line = self.gap_line(row)
		line.append(lines[row+1])
		lines.pop(row + 1)

	def char_at(self, row, col):
		return self.lines[row][col]

	def row(self, row):
		return self.lines[row]

	@property
	def text(self):
		last = self.last_edit_row
		lines = self.lines
		if last is None:
			return self.line_terminator.join([line for line in lines])
		else:
			tmp = lines[last]
			lines[last] = tmp.text
			text = self.line_terminator.join([line for line in lines])
			lines[last] = tmp
			return text

	@property
	def rows(self):
		return len(self.lines)

