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
    return scrape.games.head().to_csv()
