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

    def unique_decks_tests(self):
        """
        Tests for a unique deck list
        """
        self.client.open_collectobot_data()
        self.client.generate_decks()
        deck_types = self.client._unique_decks()
        self.assertTrue(len(deck_types) > 0)
        self.assertTrue(isinstance(deck_types[0], str))

    def unique_cards_test(self):
        """
        Tests for a unique card lists
        """
        self.client.open_collectobot_data()
        self.client.generate_decks()
        card_types = self.client._unique_cards()
        self.assertTrue(len(card_types) > 0)
        self.assertTrue(isinstance(card_types[0], str))

    def get_card_list_test(self):
        self.client.open_collectobot_data()
        self.client.generate_decks()
        dict_list_test = [{"player":"opponent","turn":1,"card":{"id":"GAME_005","name":"The Coin","mana":null}},{"player":"opponent","turn":1,"card":{"id":"EX1_169","name":"Innervate","mana":0}},{"player":"opponent","turn":1,"card":{"id":"AT_043","name":"Astral Communion","mana":4}},{"player":"opponent","turn":1,"card":{"id":"CS2_017","name":"Shapeshift","mana":2}},{"player":"me","turn":2,"card":{"id":"EX1_169","name":"Innervate","mana":0}},{"player":"me","turn":2,"card":{"id":"NEW1_026","name":"Violet Teacher","mana":4}},{"player":"opponent","turn":2,"card":{"id":"OG_202","name":"Mire Keeper","mana":4}},{"player":"opponent","turn":2,"card":{"id":"CS2_017","name":"Shapeshift","mana":2}},{"player":"me","turn":3,"card":{"id":"LOE_115","name":"Raven Idol","mana":1}},{"player":"me","turn":3,"card":{"id":"AT_037","name":"Living Roots","mana":1}}]
        p_card_list = self.client._get_card_list(dict_list = dict_list_test)
        self.assertTrue(len(p_card_list) > 0)
        self.assertTrue(isinstance(p_card_list[0], str))

