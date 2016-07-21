from flask import Flask, make_response
import preordain_analyzer

app = Flask(__name__)

@app.route('/')
def index():
    pass

@app.route('/submit/<username>/<api_key>') #TODO - make this a real request
def submit(username, api_key):
    scrape = preordain_analyzer.preordain_analyzer()
    scrape.grab_data(username, api_key)
    response = make_response(scrape.games.to_csv())
    response.headers['Content-Type'] = 'Content-Disposition'
    return response

    p_df, o_df = scrape.generate_cards(scrape.games[(scrape.games['mode'] == 'ranked') & (scrape.games['p_deck_type'] == 'Dragon Warrior')])
    return o_df.to_csv()
