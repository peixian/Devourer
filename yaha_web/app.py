from flask import Flask, make_response, render_template
import yaha_analyzer
import plotly.plotly as py
import plotly
import plotly.graph_objs as go
import json
import sys
import collectobot
CSV_HEADER = 'Content-Disposition'

app = Flask(__name__)

@app.route('/')
def index():
    scrape = yaha_analyzer.yaha_analyzer()
    deck_data, card_data = scrape.get_name_list()
    return render_template('front.html', title = 'Yaha', active=generate_active_status('index'), deck_data=deck_data, card_data=card_data, game_count = 20)

@app.route('/card/<card_name>')
def card(card_name):
    scrape = yaha_analyzer.yaha_analyzer()
    graphJSON = scrape.get_graph_data(card_name)
    game_count = 20
    return render_template('matchups.html', title = card_name, page_name = card_name, active=generate_active_status('card'), graphJSON=graphJSON, game_count = game_count, ids = ['Heatmap', 'Win Counts With {} in Decks'.format(card_name), 'Win Counts With {} Against Decks'.format(card_name), 'Lose Counts With', 'Lose Counts Against'])

@app.route('/deck/<deck>')
def return_deck(deck):
    deck = deck.replace(' ', '_')
    scrape = yaha_analyzer.yaha_analyzer()
    graphJSON = scrape.get_graph_data(deck)

    game_count = 20
    return render_template('matchups.html', title = deck, page_name = deck, active = generate_active_status('deck'), graphJSON = graphJSON, game_count = game_count, ids = ['Heatmap'])

@app.route('/decks')
def return_decks():
    scrape = yaha_analyzer.yaha_analyzer()
    deck_data, card_data = scrape.get_name_list()
    return render_template('front.html', title = 'Decks', active = generate_active_status('deck'), deck_data=deck_data, card_data=[], game_count = 20)

@app.route('/cards')
def return_cards():
    scrape = yaha_analyzer.yaha_analyzer()
    deck_data, card_data = scrape.get_name_list()
    return render_template('front.html', title = 'Cards', active=generate_active_status('card'), deck_data=[], card_data=card_data, game_count = 20)

@app.route('/rebuild')
def rebuild():
    scrape = yaha_analyzer.yaha_analyzer()
    scrape.rebuild_and_update()

@app.route('/remake')
def remake():
    scrape = yaha_analyzer.yaha_analyzer()
    scrape.remake_graphs()


def generate_active_status(active_element):
    if active_element == 'index':
        return ['active', '', '']
    elif active_element == 'deck':
        return ['', 'active', '']
    elif active_element == 'card':
        return ['', '', 'active']

def remove_underscore(names):
    return list(map(lambda x: x.replace('_', ' '), names))

