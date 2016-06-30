from unittest2 import TestCase

from devourer import devourer

class devourerTests(TestCase):
    def setUp(self):
        self.client = devourer()

    def test_pull_data(self):
        USERNAME = "ancient-molten-giant-2943"
        API_KEY = "-X_VZRijrHoV4qMZxfXq"
