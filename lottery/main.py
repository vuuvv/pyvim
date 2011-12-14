import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *

PageSize = (612, 792)

class TextItem(QGraphicsTextItem):
	def __init__(self, text):
		super(TextItem, self).__init__(text)

class GraphicsView(QGraphicsView):
	def __init__(self, parent=None):
		super(GraphicsView, self).__init__(parent)
		self.setDragMode(QGraphicsView.RubberBandDrag)
		self.setRenderHint(QPainter.Antialiasing)
		self.setRenderHint(QPainter.TextAntialiasing)

	def wheelEvent(self, event):
		factor = 1.41 ** (-event.delta() / 240.0)
		self.scale(factor, factor)

class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(QMainWindow, self).__init__(parent)

		self.buttons = [
			("Add &Text", self.add_text),
			("Add &Box", self.add_box),
			("Add Pi&xmap", self.add_pixmap),
			("&Align", None),
			("&Copy", self.copy),
			("C&ut", self.cut),
			("&Paste", self.paste),
			("&Delete...", self.delete),
			("&FullScreen", self.full_screen),
			("&Save", self.save),
			("&Quit", self.accept),
		]

		self.view = GraphicsView()
		self.scene = QGraphicsScene(self)
		self.view.setScene(self.scene)

		self.button_layout = QVBoxLayout()

		#for text, slot in self.buttons:
		#	button = QPushButton(text)
		#	if slot is not None:
		#		self.connect(button, SIGNAL("clicked()"), slot)

		#	self.button_layout.addWidget(button)

		#self.button_layout.addStretch()

		#self.layout = QHBoxLayout()
		#self.layout.addWidget(self.view, 1)
		#self.layout.addLayout(self.button_layout)
		#self.setLayout(self.layout)
		self.setCentralWidget(self.view)

		fm = QFontMetrics(self.font())
		self.resize(self.scene.width() + fm.width(" Delete... ") + 50,
				self.scene.height() + 50)
		self.setWindowTitle("Page Designer")

	def add_text(self):
		pass

	def add_box(self):
		pass

	def add_pixmap(self):
		pass

	def copy(self):
		pass

	def cut(self):
		pass

	def paste(self):
		pass

	def delete(self):
		pass

	def full_screen(self):
		self.button_layout.hide()
		self.showFullScreen()

	def save(self):
		pass

	def accept(self):
		pass

app = QApplication(sys.argv)
form = MainWindow()
rect = QApplication.desktop().availableGeometry()
form.resize(int(rect.width() * 0.6), int(rect.height() * 0.9))
form.show()
app.exec_()
