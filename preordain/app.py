from flask import Flask, make_response

app = Flask(__name__)

@app.route('/')
def index():
    pass

@app.route('/submit/<username>/<api_key>') #TODO - make this a real request
def submit(username, api_key):
    url = "https://trackobot.com/profile/history.json?"
    auth = {"username": username, "token": api_key}
    req = requests.get(url, params=auth).json()
    metadata = req["meta"]
    results = {'children': req['history']}
    if metadata['total_pages'] != None:
        for page_number in range(2, metadata['total_pages']+1):
            auth['page'] = page_number
            results['children'].extend(requests.get(url, params=auth).json()['history'])
    return json.dumps(results, indent=4)
