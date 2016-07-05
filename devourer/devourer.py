import sys
import json
import requests
import pandas as pd
import numpy as np
import os.path
import seaborn as sns
import matplotlib.pyplot as plt



HS_JSON = "https://api.hearthstonejson.com/v1/latest/enUS/"
HS_JSON_EXT = ["cardbacks.json", "cards.collectible.json", "cards.json"]

USERNAME = "ancient-molten-giant-2943"
API_KEY = "-X_VZRijrHoV4qMZxfXq"
URL = "https://trackobot.com/profile/history.json?"

class devourer(object):

    def __init__(self):
        self.total_pages = 0
        self.history = []
        
    def pull_data(self, username, api_key, page=1, force_update = False):
        """
        Repulls the data using the Track-o-Bot API
        """
        if (force_update):
            auth = {"username": username, "token": api_key, "page": page}
            req = requests.get(URL, params=auth)
            data = req.json()
            print("Pulling page #{}".format(page))
            print(req.url)
            
            with open("history_{}.json".format(page), "w") as outfile:
                json.dump(data, outfile)
            if (data["meta"]["next_page"] != None):
              self.pull_data(username, api_key, page=data["meta"]["next_page"], force_update = force_update)
        
    def parse_data(self):
        """
        Parses the json from the pull_data, splits it into readable json object
        """
        with open("history_1.json", "r") as infile:
            self.total_pages = json.load(infile)["meta"]["total_pages"]
        history = []
        meta = {}
        for i in range(1, self.total_pages+1):
            with open("history_{}.json".format(i), "r") as infile:
                data = json.load(infile)["history"]

                history.extend(data)
                
        meta["total_items"] = len(history)
        meta["total_pages"] = self.total_pages
        out = {"history": history, "meta": meta}
        with open("history.json", "w") as outfile:
            json.dump(out, outfile)
        self.history = history
        return history

    def generate_decks(self):
        """
        Differentiates between the different deck types, and sorts them into their individual lists (history is a massive array, transform into a pandas dataframe for processing)
        """
        self.games = pd.DataFrame(self.history)
        self.games["player_deck_type"] = "{}_{}".format(self.games["hero"], self.games["hero_deck"])
        self.games["opponent_deck_type"] = "{}_{}".format(self.games["opponent"], self.games["opponent_deck"])
        print(self.games.dtypes)
        return self.games
  
    def results(self, hero, hero_deck, game_result = "win"):
        """
        Get win turns, win %, most commonly played card, played card turns
        """
        ranked_matches = self.games[(self.games["rank"].notnull()) & (self.games["hero"] == hero) & (self.games["hero_deck"] == hero_deck) & (self.games["result"] == game_result)]
        card_history = ranked_matches["card_history"]
        game_history = pd.concat(list(map(lambda x: pd.DataFrame(x), card_history)))
        
        print(game_history)
        
    

def main():
    nom = devourer()
    nom.pull_data(USERNAME, API_KEY, force_update = False)
    nom.parse_data()
    nom.generate_decks()
    nom.results("Warrior", "Control")

if __name__ == "__main__":
    main()

