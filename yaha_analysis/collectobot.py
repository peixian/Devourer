import requests
import pandas as pd
import urllib.request
import subprocess

URL = 'http://files.hearthscry.com/collectobot/'

def pull_data(start_date):
    times = pd.date_range(end=pd.to_datetime('today'), start=start_date)
    for date in times:
        urllib.request.urlretrieve('{}{}.zip'.format(URL, date.date().strftime('%Y-%m-%d')), 'collectobot_data/{}.zip'.format(date.date()))


pull_data()
