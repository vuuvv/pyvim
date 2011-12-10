import unittest
import os
import codecs

from qvim.ui.text import Line, Document

class TestLine(unittest.TestCase):

	def test_simple(self):
		line = Line("abc")
		self.assertEqual(0, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(3, line.length)
		self.assertEqual("", line.part1)
		self.assertEqual("abc", line.part2)
		self.assertEqual("abc", line.text)
		self.assertEqual("bc", line.read(1, 2))
		# first insert
		line.write(1, "1")
		self.assertEqual(2, line.gap_pos)
		self.assertEqual(32, line.gap_length)
		self.assertEqual(4, line.length)
		self.assertEqual("a1", line.part1)
		self.assertEqual("bc", line.part2)
		self.assertEqual("a1bc", line.text)
		self.assertEqual("a", line.read(0, 1))
		self.assertEqual("1b", line.read(1, 2))
		self.assertEqual("bc", line.read(2, 2))
		# insert at part1
		line.write(2, "2")
		self.assertEqual(3, line.gap_pos)
		self.assertEqual(31, line.gap_length)
		self.assertEqual(5, line.length)
		self.assertEqual("a12", line.part1)
		self.assertEqual("bc", line.part2)
		self.assertEqual("a12bc", line.text)
		# insert at part2
		line.write(4, "3")
		self.assertEqual(5, line.gap_pos)
		self.assertEqual(30, line.gap_length)
		self.assertEqual(6, line.length)
		self.assertEqual("a12b3", line.part1)
		self.assertEqual("c", line.part2)
		self.assertEqual("a12b3c", line.text)
		# insert at end
		line.write(6, "4")
		self.assertEqual(5, line.gap_pos)
		self.assertEqual(30, line.gap_length)
		self.assertEqual(7, line.length)
		self.assertEqual("a12b3", line.part1)
		self.assertEqual("c4", line.part2)
		self.assertEqual("a12b3c4", line.text)
		# remove part1
		line.remove(1, 2)
		self.assertEqual(1, line.gap_pos)
		self.assertEqual(32, line.gap_length)
		self.assertEqual(5, line.length)
		self.assertEqual("a", line.part1)
		self.assertEqual("b3c4", line.part2)
		self.assertEqual("ab3c4", line.text)
		# remove part2
		line.remove(2, 1)
		self.assertEqual(2, line.gap_pos)
		self.assertEqual(33, line.gap_length)
		self.assertEqual(4, line.length)
		self.assertEqual("ab", line.part1)
		self.assertEqual("c4", line.part2)
		self.assertEqual("abc4", line.text)
		# test text setter
		line.text = "abcdefg"
		self.assertEqual(0, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(7, line.length)
		self.assertEqual("", line.part1)
		self.assertEqual("abcdefg", line.part2)
		self.assertEqual("abcdefg", line.text)

	def test_insert_at_end(self):
		line = Line("abc")
		line.write(3, "d")
		self.assertEqual(0, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(4, line.length)
		self.assertEqual("", line.part1)
		self.assertEqual("abcd", line.part2)
		self.assertEqual("abcd", line.text)

	def test_gap_pos_at_end(self):
		line = Line("abc")

		line.write(2, "d")
		self.assertEqual(3, line.gap_pos)
		self.assertEqual(32, line.gap_length)
		self.assertEqual(4, line.length)
		self.assertEqual("abd", line.part1)
		self.assertEqual("c", line.part2)
		self.assertEqual("abdc", line.text)

		line.remove(2, 2)
		self.assertEqual(2, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(2, line.length)
		self.assertEqual("ab", line.part1)
		self.assertEqual("", line.part2)
		self.assertEqual("ab", line.text)

		line.write(2, "cdefg")
		self.assertEqual(2, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(7, line.length)
		self.assertEqual("ab", line.part1)
		self.assertEqual("cdefg", line.part2)
		self.assertEqual("abcdefg", line.text)

		line.remove(2, 1000)
		self.assertEqual(2, line.gap_pos)
		self.assertEqual(0, line.gap_length)
		self.assertEqual(2, line.length)
		self.assertEqual("ab", line.part1)
		self.assertEqual("", line.part2)
		self.assertEqual("ab", line.text)

class TestDocument(unittest.TestCase):
	def setUp(self):
		directory = os.environ["TEMP"]
		self.filename = os.path.join(directory, "__test__.txt")
		self.file = open(self.filename, "wb")
		self.file.write(codecs.BOM_UTF8)
		self.file.write(b'abcdefg\n')
		self.file.close()

	def test_open(self):
		doc = Document(self.filename)
		self.assertEqual(self.filename, doc.filename)
		self.assertEqual("UTF-8", doc.codec)
		self.assertEqual(codecs.BOM_UTF8, doc.bom)
		self.assertEqual(doc.LF_LINE_TEMINATOR, doc.line_terminator)
		self.assertFalse(doc.file_is_read_only)
		self.assertEqual(2, doc.rows)
		self.assertEqual('', doc.decoding_error_sample)
		self.assertEqual("abcdefg", doc.lines[0])

	def test_edit(self):
		doc = Document(self.filename)
		# insert single line
		doc.insert(0, 0, "111")
		self.assertEqual(2, doc.rows)
		self.assertEqual(0, doc.last_edit_row)
		self.assertEqual("111abcdefg", doc.lines[0].text)

		#insert multiple line at end
		doc.insert(2, 0, "1\n2\n3\n")
		self.assertEqual(6, doc.rows)
		self.assertEqual(5, doc.last_edit_row)
		self.assertEqual("111abcdefg", doc.lines[0])
		self.assertEqual("", doc.lines[1])
		self.assertEqual("1", doc.lines[2])
		self.assertEqual("2", doc.lines[3])
		self.assertEqual("3", doc.lines[4])
		self.assertEqual("", doc.lines[5].text)
		
		#insert multiple line in buf
		doc.insert(0, 9, "222222\nbcdefg\ncccd")
		self.assertEqual(8, doc.rows)
		self.assertEqual(2, doc.last_edit_row)
		self.assertEqual("111abcdef222222", doc.lines[0])
		self.assertEqual("bcdefg", doc.lines[1])
		self.assertEqual("cccdg", doc.lines[2].text)
		self.assertEqual("", doc.lines[3])
		self.assertEqual("1", doc.lines[4])
		self.assertEqual("2", doc.lines[5])
		self.assertEqual("3", doc.lines[6])
		self.assertEqual("", doc.lines[7])

		#insert multiple line at line end
		doc.insert(0, 16, "0\n1\n2")
		self.assertEqual(10, doc.rows)
		self.assertEqual(3, doc.last_edit_row)
		self.assertEqual("111abcdef222222", doc.lines[0])
		self.assertEqual("0", doc.lines[1])
		self.assertEqual("1", doc.lines[2])
		self.assertEqual("2bcdefg", doc.lines[3].text)
		self.assertEqual("cccdg", doc.lines[4])
		self.assertEqual("", doc.lines[5])
		self.assertEqual("1", doc.lines[6])
		self.assertEqual("2", doc.lines[7])
		self.assertEqual("3", doc.lines[8])
		self.assertEqual("", doc.lines[9])

		#remove simple
		doc.remove(4, 2, 2)
		self.assertEqual(10, doc.rows)
		self.assertEqual(4, doc.last_edit_row)
		self.assertEqual("111abcdef222222", doc.lines[0])
		self.assertEqual("0", doc.lines[1])
		self.assertEqual("1", doc.lines[2])
		self.assertEqual("2bcdefg", doc.lines[3])
		self.assertEqual("ccg", doc.lines[4].text)
		self.assertEqual("", doc.lines[5])
		self.assertEqual("1", doc.lines[6])
		self.assertEqual("2", doc.lines[7])
		self.assertEqual("3", doc.lines[8])
		self.assertEqual("", doc.lines[9])

		#remove at line end
		doc.remove(5, 0, 1)
		self.assertEqual(9, doc.rows)
		self.assertEqual(5, doc.last_edit_row)
		self.assertEqual("111abcdef222222", doc.lines[0])
		self.assertEqual("0", doc.lines[1])
		self.assertEqual("1", doc.lines[2])
		self.assertEqual("2bcdefg", doc.lines[3])
		self.assertEqual("ccg", doc.lines[4])
		self.assertEqual("1", doc.lines[5].text)
		self.assertEqual("2", doc.lines[6])
		self.assertEqual("3", doc.lines[7])
		self.assertEqual("", doc.lines[8])

	def tearDown(self):
		os.remove(self.filename)

