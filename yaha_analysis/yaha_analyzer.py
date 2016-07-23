import sys
import json
import requests
import pandas as pd
import numpy as np
import os.path
import datetime
import sqlite3
import hashlib
from pandas import HDFStore
import plotly
from collections import defaultdict

DATA_PATH = '../test_data/' #TODO in current directory while testing, needs to be fixed before shipping!

HS_JSON = 'https://api.hearthstonejson.com/v1/latest/enUS/'
HS_JSON_EXT = ['cardbacks.json', 'cards.collectible.json', 'cards.json']

USERNAME = 'ancient-molten-giant-2943'
API_KEY = '-X_VZRijrHoV4qMZxfXq'
URL = 'https://trackobot.com/profile/history.json?'

class yaha_analyzer(object):

    def __init__(self):
        self.total_pages = 0
        self.history = []
        self.username = ''
        self.api_key = ''
        self.new_data = False


    def _open_collectobot_data(self, bot_data):
        """
        Opens a json file created by collectobot

        Keyword parameter:
        bot_data -- str, location of the collectobot file
        """

        with open("{}{}".format(DATA_PATH, bot_data)) as json_data:
            results = json.load(json_data)
        results = results['games']
        self.history = {'children': results, 'meta': {'total_items': len(results)}}
        self.generate_decks(dates = False)
        return results

    def _open_data(self, json_file):
        """
        Opens a json file and loads it into the object, this method is meant for testing

        Keyword parameter:
        json_file -- str, location of the json file
        """
        with open(json_file, "r") as infile:
            results = json.loads(infile)
        self.history = results
        self.generate_decks()
        return results


    def grab_data(self, username, api_key):
        """

        Grabs the data from the trackobot servers, writes it out to a new files and the database if it doesn't exist/outdated

        Keyword parameter:
        username -- str, trackobot username
        api_key -- str, trackobot api_key

        Returns:
        The contents of the json_file (includes history & metadata)
        """
        self.username = username
        self.api_key = api_key
        url = 'https://trackobot.com/profile/history.json?'
        auth = {'username': username, 'token': api_key}
        req = requests.get(url, params=auth).json()
        metadata = req['meta']
        user_hash, count, json_name, hdf5_name = self.store_data()
        #if it's not equal, repull
        if metadata['total_items'] != count or not self.check_data(json_name, hdf5_name):
            results = {'children': req['history']}
            if metadata['total_pages'] != None:
                for page_number in range(2, metadata['total_pages']+1):
                    auth['page'] = page_number
                    results['children'].extend(requests.get(url, params=auth).json()['history'])
            results['meta'] = {'total_items': metadata['total_items']}
            self.history = results
            self.generate_decks()
            self.write_hdf5(hdf5_name)
            with open('{}{}'.format(DATA_PATH, json_name), "w") as outfile:
                json.dump(results, outfile)
            self.update_count(user_hash, metadata['total_items']) #once everything's been loaded and written, update the total_items count in the database
        else:
            results = self.read_data(json_name, hdf5_name)
        return results

    def generate_decks(self, dates = True):
        """
        Differentiates between the different deck types, and sorts them into their individual lists (history is a massive array, transform into a pandas dataframe for processing)

        Returns:
        Pandas dataframe with all the games
        """
        self.games = pd.DataFrame(self.history['children'])
        self.games.loc[self.games['hero_deck'].isnull(), 'hero_deck'] = 'Other'
        self.games.loc[self.games['opponent_deck'].isnull(), 'opponent_deck'] = 'Other'
        self.games['p_deck_type'] = self.games['hero_deck'].map(str) + '_' +  self.games['hero']
        self.games['o_deck_type'] = self.games['opponent_deck'].map(str) + '_' + self.games['opponent']

        self._generate_cards_played()
        if dates:
            self._make_dates()
        self.games = self.games[self.games['card_history'].str.len() != 0]
        return self.games


    def _make_dates(self):
        """Internal method -- Converts the dates in self.games to separate columns for easier parsing, called by generate_decks"""
        format_date = lambda x: datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S.%fZ')
        split_date = lambda x: {'year': x.year, 'month': x.month, 'day': x.day, 'hour': x.hour, 'minute': x.minute, 'second': x.second}
        date_df = pd.DataFrame(list(map(lambda x: split_date(format_date(x)), self.games['added'])))
        self.games = self.games.join(date_df, how='outer')

    def _get_card_list(self, dict_list, player='me'):
        """
        Internal method -- Returns the list of cards that were played in a game, called by _generate_cards_played

        Keyword parameter:
        dict_list -- list of dictionaries from the ['card_history'] column in self.games for one particular game
        player -- the player to be parsing

        Returns:
        p_card_list -- array of card names (str)
        """
        p_card_list = list(filter(None, map(lambda x: x['card']['name'] if x['player'] == player else None, dict_list)))
        return p_card_list


    def _generate_cards_played(self):
        """Internal method -- Generates a list of cards for player and opponent into the list ['p_cards_played'] and ['o_cards_played'], called by generate_decks"""
        self.games['p_cards_played'] = self.games['card_history'].map(lambda x: self._get_card_list(x, player='me'))
        self.games['o_cards_played'] = self.games['card_history'].map(lambda x: self._get_card_list(x, player='opponent'))

    def generate_matchups(self, game_mode = 'ranked', game_threshold = 0):
        """
        Generates a pandas groupby table with duration, count, coin, win #, win%, and card_history

        Keyword parameter:
        game_mode -- str, either 'ranked', 'casual', or 'both', default is ranked
        game_threshold -- lowerbound for games played, any # of games lower than the threshold are not returned

        Returns:
        grouped -- pandas groupby object, indicies are player deck 'p_deck_type' then opponent 'o_deck_type'
        """
        decks = self.games
        if game_mode != 'both':
            decks = decks[decks['mode'] == game_mode]
        decks['win'] = decks['result'].map(lambda x: True if x == 'win' else False)
        decks['count'] = [1]*len(decks)

        grouped = decks.groupby(['p_deck_type', 'o_deck_type']).agg({'coin': np.sum, 'duration': [np.mean, np.std], 'count': np.sum, 'win': np.sum, 'card_history': lambda x: tuple(x)})
        grouped['win%'] = grouped['win']['sum']/grouped['count']['sum']*100
        grouped = grouped[grouped['count']['sum'] > game_threshold]
        return grouped #note this returns a groupby, so a reset_index is necessary before pivoting/plotting


    def create_matchup_heatmap(self, game_mode = 'ranked', game_threshold = 0):
        """
        Returns a list of one dictionary to be used with plotly's json renderr

        Keyword parameter:
        game_mode -- str, either 'ranked', 'casual', or 'both', default is ranked
        game_threshold -- lowerbound for games played, any # of games lower than the threshold are not returned

        Returns:
        graphs -- a list of one dictionary to be used with plotly.utils.PlotlyJSONEncoder
        """
        data = self.generate_matchups(game_mode, game_threshold).reset_index()
        data = data[['p_deck_type', 'o_deck_type', 'win%']]
        x_vals = data['o_deck_type'].map(lambda x: x.replace('_', ' '))
        y_vals = data['p_deck_type'].map(lambda x: x.replace('_', ' '))
        data = data.pivot('o_deck_type', 'p_deck_type')

        graphs = [
            dict(
                data=[
                    dict(
                        z = [data[x].values.tolist() for x in data.columns],
                        y = y_vals,
                        x = x_vals,
                        type='heatmap',
                        colorscale='Viridis'

                )
                ],
                layout = dict(
                    margin = dict(
                        l = 160,
                        b = 160
                    ),
                    height = 900
                )
            )
        ]

        return graphs

    def generate_cards(self, filtered):
        """
        Generates a grouped win/loss count for specific cards

        Keyword parameter:
        filtered -- pandas dataframe, should be a subset of self.games filtered somehow

        Returns:
        p_df -- pandas groupby object, cards marked as 'me' for player, index is the card name ['card'], columns are win count and loss count ['win', 'loss']
        o_df -- pandas groupby object, cards marked as 'opponent' for player, index is the card name ['card'], columns are win count and loss count ['win', 'loss']
        """
        p_df = []
        o_df = []
        for r in zip(filtered['p_cards_played'], filtered['o_cards_played'], filtered['result']):
            for p_card in r[0]:
                p_df.append({'card': p_card, 'win': 1, 'loss': 0} if r[2] == 'win' else {'card': p_card, 'win': 0, 'loss': 1})
            for o_card in r[1]:
                o_df.append({'card': o_card, 'win': 1, 'loss': 0} if r[2] == 'loss' else {'card': o_card, 'win': 0, 'loss': 1})

        p_df = pd.DataFrame(p_df)
        o_df = pd.DataFrame(o_df)
        p_df = p_df.groupby('card').agg(np.sum)
        o_df = o_df.groupby('card').agg(np.sum)
        return p_df, o_df

    def generate_card_matchups(self, game_mode = 'ranked', card_threshold = 2):
        """
        Generates a dataframe with a list of cards, and the matchups where the card won and lost in the format of: ['card', 'p_deck_type', 'winning_matchups', 'losing_matchups']

        Keyword parameter:
        game_mode -- str, game type
        card_threshold -- int, the minimum amount of time the card has to show up

        Returns:
        cards -- pandas groupby object, with ['card', 'p_deck_type', 'o_deck_type', 'loss', 'win', 'win%']
        """
        cards = []
        gs = self.games
        if game_mode != 'both':
           gs = gs[gs['mode'] == game_mode]
        for r in zip(gs['p_cards_played'], gs['result'], gs['p_deck_type'], gs['o_deck_type']):
            for card in r[0]:
                data = {'card': card, 'p_deck_type': r[2], 'o_deck_type': r[3], 'win': 1, 'loss': 0} if r[1] == 'win' else {'card': card, 'p_deck_type': r[2], 'o_deck_type': r[3], 'win': 0, 'loss': 1}
                cards.append(data)
        cards = pd.DataFrame(cards)
        cards = cards.groupby(['card', 'p_deck_type', 'o_deck_type']).agg(np.sum)
        cards = cards[cards['win'] + cards['loss'] > card_threshold]
        cards['win%'] = cards['win']/(cards['win'] + cards['loss'])
        return cards

    def create_cards_heatmap(self, p_deck_type, game_mode = 'ranked', card_threshold = 2):
        data = self.generate_card_matchups(game_mode, card_threshold).reset_index()
        data = data[data['p_deck_type'] == p_deck_type]
        data = data[['card', 'o_deck_type', 'win%']]
        x_vals = data['o_deck_type'].map(lambda x: x.replace('_', ' '))
        y_vals = data['card']
        data = data.pivot('o_deck_type', 'card')

        graphs = [
            dict(
                data=[
                    dict(
                        z = [data[x].values.tolist() for x in data.columns],
                        y = y_vals,
                        x = x_vals,
                        type='heatmap',
                        colorscale='Viridis'

                )
                ],
                layout = dict(
                    margin = dict(
                        l = 160,
                        b = 160
                    ),
                    height = 900
                )
            )
        ]

        return graphs

    def write_hdf5(self, hdf5_name):
        """
        Writes out self.games into a hdf5_file

        Keyword parameter:
        hdf5_name -- str, name of the hdf5 file
        """
        self.games.to_hdf('{}{}'.format(DATA_PATH, hdf5_name), 'table', append = False)


    def update_count(self, user_hash, total_items):
        """Updates the given total items count for the user with user_hash"""
        conn = sqlite3.connect('{}/users.db'.format(DATA_PATH))
        c = conn.cursor()
        c.execute('UPDATE users SET total_items = ?', (total_items,))
        conn.commit()
        conn.close()

    def store_data(self):
        """
        Stores the python data by using the filename as the sha5 hash of the username and api_key -> hash is stored in a database for lookups later, data is stored using the hdf5 format
        Table is in the format of ['user_hash', 'total_items', 'json_name', 'hdf5_name']

        Returns:
        user[1] -- int, total items
        user[2] -- str, json_name
        user[3] -- str, hdf5_name
        """
        user_hash = hashlib.sha1(('{}{}'.format(self.username, self.api_key)).encode()).hexdigest()
        conn = sqlite3.connect('{}/users.db'.format(DATA_PATH)) #TODO FIX THIS
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_hash = ?', (user_hash,))
        data = c.fetchall()
        if len(data) != 0:
            user = data[0]
        else:
            user = (user_hash, 0, '{}_j.json'.format(user_hash), '{}_h.hdf5'.format(user_hash))
            c.execute('INSERT INTO users VALUES (?, ?, ?, ?)', user)
        conn.commit()
        conn.close()
        return user[0], user[1], user[2], user[3]

    def read_data(self, json_name, hdf5_name):
        """
        Takes the names of the files and loads them into memory for processing

        Keyword parameter:
        json_name -- str, name of the json file
        hdf5_name -- str, name of the hdf5 file

        Returns:
        results -- dict, complete history of games and metadata
        """
        with open("{}{}".format(DATA_PATH, json_name)) as json_data:
            results = json.load(json_data)
        self.history = results
        self.games = pd.read_hdf('{}{}'.format(DATA_PATH, hdf5_name), 'table')
        return results

    def check_data(self, json_name, hdf5_name):
        """
        Checks for the existance of either file under the DATA_PATH, returns False if either is missing

        Keyword parameter:
        json_name -- str
        hdf5 -- str

        Returns:
        bool -- False if either is missing, True otherwise
        """
        if os.path.isfile("{}{}".format(DATA_PATH, json_name)) and os.path.isfile("{}{}".format(DATA_PATH, hdf5_name)):
            return True
        else:
            return False
