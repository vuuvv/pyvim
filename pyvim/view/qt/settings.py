import os
from PyQt4.QtGui import QFont

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = 'images'

def r(path):
	return os.path.join(LOCAL_DIR, path)

def image(path):
	return r(os.path.join(IMAGE_DIR, path))

APP_NAME = "QVIM"
ORGANIZATION_NAME = "VUUVV"
ORGANIZATION_DOMAIN = "vuuvv.com"
WINDOW_ICON = image("icon.png")

DEFAULT_FONT = QFont("Courier New", 10)
