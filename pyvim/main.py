import os
import sys

from pyvim.view.qt import qt
from pyvim.view.qt import settings
from pyvim.view.qt.mainwindow import MainWindow

def main():
	app = qt.QApplication(sys.argv)
	app.setOrganizationName(settings.ORGANIZATION_NAME)
	app.setOrganizationDomain(settings.ORGANIZATION_DOMAIN)

	win = MainWindow()
	win.show()
	app.exec_()

if __name__ == '__main__':
	main()
