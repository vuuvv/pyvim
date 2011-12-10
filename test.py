"""
do the unit tests
"""

import os
import sys
import unittest
import logging

TEST_DIR = "tests"

logging.basicConfig(level=logging.DEBUG)

def main():
	loader = unittest.TestLoader()
	suite = loader.discover(TEST_DIR)
	runner = unittest.TextTestRunner(verbosity=2)
	runner.run(suite)

if '__main__' == __name__:
	main()

