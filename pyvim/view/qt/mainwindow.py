
from pyvim.view.qt import qt
from pyvim.view.qt.text import Editor

class MainWindow(qt.QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)

		self.editor = Editor(self)
		self.setCentralWidget(self.editor)
		self.editor.test()
