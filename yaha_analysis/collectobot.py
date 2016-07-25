import requests
import pandas as pd
import urllib.request
import subprocess
import sqlite3
import zipfile
import os

URL = 'http://files.hearthscry.com/collectobot/'
DATABASE = './collectobot_data/collectobot.db'

def pull_data():
    """
    Pulls all the collect-o-bot data from: http://www.hearthscry.com/CollectOBot and stores them into DATABASE
    Datebase structure is: ['id', 'date', 'json'] with [int, text, text]
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT max(id) FROM collectobot')
    max_id = c.fetchone()[0]
    if max_id:
        c.execute('SELECT * FROM collectobot WHERE id = ?', (max_id,))
        data = c.fetchone()
        last_date = data[1]
    else:
        last_date = '2016-7-01'
        max_id = 1
    beginning = max_id
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
        if date.date() not in error_dates and date.date().strftime('%Y-%m-%d') != last_date:
            with zipfile.ZipFile('./collectobot_data/{}.zip'.format(date.date())) as zip_ref:
                zip_ref.extractall('./collectobot_data/')
            with open('./collectobot_data/{}.json'.format(date.date())) as infile:
                data = infile.readlines()
                data = ''.join(data)
                max_id += 1
                c.execute('INSERT INTO collectobot VALUES (?, ?, ?)', (max_id, '{}'.format(date.date()), data))
    conn.commit()
    conn.close()

    for date in times:
        if date.date() not in error_dates and date.date().strftime('%Y-%m-%d') != last_date:
            os.remove('collectobot_data/{}.zip'.format(date.date()))
            os.remove('collectobot_data/{}.json'.format(date.date()))
    print('wrote {} new entries'.format(max_id - beginning))

def add_june_2016():
    """This is a manual method to add june 2016, which only has a monthly json file. Don't actually use this."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    with open('./collectobot_data/2016-06.json') as infile:
        data = infile.readlines()
        data = ''.join(data)
        c.execute('INSERT INTO collectobot VALUES (?, ?, ?)', (0, '{}'.format(2016-6-30), data))

    conn.commit()
    conn.close()


