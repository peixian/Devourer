import sys
import json
import urllib2
import requests
import pandas as pd

HS_JSON = "https://api.hearthstonejson.com/v1/latest/enUS/"
HS_JSON_EXT = ["cardbacks.json", "cards.collectible.json", "cards.json"]

USERNAME = "ancient-molten-giant-2943"
API_KEY = "-X_VZRijrHoV4qMZxfXq"

def pull_data(username, api_key):
    """
    Repulls the data using the Track-o-Bot API
    """
    URL = "https://trackobot.com/profile/history.json?"
    auth = {"username": username, "token": api_key}
    data = requests.get(URL, params=auth)
    return data

def parse_data(data):
    """
    Parses the json from the pull_data, splits it into readable json object
    """
    data = pd.read_json(data)
    return data

def main():
    df = parse_data(pull_data(USERNAME, API_KEY))
    print(df)



if __name__ == "__main__":
    main()

