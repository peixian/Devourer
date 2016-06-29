import sys
import json
import requests
import pandas as pd

HS_JSON = "https://api.hearthstonejson.com/v1/latest/enUS/"
HS_JSON_EXT = ["cardbacks.json", "cards.collectible.json", "cards.json"]

USERNAME = "ancient-molten-giant-2943"
API_KEY = "-X_VZRijrHoV4qMZxfXq"
URL = "https://trackobot.com/profile/history.json?"

def pull_data(username, api_key, page=1):
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
    return data["meta"]["total_pages"]

def parse_data(pages):
    """
    Parses the json from the pull_data, splits it into readable json object
    """
    history = []
    meta = {}
    for i in xrange(1, pages+1):
        with open("history_{}.json".format(i), "r") as infile:
            data = json.load(infile)["history"]
            
            history.extend(data)

    meta["total_items"] = len(history)
    meta["total_pages"] = pages
    out = {"history": history, "meta": meta}
    with open("history.json", "w") as outfile:
        json.dump(out, outfile)
    return history

def main():
    #tot_pages = pull_data(USERNAME, API_KEY)
    #parse_data(tot_pages)
    parse_data(8)


if __name__ == "__main__":
    main()

