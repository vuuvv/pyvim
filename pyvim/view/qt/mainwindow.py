
from pyvim.view.qt import qt
from pyvim.view.qt.text import Text

class MainWindow(qt.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

		self.text = Text(self)
		self.setCentralWidget(self.text)
		self.text.test()
