from functools import reduce

from .context import sapio
from sapio.examples.multisig import *
import os
import unittest
class TestMultiSig(unittest.TestCase):
    def test(self):
        a = RawMultiSig(keys = [os.urandom(32) for _ in range(5)], thresh=2)
        b = RawMultiSigWithPath(keys = [os.urandom(32) for _ in range(5)], thresh_all=3, thresh_path=2, amount=Bitcoin(5), path=a)
        print(b)

if __name__ == '__main__':
    unittest.main()
