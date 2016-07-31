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
import collectobot
import plotly.graph_objs as go

DATA_PATH = '../test_data/' #TODO in current directory while testing, needs to be fixed before shipping!
HDF_NAME = '../test_data/cbot.hdf5'
GRAPH_DATABASE = '../test_data/graph.db'

class yaha_analyzer(object):

    def __init__(self):
        self.total_pages = 0
        self.history = []
        self.username = ''
        self.api_key = ''
        self.new_data = False

    def generate_collectobot_data(self):
        """
        Generates collect-o-bot data from the database, writes it to a hdf5 file

        :return: list of games
        :rtype: pandas dataframe
        """
        results = collectobot.aggregate()
        self.games = results
        self.history = {'children': results, 'meta': {'total_items': len(results)}}
        self.generate_decks(dates = False)
        self.write_hdf5(HDF_NAME)
        return results


    def open_collectobot_data(self):
        """
        Loads the collectobot data from a hdf5 file
        """
        self.read_data(hdf5_name=HDF_NAME)

    def _load_json_data(self, json_file):
        """
        Opens a json file and loads it into the object, this method is meant for testing

        :param json_file: location of the json file
        :type json_file: string

        :return: list of games
        :rtype: pandas dataframe
        """
        with open(json_file, "r") as infile:
            results = json.load(infile)
        self.history = results
        self.generate_decks()
        return results

    def pull_data(self, username, api_key):
        """

        Grabs the data from the trackobot servers, writes it out to a new files and the database if it doesn't exist/outdated

        :param username: trackobot username
        :param api_key: trackobot api key
        :type username: string
        :type api_key: string

        :return: contents of the json_files
        :rtype: dictionary
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

        :param dates: generate specific dates into their own columns
        :type dates: bool

        :return: list of games
        :rtype: pandas dataframe
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

    def _unique_decks(self, game_mode='ranked', game_threshold = 5, formatted = True):
        """
        Returns a list with the unique decks for that game mode in self.games
        >> Don't actually use this, call the database instead

        :param game_mode: the game mode, 'ranked', 'casual', or 'both
        :param game_threshold: the minimum amount of games the deck has to show up
        :type game_mode: string
        :type game_threshold: int

        :returns: list of unique p_deck_types
        :rtype: list of strings
        """
        deck_types = self.generate_matchups(game_mode, game_threshold).reset_index()
        deck_types = deck_types['p_deck_type'].unique()
        if formatted:
            return sorted(list(map(lambda x: x.replace("_", " "), deck_types)))
        return deck_types

    def _unique_cards(self, game_mode='ranked', game_threshold = 5, formatted = True):
        """
        Returns a list with the unique cards for that game mode in self.games
        >> Don't actually use this, call the database instead

        :param game_mode: the game mode, 'ranked', 'casual', or 'both
        :param game_threshold: the minimum amount of games the deck has to show up
        :type game_mode: string
        :type game_threshold: int

        :return: a list of cards
        :rtype: list of strings
        """
        cards = self.generate_card_stats(game_mode, game_threshold).reset_index()
        cards = cards['card'].unique().tolist()
        return cards

    def _make_dates(self):
        """Internal method -- Converts the dates in self.games to separate columns for easier parsing, called by generate_decks"""
        format_date = lambda x: datetime.datetime.strptime(x, '%Y-%m-%dT%H:%M:%S.%fZ')
        split_date = lambda x: {'year': x.year, 'month': x.month, 'day': x.day, 'hour': x.hour, 'minute': x.minute, 'second': x.second}
        date_df = pd.DataFrame(list(map(lambda x: split_date(format_date(x)), self.games['added'])))
        self.games = self.games.join(date_df, how='outer')

    def _get_card_list(self, dict_list, player='me'):
        """
        Internal method -- Returns the list of cards that were played in a game, called by _generate_cards_played

        Keyword parameters:
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

        :param game_mode: the game mode, 'ranked', 'casual', or 'both
        :param game_threshold: the minimum amount of games the deck has to show up
        :type game_mode: string
        :type game_threshold: int

        :return: grouped, indicies are player 'p_deck_type' then opponent 'o_deck_type'
        :rtype: pandas groupby
         """
        decks = self.games
        if game_mode != 'both':
            decks = decks[decks['mode'] == game_mode]
        decks.loc[:, 'win'] = decks['result'].map(lambda x: True if x == 'win' else False)
        decks.loc[:, 'count'] = [1]*len(decks)

        grouped = decks.groupby(['p_deck_type', 'o_deck_type']).agg({'coin': np.sum, 'duration': [np.mean, np.std], 'count': np.sum, 'win': np.sum, 'card_history': lambda x: tuple(x)})
        grouped['win%'] = grouped['win']['sum']/grouped['count']['sum']*100
        grouped = grouped[grouped['count']['sum'] > game_threshold]
        return grouped #note this returns a groupby, so a reset_index is necessary before pivoting/plotting


    def generate_cards(self, filtered):
        """
        Generates a grouped win/loss count for specific cards

        :param filtered: subset of self.games filtered
        :type filtered: pandas dataframe

        :return: p_df, o_df -- cards marked as 'me' for player, index is the card name ['card'], columns are win count and loss count ['win', 'loss'], cards marked as 'opponent' for player, index is the card name ['card'], columns are win count and loss count ['win', 'loss']
        :rtype: pandas groupby, pandas groupby
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

    def generate_decklist_matchups(self, game_mode = 'ranked', game_threshold = 2):
        """
        Generates a dataframe with a list of cards, and the matchups where the card won and lost in the format of: ['card', 'p_deck_type', 'winning_matchups', 'losing_matchups']

        :param game_mode: the game mode, 'ranked', 'casual', or 'both
        :param game_threshold: the minimum amount of games the deck has to show up
        :type game_mode: string
        :type game_threshold: int

        :return: cards with ['card', 'p_deck_type', 'o_deck_type', 'loss', 'win', 'win%']
        :rtype: pandas groupby
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
        cards = cards[(cards['win'] + cards['loss']) > game_threshold]
        cards.loc[:, 'win%'] = cards['win']/(cards['win'] + cards['loss'])
        cards['total_games'] = cards['win'] + cards['loss']
        return cards


    def generate_card_stats(self, game_mode='ranked', game_threshold = 2):
        """
        Returns a groupby object with ['card', 'p_deck_type', 'o_deck_type', 'turn', 'loss', 'win'] as [str, str, str, int, int, int]
        :param game_mode: game type
        :param card_threshold: the minimum amount of time the card has to show up
        :type game_mode: str
        :type card_threshold: str

        :return: cards
        :rtype: pandas groupby object
        """
        cards = []
        gs = self.games
        if game_mode != 'both':
            gs = gs[gs['mode'] == game_mode]

        for r in zip(gs['card_history'], gs['result'], gs['p_deck_type'], gs['o_deck_type']):
            for play in r[0]:
                card = play['card']['name']
                player = play['player']
                turn = play['turn']
                result = {'win': 1, 'loss': 0} if r[1] == 'win' else {'win': 0, 'loss': 1}
                card_data = {'card': card,  'player': player, 'turn': turn}
                player_data = {'p_deck_type': r[2], 'o_deck_type': r[3]} if player == 'me' else {'p_deck_type': r[3], 'o_deck_type': r[2]}
                data = result.copy()
                data.update(card_data)
                data.update(player_data)
                cards.append(data)

        cards = pd.DataFrame(cards)
        cards = cards.groupby(['card', 'p_deck_type', 'o_deck_type', 'turn']).agg(np.sum)
        cards = cards[cards['win'] + cards['loss'] > game_threshold]
        cards.loc[:, 'win%'] = cards['win']/(cards['win'] + cards['loss'])
        cards['total_games'] = cards['win'] + cards['loss']
        return cards

    def create_heatmap(self, x, y, z, df, title, layout = None, text = None):
        """
        Creates a heatmap x, y, and z

        :param x: name of the x value column
        :param y: name of the y value column
        :param z: name of the z value column
        :param df: dataframe
        :param title: heatmap title
        :param layout: dictionary for plotly layout. Autogenerated if None is passed
        :param text: column to be displayed for hover text
        :type x: string
        :type y: string
        :type z: string
        :type df: pandas dataframe
        :type title: string
        :type layout: dictionary
        :type text: string

        :return: one dictionary to be used with plotly.utils.PlotlyJSONEncoder
        :rtype: list
        """
        data = df.reset_index()
        hover_text = []
        if text:
            text = data[[x, y, text]]
            text = text.pivot(x, y)
            hover_text = [text[x].values.tolist() for x in text.columns]
            for n, row in enumerate(hover_text):
                for m, val in enumerate(row):
                    hover_text[n][m] = 'Total Games: {}'.format(hover_text[n][m])
        data = data[[x, y, z]]
        x_vals = sorted(data[x].unique())
        y_vals = sorted(data[y].unique())
        x_vals = list(map(lambda x: x.replace('_', ' '), x_vals))
        y_vals = list(map(lambda x: x.replace('_', ' '), y_vals))
        data = data.pivot(x, y)
        z_vals = [data[x].values.tolist() for x in data.columns]
        titles = self.title_format(x, y, z)
        if layout == None:
            annotations = []
            for n, row in enumerate(z_vals):
                for m, val in enumerate(row):
                    var = z_vals[n][m]
                    annotations.append(
                        dict(
                            text = '{:.2f}'.format(val) if not pd.isnull(val) else '',
                            x = x_vals[m],
                            y = y_vals[n],
                            showarrow = False,
                            font = dict(color='white' if val < 0.7 else 'black')
                        )
                    )

            layout = dict(
                margin = dict(
                    l = 160,
                    b = 160
                ),
                height = 900,
                xaxis = dict(
                    title = titles[0]
                ),
                yaxis = dict(
                    title = titles[1]
                ),
                title = title,
                annotations = annotations
            )

        graphs = dict(
                data = [
                    dict(
                        z = z_vals,
                        y = y_vals,
                        x = x_vals,
                        type = 'heatmap',
                        text = hover_text,
                        colorscale = 'Viridis'
                    )
                ],
                layout = layout
            )


        return graphs

    def create_stacked_chart(self, iter_column, x_col, y_col, df, layout = None):
        """
        Creates a stacked chart from a cards groupby object
        """
        if layout == None:
            layout = dict(
                margin = dict(
                    l = 160,
                    b = 160
                ),
                height = 900
            )
        x_vals = []
        y_vals = []
        for uniq_value in data.index.get_level_values(iter_column).tolist():
            x_vals.append(data.loc[uniq_value][x_col])
            y_vals.append(data.loc[uniq_value][y_col])
        data = []
        for i in zip(x_vals, y_vals):
            scatter = dict(
                x = i[0],
                y = i[1],
                fill='tozeroy'
            )
            data.append(scatter)
        graphs = [
            dict(
                data = data,
                layout = layout)
        ]
        return graphs


    def create_stacked_histogram(self, df, card_name):
        """
        Creates a stacked histogram of the card for it's win counts
        :param df: the card dataframe to generate a histogram for
        :type df: pandas dataframe
        :param card_name: the card name for the title
        :type card_name: string

        :return: one dictionary to be used with plotly.utils.PlotlyJSONEncoder
        :rtype: dictionary
        """
        stats = df.reset_index().groupby(['p_deck_type', 'turn']).agg({'win': np.sum})
        hist_data = []
        traces = []
        for deck_type, new_df in stats.groupby(level=0):
            df = new_df.reset_index()
            trace = go.Bar(
                x = df['turn'],
                y = df['win'],
                name = deck_type.replace('_', ' ')
            )
            traces.append(trace)
        layout = go.Layout(
            barmode='stack',
            xaxis = dict(title='Turn #'),
            yaxis = dict(title='Win Count'),
            title = 'Win Counts for {}'.format(card_name),
            showlegend = True
        )
        return go.Figure(data = traces, layout=layout)


    def write_hdf5(self, hdf5_name):
        """
        Writes out self.games into a hdf5_file

        :param hdf5_name: name of the hdf5 file
        :type hdf5_name: string
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


        :return: total items, json_name, and hdf5_name
        :rtype: [int, string, string]
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

    def read_data(self, json_name = None, hdf5_name = None):
        """
        Takes the names of the files and loads them into memory for processing

        :param hdf5_name: name of the hdf5 file
        :type hdf5_name: string
        :param json_name: name of the json file
        :type json_name: string

        :return: complete history of games and metadata
        :rtype: dictionary
        """
        if json_name:
            with open("{}{}".format(DATA_PATH, json_name)) as json_data:
                results = json.load(json_data)
                self.history = results
        if hdf5_name:
            self.games = pd.read_hdf('{}{}'.format(DATA_PATH, hdf5_name), 'table')

    def check_data(self, json_name, hdf5_name):
        """
        Checks for the existance of either file under the DATA_PATH, returns False if either is missing

        :param hdf5_name: name of the hdf5 file
        :type hdf5_name: string
        :param json_name: name of the json file
        :type json_name: string

        :return: False if either is missing, True otherwise
        :rtype: bool
        """
        if os.path.isfile("{}{}".format(DATA_PATH, json_name)) and os.path.isfile("{}{}".format(DATA_PATH, hdf5_name)):
            return True
        else:
            return False


    def title_format(self, *titles):
        """
        Formats the titles

        :param titles: titles to be replaced
        :type titles: list of strings

        :return: list of replaced titles
        :rtype: list of strings
        """
        titles_list = []
        for title in titles:
            if title == 'p_deck_type':
                titles_list.append('Player Deck Name')
            if title == 'o_deck_type':
                titles_list.append('Opponent Deck Name')
            if title == 'win%':
                titles_list.append('Win %')
        return titles_list

    def get_name_list(self):
        """
        Iterates through the database and creates a list of strings for deck names and card names

        :return: list of deck and card names
        :rtype: (list, list)
        """
        conn = sqlite3.connect(GRAPH_DATABASE)
        c = conn.cursor()
        c.execute('SELECT name, type FROM graphs')
        data = c.fetchall()
        deck_data = []
        card_data = []
        for row in data:
            if row[1] == 'deck':
                deck_data.append(row[0].replace('_', ' '))
            elif row[1] == 'card':
                card_data.append(row[0])
        conn.close()
        return deck_data, card_data

    def make_graph_data(self): #TODO: multithread this at some point
        """
        Iterates through all the cards & decks above the game threshold, makes plotly json for each one
        """
        game_threshold = 5
        graph_id = 0
        sql_data = []
        decks = map(lambda x: x.replace(' ', '_'), self._unique_decks())
        data = self.generate_decklist_matchups(game_threshold = game_threshold).reset_index()
        for deck in decks:
            d_data = data[data['p_deck_type'] == deck]
            graphs = self.create_heatmap(x = 'o_deck_type', y = 'card', z = 'win%', df = d_data, title = 'Win % of Cards in {}'.format(deck), text='total_games')
            graph_json = json.dumps([graphs], cls=plotly.utils.PlotlyJSONEncoder)
            sql_data.append((graph_id, deck, graph_json, 'deck'))
            graph_id += 1
        self._update_graph_data(sql_data)

        sql_data = []
        cards = self._unique_cards()
        data = self.generate_card_stats(game_threshold = game_threshold)
        for card in cards:
            h_data = data.sum(level=['card', 'p_deck_type', 'o_deck_type']).loc[card]
            h_data.loc[:, 'win%'] = h_data['win']/(h_data['loss'] + h_data['win'])
            heatmap = self.create_heatmap(x = 'o_deck_type', y = 'p_deck_type',z = 'win%', df = h_data, title = 'Win % of {}'.format(card), text='total_games')
            distplot = self.create_stacked_histogram(df = data.loc[card], card_name = card)
            graph_json = json.dumps([heatmap, distplot], cls=plotly.utils.PlotlyJSONEncoder)
            graph_name = card
            sql_data.append((graph_id, card, graph_json, 'card'))
            graph_id += 1
        self._update_graph_data(sql_data)

    def _update_graph_data(self, graph_sql):
        """
        Updates the graph database, if the row doesn't already exist, then insert
        :param: graph_sql -- list of tuples in the fasion (graph_id, graph_name, graph_json, graph_type)
        """
        conn = sqlite3.connect(GRAPH_DATABASE)
        c = conn.cursor()
        for graph_id, graph_name, graph_json, graph_type in graph_sql:
            exists = c.execute('SELECT id FROM graphs WHERE name = ? AND type = ?', (graph_name, graph_type))
            if exists:
                c.execute('UPDATE graphs SET name = ?, json = ?, type = ? WHERE name = ? AND type = ?', (graph_name, graph_json, graph_type, graph_name, graph_type))
            else:
                c.execute('INSERT INTO graphs VALUES(?, ?, ?, ?)', (graph_id, graph_name, graph_json, graph_type))
        conn.commit()
        conn.close()

    def get_graph_data(self, name):
        """
        Returns plotly json for the specified name

        :param name: name to match in the database
        :type name: string

        :return: plotly json data
        :rtype: string
        """
        conn = sqlite3.connect(GRAPH_DATABASE)
        c = conn.cursor()
        c.execute('SELECT json FROM graphs WHERE name = ?', (name,))
        data = c.fetchall()
        data = data[0][0]
        conn.close()
        return data

    def rebuild_and_update(self):
        self.generate_collectobot_data()
        self.make_graph_data()

    def remake_graphs(self):
        self.open_collectobot_data()
        self.make_graph_data()
