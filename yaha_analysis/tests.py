from unittest2 import TestCase

from devourer import devourer

class devourerTests(TestCase):
    def setUp(self):
        self.client = devourer()

    def test_pull_data(self):
        """
        Tests the pulling data function by force updating, and then checking the first file for current page value
        """
        USERNAME = "ancient-molten-giant-2943"
        API_KEY = "-X_VZRijrHoV4qMZxfXq"
        self.client.pull_data(USERNAME, API_KEY, force_update = True)
        test_data = []
        if (os.path.isfile("history_1.json")):
            with open("history_1.json", "r") as infile:
                test_data = json.load(infile)
            self.assertEqual(test_data["meta"]["current_page"], 1)
        
    def test_parse_data(self):
        """
        Tests the parse data function by requesting specific information from the json object
        """
        pass

    def test_generate_decks(self):
        """
        Tests deck generation by asking for unique deck values
        """
        pass

    def test_results(self):
        """
        Tests results by asking for the specific result of a match
        """
        pass
