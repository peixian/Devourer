from flask import Flask, make_response, render_template
import preordain_analyzer
import plotly.plotly as py
import plotly
import plotly.graph_objs as go
import json

CSV_HEADER = 'Content-Disposition'

app = Flask(__name__)

@app.route('/')
def index():
    pass


@app.route('/submit/<username>/<api_key>') #TODO - make this a real request
def submit(username, api_key):
    scrape = preordain_analyzer.preordain_analyzer()
    scrape.grab_data(username, api_key)
    response = make_response(scrape.games.to_csv())
    response.headers['Content-Type'] = CSV_HEADER
    return response


@app.route('/collectobot')
def collectobot():
    scrape = preordain_analyzer.preordain_analyzer()
    scrape._open_collectobot_data('cbot_06.json')
    graphs = scrape.create_matchup_heatmap(game_threshold=1)
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('matchups.html', ids=ids, graphJSON=graphJSON)

@app.route('/matchups/<username>/<api_key>')
def matchups(username, api_key):
    scrape = preordain_analyzer.preordain_analyzer()
    scrape.grab_data(username, api_key)
    ids, graphJSON = scrape.create_matchup_heatmap(game_threshold=1)

    return render_template('matchups.html', ids=ids, graphJSON=graphJSON)
