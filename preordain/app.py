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

@app.route('/matchups/<username>/<api_key>')
def matchups(username, api_key):
    scrape = preordain_analyzer.preordain_analyzer()
    scrape.grab_data(username, api_key)
    data = scrape.generate_matchups(game_threshold=1).reset_index()
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
                yaxis = dict(
                    fixedrange = True
                ),
                xaxis = dict(
                    fixedrange = True
                )
            )
        )
    ]
    ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template('matchups.html', ids=ids, graphJSON=graphJSON)
