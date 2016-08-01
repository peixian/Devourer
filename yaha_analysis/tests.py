from unittest2 import TestCase

import yaha_analyzer

class YahaTests(TestCase):
    def setup(self):
        self.client = yaha_analyzer.yaha_analyzer()

    def collectobot_data_test(self):
        """
        Tests for generating collectobot data
        """
        results = self.client.generate_collectobot_data()
        self.assertTrue(results.size > 0)

    def open_collectobot_data_test(self):
        """
        Tests for opening collectobot data
        """
        self.client.games = None
        self.client.open_collectobot_data()
        self.assertTrue(self.client.games.size > 0)

    def pull_data_test(self):
        """
        Tests for pulling data using my api key
        """
        results = self.client.pull_data(username='ancient-molten-giant-2943', api_key='-X_VZRijrHoV4qMZxfXq')
        self.assertTrue(results.size > 0)

    def generate_deck_tests(self):
        """
        Tests the deck generation
        """
        self.client.open_collectobot_data()
        self.client.generate_decks()
        self.assertTrue(self.games.size > 0)

        
