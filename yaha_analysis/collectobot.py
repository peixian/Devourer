import requests
import pandas as pd
import urllib.request
import subprocess
import sqlite3
import zipfile
import os

URL = 'http://files.hearthscry.com/collectobot/'

def pull_data():
    conn = sqlite3.connect('./collectobot_data/collectobot.db')
    c = conn.cursor()
    c.execute('SELECT max(id) FROM collectobot')
    max_id = c.fetchone()[0]

    if max_id:
        c.execute('SELECT date FROM collectobot WHERE id = ?', (max_id,))
        data = c.fetchall()
        last_date = data[1]
    else:
        last_date = '2016-7-01'
        max_id = 0
    times = pd.date_range(end=pd.to_datetime('today'), start=last_date)
    error_dates = []
    for date in times:
        try:
            urllib.request.urlretrieve('{}{}.zip'.format(URL, date.date().strftime('%Y-%m-%d')), './collectobot_data/{}.zip'.format(date.date()))
        except urllib.request.HTTPError as err:
            if err.code == 404:
                error_dates.append(date.date())
            else:
                raise
        if date.date() not in error_dates:
            with zipfile.ZipFile('./collectobot_data/{}.zip'.format(date.date())) as zip_ref:
                zip_ref.extractall('./collectobot_data/')
            with open('{}.json'.format(date.date())) as infile:
                data = infile.readlines()
                data = ''.join(data)
                max_id += 1
                c.execute('INSERT INTO collectobot VALUES (?, ?, ?)', (max_id, '{}'.format(date.date()), data))
    conn.commit()
    conn.close()

    for date in times:
        os.remove('collectobot_data/{}.zip'.format(date.date()))
        os.remove('collectobot_data/{}.json'.format(date.date()))
pull_data()
