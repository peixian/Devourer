from unittest2 import TestCase

from devourer import devourer

class devourerTests(TestCase):
    def setUp(self):
        self.client = devourer()
