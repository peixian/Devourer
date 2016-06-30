import sys
import json
import requests
import pandas as pd

HS_JSON = "https://api.hearthstonejson.com/v1/latest/enUS/"
HS_JSON_EXT = ["cardbacks.json", "cards.collectible.json", "cards.json"]

USERNAME = "ancient-molten-giant-2943"
API_KEY = "-X_VZRijrHoV4qMZxfXq"
URL = "https://trackobot.com/profile/history.json?"

class devourer(object):
    def __init__(self):
        self.total_pages = 0
        self.history = []

        
    def pull_data(self, username, api_key, page=1):
        """
        Repulls the data using the Track-o-Bot API
        """
        auth = {"username": username, "token": api_key, "page": page}

        req = requests.get(URL, params=auth)
        data = req.json()

        with open("history_{}.json".format(page), "w") as outfile:
            json.dump(data, outfile)
        if (data["meta"]["next_page"] != None):
            pull_data(username, api_key, page=data["meta"]["next_page"])

        self.total_pages = data["meta"]["total_pages"]

    def parse_data(self):
        """
        Parses the json from the pull_data, splits it into readable json object
        """
        history = []
        meta = {}
        for i in xrange(1, self.total_pages+1):
            with open("history_{}.json".format(i), "r") as infile:
                data = json.load(infile)["history"]

                history.extend(data)

        meta["total_items"] = len(history)
        meta["total_pages"] = pages
        out = {"history": history, "meta": meta}
        with open("history.json", "w") as outfile:
            json.dump(out, outfile)
        self.history = history
        return history

    def generate_decks(self):
        """
        Differentiates between the different deck types, and sorts them into their individual lists (history is a massive array, transform into a pandas dataframe for processing)
        """
        games = pd.DataFrame(self.history)
        print(games.head(5))

        print(games["hero_deck"].unique())
    
def main():
    nom = devourer()
    nom.pull_data(USERNAME, API_KEY)
    nom.parse_data()
    nom.generate_decks()

if __name__ == "__main__":
    main()

